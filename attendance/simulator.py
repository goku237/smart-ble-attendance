from __future__ import annotations

import random

from .database import AttendanceRepository


def simulate_detections(repository: AttendanceRepository, count: int | None = None) -> list[str]:
    """Create realistic fake sightings for registered students; does not need Bluetooth hardware."""
    students = repository.list_students(active_only=True)
    if not students:
        return []
    selected = random.sample(students, min(count or len(students), len(students)))
    names: list[str] = []
    for student in selected:
        repository.record_detection(
            student["beacon_address"],
            name=f"Beacon-{student['roll_number']}",
            rssi=random.randint(-82, -38),
        )
        names.append(student["name"])
    return names


def seed_sample_students(repository: AttendanceRepository) -> int:
    sample = [
        ("CS2026001", "Aarav Sharma", "Computer Science", "AA:BB:CC:00:00:01"),
        ("CS2026002", "Diya Patel", "Computer Science", "AA:BB:CC:00:00:02"),
        ("CS2026003", "Kabir Singh", "Computer Science", "AA:BB:CC:00:00:03"),
        ("CS2026004", "Meera Iyer", "Computer Science", "AA:BB:CC:00:00:04"),
    ]
    added = 0
    for values in sample:
        try:
            repository.add_student(*values)
            added += 1
        except Exception as exc:
            if "UNIQUE constraint failed" not in str(exc):
                raise
    return added
