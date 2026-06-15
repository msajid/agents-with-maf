from pathlib import Path
from typing import Optional
from datetime import datetime, timezone, date, time
from zoneinfo import ZoneInfo
from threading import RLock
import json
import os

from seed_data import (
    INITIAL_PATIENTS,
    INITIAL_DENTISTS,
    generate_dates,
    generate_hourly_slots,
)


DATA_ROOT = Path("data")
CLINIC_TIMEZONE = "Asia/Dubai"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(value: str) -> str:
    return value.lower().strip()


def read_json(path: Path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json_atomic(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = path.with_name(path.name + ".tmp")

    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.flush()
        os.fsync(file.fileno())

    os.replace(temp_path, path)


class FileSystemClinicStore:
    """
    Simple file-system store for the course demo.

    Clinic state:
    data/clinic/dentists.json
    data/clinic/slots.json
    data/clinic/bookings.json

    Patient state:
    data/patients/<patient_id>/profile.json
    data/patients/<patient_id>/appointments.json
    data/patients/<patient_id>/session_state.json
    """

    def __init__(
        self,
        root: Path = DATA_ROOT,
        timezone_name: str = CLINIC_TIMEZONE,
    ):
        self.root = root
        self.timezone_name = timezone_name
        self.clinic_dir = self.root / "clinic"
        self.patients_dir = self.root / "patients"
        self.lock = RLock()

    @property
    def dentists_path(self) -> Path:
        return self.clinic_dir / "dentists.json"

    @property
    def slots_path(self) -> Path:
        return self.clinic_dir / "slots.json"

    @property
    def bookings_path(self) -> Path:
        return self.clinic_dir / "bookings.json"

    def patient_dir(self, patient_id: str) -> Path:
        return self.patients_dir / patient_id

    def patient_profile_path(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "profile.json"

    def patient_appointments_path(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "appointments.json"

    def patient_session_path(self, patient_id: str) -> Path:
        return self.patient_dir(patient_id) / "session_state.json"

    def bootstrap(self) -> None:
        self.clinic_dir.mkdir(parents=True, exist_ok=True)
        self.patients_dir.mkdir(parents=True, exist_ok=True)

        if not self.dentists_path.exists():
            write_json_atomic(self.dentists_path, INITIAL_DENTISTS)

        if not self.slots_path.exists():
            slots = generate_hourly_slots(
                dentists=INITIAL_DENTISTS,
                dates=generate_dates("2026-06-15", "2026-07-15"),
            )
            write_json_atomic(self.slots_path, slots)

        if not self.bookings_path.exists():
            write_json_atomic(self.bookings_path, {})

        for patient_id, profile in INITIAL_PATIENTS.items():
            self.patient_dir(patient_id).mkdir(parents=True, exist_ok=True)

            if not self.patient_profile_path(patient_id).exists():
                write_json_atomic(self.patient_profile_path(patient_id), profile)

            if not self.patient_appointments_path(patient_id).exists():
                write_json_atomic(self.patient_appointments_path(patient_id), [])

    def clinic_now(self) -> datetime:
        return datetime.now(ZoneInfo(self.timezone_name))

    def slot_start_datetime(self, slot: dict) -> datetime:
        slot_date = date.fromisoformat(slot["date"])
        slot_time = time.fromisoformat(slot["start_time"])

        return datetime.combine(
            slot_date,
            slot_time,
            tzinfo=ZoneInfo(self.timezone_name),
        )

    def is_slot_in_future(self, slot: dict) -> bool:
        return self.slot_start_datetime(slot) > self.clinic_now()

    def get_dentists(self) -> list[dict]:
        return read_json(self.dentists_path, [])

    def get_slots(self) -> list[dict]:
        return read_json(self.slots_path, [])

    def get_bookings(self) -> dict:
        return read_json(self.bookings_path, {})

    def save_bookings(self, bookings: dict) -> None:
        write_json_atomic(self.bookings_path, bookings)

    def get_patient_profile(self, patient_id: str) -> Optional[dict]:
        return read_json(self.patient_profile_path(patient_id), None)

    def get_patient_appointments(self, patient_id: str) -> list[dict]:
        return read_json(self.patient_appointments_path(patient_id), [])

    def save_patient_appointments(
        self,
        patient_id: str,
        appointments: list[dict],
    ) -> None:
        write_json_atomic(self.patient_appointments_path(patient_id), appointments)

    def save_patient_session(
        self,
        patient_id: str,
        session_dict: dict,
    ) -> None:
        write_json_atomic(self.patient_session_path(patient_id), session_dict)

    def find_dentist(self, dentist_id: int) -> Optional[dict]:
        return next(
            (
                dentist
                for dentist in self.get_dentists()
                if dentist["id"] == dentist_id
            ),
            None,
        )

    def find_slot(self, slot_id: str) -> Optional[dict]:
        return next(
            (
                slot
                for slot in self.get_slots()
                if slot["slot_id"] == slot_id
            ),
            None,
        )

    def is_slot_booked(self, slot_id: str) -> bool:
        bookings = self.get_bookings()

        return any(
            booking["slot_id"] == slot_id
            and booking["status"] == "booked"
            for booking in bookings.values()
        )

    def slot_supports_appointment_type(
        self,
        slot: dict,
        appointment_type: str,
    ) -> bool:
        requested = normalize(appointment_type)

        supported_types = [
            normalize(item)
            for item in slot.get("supported_appointment_types", [])
        ]

        return requested in supported_types

    def get_time_of_day(self, start_time: str) -> str:
        hour = int(start_time.split(":")[0])

        if 6 <= hour < 12:
            return "morning"

        if 12 <= hour < 17:
            return "afternoon"

        return "evening"

    def save_patient_appointment(
        self,
        patient_id: str,
        appointment: dict,
    ) -> list[dict]:
        appointments = self.get_patient_appointments(patient_id)
        appointments.append(appointment)
        self.save_patient_appointments(patient_id, appointments)

        return appointments

    def find_patient_appointment(
        self,
        patient_id: str,
        appointment_id: str,
    ) -> Optional[dict]:
        appointments = self.get_patient_appointments(patient_id)

        return next(
            (
                appointment
                for appointment in appointments
                if appointment["appointment_id"] == appointment_id
            ),
            None,
        )


STORE = FileSystemClinicStore()