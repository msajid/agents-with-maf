from datetime import date, timedelta


INITIAL_PATIENTS = {
    "P1001": {
        "patient_id": "P1001",
        "name": "Ayesha Khan",
        "preferred_branch": "Downtown Dental Clinic",
        "preferred_dentist_gender": "female",
        "preferred_time": "morning",
    },
    "P1002": {
        "patient_id": "P1002",
        "name": "Omar Ali",
        "preferred_branch": "Marina Dental Clinic",
        "preferred_dentist_gender": "any",
        "preferred_time": "evening",
    },
}


INITIAL_DENTISTS = [
    {
        "id": 1,
        "name": "Dr. Jane Smith",
        "gender": "female",
        "specialty": "General Dentistry & Preventive Care",
        "years_of_experience": 12,
        "daily_working_hours": "9:00 AM - 5:00 PM, Monday-Friday",
        "branch": "Downtown Dental Clinic",
        "languages": ["English", "Arabic"],
        "supported_appointment_types": [
            "cleaning",
            "consultation",
            "root canal consultation",
            "pediatric consultation",
        ],
        "strengths": [
            "Patient communication",
            "Root canal therapy",
            "Cosmetic dentistry",
            "Pediatric dentistry",
        ],
        "certifications": [
            "Board Certified - American Dental Association",
            "Advanced Life Support Certified",
            "Invisalign Provider Certification",
        ],
    },
    {
        "id": 2,
        "name": "Dr. Michael Johnson",
        "gender": "male",
        "specialty": "Orthodontics",
        "years_of_experience": 18,
        "daily_working_hours": "9:00 AM - 5:00 PM, Monday-Friday",
        "branch": "Marina Dental Clinic",
        "languages": ["English"],
        "supported_appointment_types": [
            "braces consultation",
            "invisalign consultation",
            "orthodontic follow-up",
            "consultation",
        ],
        "strengths": [
            "Braces consultation",
            "Invisalign",
            "Complex orthodontic cases",
        ],
        "certifications": [
            "Board Certified Orthodontist",
            "Invisalign Platinum Provider",
        ],
    },
    {
        "id": 3,
        "name": "Dr. Sara Ahmed",
        "gender": "female",
        "specialty": "Cosmetic Dentistry",
        "years_of_experience": 10,
        "daily_working_hours": "9:00 AM - 5:00 PM, Monday-Friday",
        "branch": "Downtown Dental Clinic",
        "languages": ["English", "Arabic", "Urdu"],
        "supported_appointment_types": [
            "cosmetic consultation",
            "teeth whitening",
            "veneers consultation",
            "consultation",
        ],
        "strengths": [
            "Teeth whitening",
            "Veneers",
            "Smile design",
        ],
        "certifications": [
            "Cosmetic Dentistry Fellowship",
            "Digital Smile Design Certification",
        ],
    },
]


def generate_dates(start_date: str, end_date: str) -> list[str]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    dates = []
    current = start

    while current <= end:
        dates.append(current.isoformat())
        current += timedelta(days=1)

    return dates


def generate_hourly_slots(
    dentists: list[dict],
    dates: list[str],
    start_hour: int = 9,
    end_hour: int = 17,
) -> list[dict]:
    slots = []

    for dentist in dentists:
        for slot_date in dates:
            for hour in range(start_hour, end_hour):
                slots.append(
                    {
                        "slot_id": f"S-{dentist['id']}-{slot_date.replace('-', '')}-{hour:02d}",
                        "dentist_id": dentist["id"],
                        "date": slot_date,
                        "start_time": f"{hour:02d}:00",
                        "end_time": f"{hour + 1:02d}:00",
                        "branch": dentist["branch"],
                        "supported_appointment_types": dentist["supported_appointment_types"],
                    }
                )

    return slots
