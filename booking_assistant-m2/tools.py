from typing import Optional
from uuid import uuid4

from agent_framework import tool, FunctionInvocationContext

from clinic_store import STORE, now_utc, normalize


STORE.bootstrap()


def current_patient_id(ctx: FunctionInvocationContext) -> Optional[str]:
    if ctx.session is None:
        return None

    return ctx.session.state.get("patient_id")


@tool()
def lookup_patient(
    ctx: FunctionInvocationContext,
    patient_id: Optional[str] = None,
) -> dict:
    """
    Look up a patient profile and appointment history.

    If patient_id is not provided, use the patient id already loaded
    in the current AgentSession.
    """

    patient_id = patient_id or current_patient_id(ctx)

    if not patient_id:
        return {
            "success": False,
            "message": "Patient id is missing.",
        }

    patient = STORE.get_patient_profile(patient_id)

    if not patient:
        return {
            "success": False,
            "message": f"No patient found with id {patient_id}.",
        }

    return {
        "success": True,
        "patient": patient,
        "appointments": STORE.get_patient_appointments(patient_id),
    }


@tool()
def get_all_dentists() -> list[dict]:
    """Return all dentist profiles available in the clinic."""
    return STORE.get_dentists()


@tool()
def search_available_slots(
    appointment_type: str,
    preferred_date: Optional[str] = None,
    preferred_time_of_day: Optional[str] = None,
    dentist_id: Optional[int] = None,
    branch: Optional[str] = None,
    preferred_dentist_gender: Optional[str] = None,
    minimum_years_of_experience: Optional[int] = None,
    limit: int = 10,
) -> dict:
    """
    Search available appointment slots.

    For the demo, this only returns future and unbooked slots.
    """

    matching_slots = []

    for slot in STORE.get_slots():
        if not STORE.is_slot_in_future(slot):
            continue

        if STORE.is_slot_booked(slot["slot_id"]):
            continue

        if not STORE.slot_supports_appointment_type(slot, appointment_type):
            continue

        dentist = STORE.find_dentist(slot["dentist_id"])

        if not dentist:
            continue

        if preferred_date and slot["date"] != preferred_date:
            continue

        if preferred_time_of_day:
            if STORE.get_time_of_day(slot["start_time"]) != normalize(preferred_time_of_day):
                continue

        if dentist_id and slot["dentist_id"] != dentist_id:
            continue

        if branch and normalize(slot["branch"]) != normalize(branch):
            continue

        if preferred_dentist_gender and normalize(preferred_dentist_gender) != "any":
            if normalize(dentist["gender"]) != normalize(preferred_dentist_gender):
                continue

        if minimum_years_of_experience:
            if dentist["years_of_experience"] < minimum_years_of_experience:
                continue

        matching_slots.append(
            {
                "slot_id": slot["slot_id"],
                "date": slot["date"],
                "start_time": slot["start_time"],
                "end_time": slot["end_time"],
                "branch": slot["branch"],
                "appointment_type": appointment_type,
                "dentist": {
                    "id": dentist["id"],
                    "name": dentist["name"],
                    "gender": dentist["gender"],
                    "specialty": dentist["specialty"],
                    "years_of_experience": dentist["years_of_experience"],
                    "languages": dentist["languages"],
                },
            }
        )

        if len(matching_slots) >= limit:
            break

    return {
        "success": True,
        "current_clinic_datetime": STORE.clinic_now().isoformat(),
        "count": len(matching_slots),
        "available_slots": matching_slots,
    }


@tool()
def book_appointment(
    ctx: FunctionInvocationContext,
    slot_id: str,
    appointment_type: str,
    patient_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict:
    """Book an appointment and persist it immediately."""

    patient_id = patient_id or current_patient_id(ctx)

    if not patient_id:
        return {
            "success": False,
            "message": "Patient id is missing.",
        }

    with STORE.lock:
        patient = STORE.get_patient_profile(patient_id)
        slot = STORE.find_slot(slot_id)

        if not patient:
            return {
                "success": False,
                "message": f"No patient found with id {patient_id}.",
            }

        if not slot:
            return {
                "success": False,
                "message": f"Slot {slot_id} does not exist.",
            }

        if STORE.is_slot_booked(slot_id):
            return {
                "success": False,
                "message": f"Slot {slot_id} is already booked.",
            }

        dentist = STORE.find_dentist(slot["dentist_id"])

        appointment_id = f"A-{uuid4().hex[:8].upper()}"
        timestamp = now_utc()

        appointment = {
            "appointment_id": appointment_id,
            "patient_id": patient_id,
            "patient_name": patient["name"],
            "dentist_id": dentist["id"],
            "dentist_name": dentist["name"],
            "appointment_type": appointment_type,
            "reason": reason,
            "slot_id": slot_id,
            "date": slot["date"],
            "start_time": slot["start_time"],
            "end_time": slot["end_time"],
            "branch": slot["branch"],
            "status": "booked",
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        bookings = STORE.get_bookings()
        bookings[appointment_id] = {
            "appointment_id": appointment_id,
            "slot_id": slot_id,
            "dentist_id": dentist["id"],
            "patient_id": patient_id,
            "status": "booked",
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        STORE.save_bookings(bookings)
        STORE.save_patient_appointment(patient_id, appointment)

    return {
        "success": True,
        "message": "Appointment booked successfully.",
        "appointment": appointment,
    }


@tool()
def get_appointment_details(
    appointment_id: str,
    ctx: FunctionInvocationContext,
) -> dict:
    """Get appointment details for the current patient session."""

    patient_id = current_patient_id(ctx)

    if not patient_id:
        return {
            "success": False,
            "message": "Patient id is missing from the current session.",
        }

    appointment = STORE.find_patient_appointment(patient_id, appointment_id)

    if not appointment:
        return {
            "success": False,
            "message": f"No appointment found with id {appointment_id} for this patient.",
        }

    dentist = STORE.find_dentist(appointment["dentist_id"])

    return {
        "success": True,
        "appointment": appointment,
        "dentist": dentist,
    }