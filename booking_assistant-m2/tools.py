from pathlib import Path
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone
import json

from agent_framework import tool, FunctionInvocationContext


DATA_DIR = Path("data")
CLINIC_DIR = DATA_DIR / "clinic"
PATIENTS_DIR = DATA_DIR / "patients"

DENTISTS_FILE = CLINIC_DIR / "dentists.json"
FREE_SLOTS_FILE = CLINIC_DIR / "slots.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def patient_appointments_folder(patient_id: str) -> Path:
    return PATIENTS_DIR / patient_id / "appointments"

def read_json(path: Path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def normalize(value: str) -> str:
    return value.lower().strip()


def current_patient_id(ctx: FunctionInvocationContext) -> Optional[str]:
    """
    Patient id must already be available in the current session.
    The user should not pass patient_id to tools.
    """

    if ctx.session is None:
        return None

    return ctx.session.state.get("patient_id")


def patient_folder(patient_id: str) -> Path:
    return PATIENTS_DIR / patient_id


def patient_profile_file(patient_id: str) -> Path:
    return patient_folder(patient_id) / "profile.json"


def patient_appointments_folder(patient_id: str) -> Path:
    return patient_folder(patient_id) / "appointments"


def appointment_file(patient_id: str, appointment_id: str) -> Path:
    return patient_appointments_folder(patient_id) / f"{appointment_id}.json"


def load_patient(patient_id: str) -> dict:
    return read_json(patient_profile_file(patient_id), {})

def load_patient_appointments(patient_id: str) -> list[dict]:
   
    folder = patient_appointments_folder(patient_id)

    if not folder.exists():
        return []

    appointments = []

    for file_path in folder.glob("*.json"):
        appointment = read_json(file_path, {})

        if appointment:
            appointments.append(appointment)

    return appointments

def get_booked_slot_ids() -> set[str]:
    booked_slot_ids = set()

    if not PATIENTS_DIR.exists():
        return booked_slot_ids

    for appointment_path in PATIENTS_DIR.glob("*/appointments/*.json"):
        appointment = read_json(appointment_path, {})

        if appointment.get("status") == "booked":
            booked_slot_ids.add(appointment.get("slot_id"))

    return booked_slot_ids


def find_dentist(dentist_id: int) -> Optional[dict]:
    dentists = read_json(DENTISTS_FILE, [])

    for dentist in dentists:
        if dentist["id"] == dentist_id:
            return dentist

    return None


def find_slot(slot_id: str) -> Optional[dict]:
    slots = read_json(FREE_SLOTS_FILE, [])

    for slot in slots:
        if slot["slot_id"] == slot_id:
            return slot

    return None


def get_time_of_day(start_time: str) -> str:
    hour = int(start_time.split(":")[0])

    if 6 <= hour < 12:
        return "morning"

    if 12 <= hour < 17:
        return "afternoon"

    return "evening"


@tool()
def get_all_dentists() -> list[dict]:
    """Return all dentists from data/clinic/dentists.json."""
    return read_json(DENTISTS_FILE, [])


@tool()
def get_free_slots(
    preferred_date: Optional[str] = None,
    preferred_time_of_day: Optional[str] = None,
    dentist_id: Optional[int] = None,
    branch: Optional[str] = None,
    preferred_dentist_gender: Optional[str] = None,
    limit: int = 2,
) -> dict:
    """
    Return free slots from data/clinic/free_slots.json.

    A slot is considered unavailable if it already exists in any patient appointment file.
    """

    slots = read_json(FREE_SLOTS_FILE, [])
    booked_slot_ids = get_booked_slot_ids()

    matching_slots = []

    for slot in slots:
        if slot["slot_id"] in booked_slot_ids:
            continue

        dentist = find_dentist(slot["dentist_id"])

        if not dentist:
            continue

        if preferred_date and slot["date"] != preferred_date:
            continue

        if preferred_time_of_day:
            if get_time_of_day(slot["start_time"]) != normalize(preferred_time_of_day):
                continue

        if dentist_id and slot["dentist_id"] != dentist_id:
            continue

        if branch and normalize(slot["branch"]) != normalize(branch):
            continue

        if preferred_dentist_gender and normalize(preferred_dentist_gender) != "any":
            if normalize(dentist["gender"]) != normalize(preferred_dentist_gender):
                continue

        matching_slots.append(
            {
                "slot_id": slot["slot_id"],
                "date": slot["date"],
                "start_time": slot["start_time"],
                "end_time": slot["end_time"],
                "branch": slot["branch"],
                "dentist": {
                    "id": dentist["id"],
                    "name": dentist["name"],
                    "gender": dentist["gender"],
                    "specialty": dentist["specialty"],
                    "languages": dentist.get("languages", []),
                },
            }
        )

        if len(matching_slots) >= limit:
            break

    return {
        "success": True,
        "count": len(matching_slots),
        "free_slots": matching_slots,
    }


@tool()
def book_appointment(
    ctx: FunctionInvocationContext,
    slot_id: str,
    visit_reason: str,
) -> dict:
    """
    Book an appointment for the current patient.

    Patient id is always taken from session context.
    visit_reason is required.
    """

    patient_id = current_patient_id(ctx)

    if not patient_id:
        return {
            "success": False,
            "message": "Patient id is missing from the current session.",
        }

    if not visit_reason or not visit_reason.strip():
        return {
            "success": False,
            "message": "Visit reason is required to book an appointment.",
        }

    slot = find_slot(slot_id)

    if not slot:
        return {
            "success": False,
            "message": f"Slot {slot_id} was not found.",
        }

    if slot_id in get_booked_slot_ids():
        return {
            "success": False,
            "message": f"Slot {slot_id} is already booked.",
        }

    dentist = find_dentist(slot["dentist_id"])

    if not dentist:
        return {
            "success": False,
            "message": "Dentist was not found for this slot.",
        }

    patient = load_patient(patient_id)

    appointment_id = f"A-{uuid4().hex[:8].upper()}"
    timestamp = now_utc()

    appointment = {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "patient_name": patient.get("name", patient_id),
        "dentist_id": dentist["id"],
        "dentist_name": dentist["name"],
        "visit_reason": visit_reason,
        "slot_id": slot_id,
        "date": slot["date"],
        "start_time": slot["start_time"],
        "end_time": slot["end_time"],
        "branch": slot["branch"],
        "status": "booked",
        "created_at": timestamp,
    }

    write_json(
        appointment_file(patient_id, appointment_id),
        appointment,
    )

    if ctx.session is not None:
        ctx.session.state["last_appointment_id"] = appointment_id

    return {
        "success": True,
        "message": "Appointment booked successfully.",
        "appointment": appointment,
    }


@tool()
def get_appointment_details(
    ctx: FunctionInvocationContext,
    appointment_id: str,
) -> dict:
    """
    Get appointment details for the current patient.

    Patient id is always taken from session context.
    """

    patient_id = current_patient_id(ctx)

    if not patient_id:
        return {
            "success": False,
            "message": "Patient id is missing from the current session.",
        }

    appointment = read_json(
        appointment_file(patient_id, appointment_id),
        None,
    )

    if not appointment:
        return {
            "success": False,
            "message": f"No appointment found with id {appointment_id}.",
        }

    dentist = find_dentist(appointment["dentist_id"])

    return {
        "success": True,
        "appointment": appointment,
        "dentist": dentist,
    }