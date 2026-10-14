from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from attendance.database import AttendanceRepository


class AttendanceRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = AttendanceRepository(Path(self.tmp.name) / "test.db")
        self.repo.initialize()
        self.repo.add_student("R001", "Test Student", "CSE", "aa-bb-cc-dd-ee-ff")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_detection_creates_and_updates_one_daily_record(self) -> None:
        when = datetime(2026, 10, 14, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.repo.record_detection("AA:BB:CC:DD:EE:FF", seen_at=when)
        self.repo.record_detection("AA:BB:CC:DD:EE:FF", seen_at=when.replace(hour=10))
        rows = self.repo.attendance_for_date("2026-10-14")
        self.assertEqual(rows[0]["status"], "Present")
        self.assertEqual(rows[0]["detection_count"], 2)

    def test_unknown_device_is_logged_not_marked_present(self) -> None:
        self.assertIsNone(self.repo.record_detection("00:00:00:00:00:00"))
        self.assertIsNone(self.repo.recent_detections()[0]["student_id"])
        self.assertEqual(self.repo.summary("2026-10-14")["present"], 0)

    def test_late_cutoff_marks_late_only_when_requested(self) -> None:
        late = datetime(2026, 10, 14, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        early = datetime(2026, 10, 14, 8, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.repo.record_detection("AA:BB:CC:DD:EE:FF", seen_at=early, late_after=time(9, 15))
        self.repo.add_student("R002", "Second", "CSE", "AA:BB:CC:DD:EE:02")
        self.repo.record_detection("AA:BB:CC:DD:EE:02", seen_at=late, late_after=time(9, 15))
        rows = {row["roll_number"]: row for row in self.repo.attendance_for_date("2026-10-14")}
        self.assertEqual(rows["R001"]["status"], "Present")
        self.assertEqual(rows["R002"]["status"], "Late")

    def test_default_behaviour_stays_present_without_cutoff(self) -> None:
        late = datetime(2026, 10, 14, 23, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.repo.record_detection("AA:BB:CC:DD:EE:FF", seen_at=late)
        self.assertEqual(self.repo.attendance_for_date("2026-10-14")[0]["status"], "Present")

    def test_update_and_delete_student(self) -> None:
        student = self.repo.list_students()[0]
        self.repo.update_student(student["id"], "R001X", "Renamed Student", "IT", "11-22-33-44-55-66")
        updated = self.repo.get_student(student["id"])
        self.assertEqual(updated["roll_number"], "R001X")
        self.assertEqual(updated["beacon_address"], "11:22:33:44:55:66")
        self.repo.delete_student(student["id"])
        self.assertIsNone(self.repo.get_student(student["id"]))

    def test_student_summary_and_low_attendance(self) -> None:
        when = datetime(2026, 10, 14, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.repo.record_detection("AA:BB:CC:DD:EE:FF", seen_at=when)
        self.repo.set_attendance_status(1, "2026-10-15", "Absent")
        summary = self.repo.student_summary("2026-10-14", "2026-10-15")[0]
        self.assertEqual(summary["present"], 1)
        self.assertEqual(summary["absent"], 1)
        self.assertEqual(summary["attendance_rate"], 50.0)
        self.assertEqual(len(self.repo.low_attendance_students("2026-10-14", "2026-10-15", 75)), 1)

    def test_detection_stats_and_clear_log(self) -> None:
        self.repo.record_detection("AA:BB:CC:DD:EE:FF", rssi=-40)
        self.repo.record_detection("00:00:00:00:00:00", rssi=-70)
        stats = self.repo.detection_stats()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["matched"], 1)
        self.assertEqual(stats["unknown"], 1)
        self.assertEqual(stats["best_rssi"], -40)
        self.repo.clear_detection_log()
        self.assertEqual(self.repo.detection_stats()["total"], 0)

    def test_attendance_between_returns_range_rows(self) -> None:
        when = datetime(2026, 10, 14, 9, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        self.repo.record_detection("AA:BB:CC:DD:EE:FF", seen_at=when)
        self.repo.set_attendance_status(1, "2026-10-20", "Excused")
        rows = self.repo.attendance_between("2026-10-14", "2026-10-15")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "Present")


if __name__ == "__main__":
    unittest.main()
