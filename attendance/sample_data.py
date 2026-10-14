from __future__ import annotations

import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .config import APP_TIMEZONE
from .database import AttendanceRepository


SAMPLE_STUDENTS: list[tuple[str, str, str, str]] = [
    # Computer Science
    ("CS2026001", "Aarav Sharma", "Computer Science", "AA:BB:CC:00:00:01"),
    ("CS2026002", "Diya Patel", "Computer Science", "AA:BB:CC:00:00:02"),
    ("CS2026003", "Kabir Singh", "Computer Science", "AA:BB:CC:00:00:03"),
    ("CS2026004", "Meera Iyer", "Computer Science", "AA:BB:CC:00:00:04"),
    ("CS2026005", "Rohan Gupta", "Computer Science", "AA:BB:CC:00:00:05"),
    ("CS2026006", "Pooja Bhat", "Computer Science", "AA:BB:CC:00:00:06"),
    ("CS2026007", "Aryan Deshmukh", "Computer Science", "AA:BB:CC:00:00:07"),
    ("CS2026008", "Sneha Kulkarni", "Computer Science", "AA:BB:CC:00:00:08"),
    ("CS2026009", "Vikram Nair", "Computer Science", "AA:BB:CC:00:00:09"),
    # Information Technology
    ("IT2026001", "Ananya Reddy", "Information Technology", "AA:BB:CC:00:00:0A"),
    ("IT2026002", "Vivaan Joshi", "Information Technology", "AA:BB:CC:00:00:0B"),
    ("IT2026003", "Ishita Nair", "Information Technology", "AA:BB:CC:00:00:0C"),
    ("IT2026004", "Arjun Mehta", "Information Technology", "AA:BB:CC:00:00:0D"),
    ("IT2026005", "Tanvi Shah", "Information Technology", "AA:BB:CC:00:00:0E"),
    ("IT2026006", "Kunal Verma", "Information Technology", "AA:BB:CC:00:00:0F"),
    ("IT2026007", "Riya Sen", "Information Technology", "AA:BB:CC:00:00:10"),
    ("IT2026008", "Aditya Rao", "Information Technology", "AA:BB:CC:00:00:11"),
    ("IT2026009", "Neha Pillai", "Information Technology", "AA:BB:CC:00:00:12"),
    # Electronics
    ("EC2026001", "Saanvi Kulkarni", "Electronics", "AA:BB:CC:00:00:13"),
    ("EC2026002", "Navya Desai", "Electronics", "AA:BB:CC:00:00:14"),
    ("EC2026003", "Harsh Patel", "Electronics", "AA:BB:CC:00:00:15"),
    ("EC2026004", "Priya Menon", "Electronics", "AA:BB:CC:00:00:16"),
    ("EC2026005", "Yash Thakur", "Electronics", "AA:BB:CC:00:00:17"),
    ("EC2026006", "Anjali Mishra", "Electronics", "AA:BB:CC:00:00:18"),
    ("EC2026007", "Rahul Chandra", "Electronics", "AA:BB:CC:00:00:19"),
    ("EC2026008", "Divya Krishnan", "Electronics", "AA:BB:CC:00:00:1A"),
    # Mechanical
    ("ME2026001", "Dhruv Verma", "Mechanical", "AA:BB:CC:00:00:1B"),
    ("ME2026002", "Riya Chatterjee", "Mechanical", "AA:BB:CC:00:00:1C"),
    ("ME2026003", "Karthik Menon", "Mechanical", "AA:BB:CC:00:00:1D"),
    ("ME2026004", "Simran Kaur", "Mechanical", "AA:BB:CC:00:00:1E"),
    ("ME2026005", "Manish Yadav", "Mechanical", "AA:BB:CC:00:00:1F"),
    ("ME2026006", "Lakshmi Narayan", "Mechanical", "AA:BB:CC:00:00:20"),
    ("ME2026007", "Farhan Ahmed", "Mechanical", "AA:BB:CC:00:00:21"),
    ("ME2026008", "Kavya Shetty", "Mechanical", "AA:BB:CC:00:00:22"),
    # Civil
    ("CE2026001", "Rohit Sharma", "Civil", "AA:BB:CC:00:00:23"),
    ("CE2026002", "Nandini Rao", "Civil", "AA:BB:CC:00:00:24"),
    ("CE2026003", "Imran Khan", "Civil", "AA:BB:CC:00:00:25"),
    ("CE2026004", "Shreya Bose", "Civil", "AA:BB:CC:00:00:26"),
    ("CE2026005", "Gaurav Malhotra", "Civil", "AA:BB:CC:00:00:27"),
    ("CE2026006", "Trisha Kapoor", "Civil", "AA:BB:CC:00:00:28"),
    ("CE2026007", "Nikhil Jain", "Civil", "AA:BB:CC:00:00:29"),
    ("CE2026008", "Aarohi Saxena", "Civil", "AA:BB:CC:00:00:2A"),
    # Electrical
    ("EE2026001", "Pranav Iyer", "Electrical", "AA:BB:CC:00:00:2B"),
    ("EE2026002", "Bhavna Patel", "Electrical", "AA:BB:CC:00:00:2C"),
    ("EE2026003", "Sachin Nair", "Electrical", "AA:BB:CC:00:00:2D"),
    ("EE2026004", "Megha Trivedi", "Electrical", "AA:BB:CC:00:00:2E"),
    ("EE2026005", "Varun Bhatia", "Electrical", "AA:BB:CC:00:00:2F"),
    ("EE2026006", "Pooja Rane", "Electrical", "AA:BB:CC:00:00:30"),
    ("EE2026007", "Deepak Kumar", "Electrical", "AA:BB:CC:00:00:31"),
    ("EE2026008", "Sanjana Ghosh", "Electrical", "AA:BB:CC:00:00:32"),
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

    detections: list[dict] = []
    absences: list[dict] = []
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
                detections.append(
                    {
                        "address": student["beacon_address"],
                        "name": f"Beacon-{student['roll_number']}",
                        "rssi": rng.randint(-85, -42),
                        "seen_at": when,
                        "late_after": time(9, 15),
                    }
                )
            elif rng.random() < 0.55:
                absences.append(
                    {"student_id": student["id"], "attendance_date": day.isoformat(), "status": "Absent"}
                )
    repository.record_detections_bulk(detections)
    repository.set_attendance_status_bulk(absences)
    return len(detections) + len(absences)


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
