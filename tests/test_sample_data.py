from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from attendance.database import AttendanceRepository
from attendance.sample_data import (
    SAMPLE_STUDENTS,
    reset_demo_dataset,
    seed_demo_dataset,
)


class SampleDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = AttendanceRepository(Path(self.tmp.name) / "test.db")
        self.repo.initialize()
        self.today = datetime(2026, 10, 14, 12, 0, tzinfo=ZoneInfo("Asia/Kolkata"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_seed_creates_roster_and_attendance(self) -> None:
        result = seed_demo_dataset(self.repo, today=self.today)
        self.assertEqual(result["students_added"], len(SAMPLE_STUDENTS))
        self.assertEqual(len(self.repo.list_students()), len(SAMPLE_STUDENTS))
        self.assertGreater(result["attendance_created"], 0)

    def test_seed_is_idempotent_for_students(self) -> None:
        seed_demo_dataset(self.repo, today=self.today)
        second = seed_demo_dataset(self.repo, today=self.today)
        self.assertEqual(second["students_added"], 0)
        self.assertEqual(len(self.repo.list_students()), len(SAMPLE_STUDENTS))

    def test_seed_is_deterministic(self) -> None:
        seed_demo_dataset(self.repo, today=self.today)

        other_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(other_tmp.cleanup)
        other = AttendanceRepository(Path(other_tmp.name) / "test.db")
        other.initialize()
        seed_demo_dataset(other, today=self.today)

        self.assertEqual(
            self.repo.student_summary("2026-10-01", "2026-10-14"),
            other.student_summary("2026-10-01", "2026-10-14"),
        )

    def test_reset_rebuilds_clean_dataset(self) -> None:
        seed_demo_dataset(self.repo, today=self.today)
        result = reset_demo_dataset(self.repo)
        self.assertEqual(len(self.repo.list_students()), len(SAMPLE_STUDENTS))
        self.assertGreater(result["attendance_created"], 0)


if __name__ == "__main__":
    unittest.main()
