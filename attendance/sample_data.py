from __future__ import annotations

import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import APP_TIMEZONE
from .database import AttendanceRepository


SAMPLE_STUDENTS: list[tuple[str, str, str, str]] = [
    ("CS2026001", "Aarav Sharma", "Computer Science", "AA:BB:CC:00:00:01"),
    ("CS2026002", "Diya Patel", "Computer Science", "AA:BB:CC:00:00:02"),
    ("CS2026003", "Kabir Singh", "Computer Science", "AA:BB:CC:00:00:03"),
    ("CS2026004", "Meera Iyer", "Computer Science", "AA:BB:CC:00:00:04"),
    ("CS2026005", "Rohan Gupta", "Computer Science", "AA:BB:CC:00:00:05"),
    ("CS2026006", "Pooja Bhat", "Computer Science", "AA:BB:CC:00:00:06"),
    ("IT2026001", "Ananya Reddy", "Information Technology", "AA:BB:CC:00:00:07"),
    ("IT2026002", "Vivaan Joshi", "Information Technology", "AA:BB:CC:00:00:08"),
    ("IT2026003", "Ishita Nair", "Information Technology", "AA:BB:CC:00:00:09"),
    ("IT2026004", "Arjun Mehta", "Information Technology", "AA:BB:CC:00:00:0A"),
    ("EC2026001", "Saanvi Kulkarni", "Electronics", "AA:BB:CC:00:00:0B"),
    ("EC2026002", "Aditya Rao", "Electronics", "AA:BB:CC:00:00:0C"),
    ("EC2026003", "Navya Desai", "Electronics", "AA:BB:CC:00:00:0D"),
    ("ME2026001", "Dhruv Verma", "Mechanical", "AA:BB:CC:00:00:0E"),
    ("ME2026002", "Riya Chatterjee", "Mechanical", "AA:BB:CC:00:00:0F"),
    ("ME2026003", "Karthik Menon", "Mechanical", "AA:BB:CC:00:00:10"),
]


def seed_sample_students(repository: AttendanceRepository) -> int:
    """Insert the demo roster, skipping any students that already exist."""
    added = 0
    for roll_number, name, department, beacon in SAMPLE_STUDENTS:
        try:
            repository.add_student(roll_number, name, department, beacon)
            added += 1
        except Exception as exc:
            if "UNIQUE constraint failed" not in str(exc):
                raise
    return added


def seed_demo_attendance(
    repository: AttendanceRepository,
    days: int = 14,
    seed: int = 7,
    today: datetime | None = None,
) -> int:
    """Backfill deterministic, realistic attendance history for the demo roster.

    Each student gets a stable "reliability" so the analytics look believable, and
    Sundays are skipped. Sights go through the normal ``record_detection`` path so the
    detection log and attendance counts stay consistent with real scans.
    """
    rng = random.Random(seed)
    anchor = today or datetime.now(ZoneInfo(APP_TIMEZONE))
    anchor_date = anchor.date()
    students = repository.list_students(active_only=True)
    if not students:
        return 0

    created = 0
    for offset in range(days):
        day = anchor_date - timedelta(days=offset)
        if day.weekday() == 6:  # Skip Sundays.
            continue
        for index, student in enumerate(students):
            reliability = 0.7 + ((index * 13 + seed) % 24) / 100
            if rng.random() < min(reliability, 0.97):
                late = rng.random() < 0.18
                hour = 9 if late else 8
                minute = rng.randint(16, 44) if late else rng.randint(40, 59)
                when = datetime(
                    day.year, day.month, day.day, hour, minute, 0, tzinfo=ZoneInfo(APP_TIMEZONE)
                )
                repository.record_detection(
                    student["beacon_address"],
                    name=f"Beacon-{student['roll_number']}",
                    rssi=rng.randint(-85, -42),
                    seen_at=when,
                    late_after=time(9, 15),
                )
                created += 1
            elif rng.random() < 0.55:
                repository.set_attendance_status(student["id"], day.isoformat(), "Absent")
                created += 1
    return created


def seed_demo_dataset(
    repository: AttendanceRepository,
    days: int = 14,
    seed: int = 7,
    today: datetime | None = None,
) -> dict[str, int]:
    """Seed the demo roster and a matching history of attendance records."""
    students_added = seed_sample_students(repository)
    attendance_created = seed_demo_attendance(repository, days=days, seed=seed, today=today)
    return {"students_added": students_added, "attendance_created": attendance_created}


def reset_demo_dataset(
    repository: AttendanceRepository,
    days: int = 14,
    seed: int = 7,
) -> dict[str, int]:
    """Wipe students, attendance and detections, then rebuild the demo dataset."""
    for student in repository.list_students():
        repository.delete_student(student["id"])
    repository.clear_detection_log()
    return seed_demo_dataset(repository, days=days, seed=seed)
