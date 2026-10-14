from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from .config import APP_TIMEZONE, DB_PATH


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_number TEXT NOT NULL UNIQUE COLLATE NOCASE,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    beacon_address TEXT NOT NULL UNIQUE COLLATE NOCASE,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    attendance_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Present'
        CHECK (status IN ('Present', 'Late', 'Absent', 'Excused')),
    first_seen TEXT,
    last_seen TEXT,
    detection_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    UNIQUE(student_id, attendance_date),
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS detection_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    device_address TEXT NOT NULL,
    device_name TEXT,
    rssi INTEGER,
    seen_at TEXT NOT NULL,
    FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(attendance_date);
CREATE INDEX IF NOT EXISTS idx_detection_seen_at ON detection_log(seen_at);
"""


def now_local() -> datetime:
    return datetime.now(ZoneInfo(APP_TIMEZONE)).replace(microsecond=0)


def normalize_address(address: str) -> str:
    return address.strip().upper().replace("-", ":")


class AttendanceRepository:
    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self.db_path = Path(db_path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    def add_student(self, roll_number: str, name: str, department: str, beacon_address: str) -> int:
        timestamp = now_local().isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """INSERT INTO students (roll_number, name, department, beacon_address, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (roll_number.strip(), name.strip(), department.strip(), normalize_address(beacon_address), timestamp),
            )
            return int(cursor.lastrowid)

    def list_students(self, active_only: bool = False) -> list[dict]:
        clause = "WHERE active = 1" if active_only else ""
        with self.connection() as conn:
            rows = conn.execute(f"SELECT * FROM students {clause} ORDER BY roll_number").fetchall()
        return [dict(row) for row in rows]

    def set_student_active(self, student_id: int, active: bool) -> None:
        with self.connection() as conn:
            conn.execute("UPDATE students SET active = ? WHERE id = ?", (int(active), student_id))

    def record_detection(
        self,
        address: str,
        name: str | None = None,
        rssi: int | None = None,
        seen_at: datetime | None = None,
        late_after: time | None = None,
    ) -> dict | None:
        """Log a device sighting and update daily attendance when it belongs to an active student.

        When ``late_after`` is provided, the first sighting of the day is recorded as
        ``Late`` instead of ``Present`` if it happens after that local time. Leaving it as
        ``None`` keeps the original behaviour where every first sighting is ``Present``.
        """
        with self.connection() as conn:
            return self._record_detection(conn, address, name, rssi, seen_at, late_after)

    def _record_detection(
        self,
        conn: sqlite3.Connection,
        address: str,
        name: str | None = None,
        rssi: int | None = None,
        seen_at: datetime | None = None,
        late_after: time | None = None,
    ) -> dict | None:
        """Core detection logic that operates on an existing connection."""
        timestamp = (seen_at or now_local()).replace(microsecond=0)
        address = normalize_address(address)
        student = conn.execute(
            "SELECT * FROM students WHERE beacon_address = ? AND active = 1", (address,)
        ).fetchone()
        student_id = student["id"] if student else None
        conn.execute(
            """INSERT INTO detection_log (student_id, device_address, device_name, rssi, seen_at)
               VALUES (?, ?, ?, ?, ?)""",
            (student_id, address, name, rssi, timestamp.isoformat()),
        )
        if not student:
            return None
        today = timestamp.date().isoformat()
        existing = conn.execute(
            "SELECT id FROM attendance WHERE student_id = ? AND attendance_date = ?",
            (student_id, today),
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE attendance SET last_seen = ?, detection_count = detection_count + 1
                   WHERE id = ?""",
                (timestamp.isoformat(), existing["id"]),
            )
        else:
            status = "Present"
            if late_after is not None and timestamp.time() > late_after:
                status = "Late"
            conn.execute(
                """INSERT INTO attendance
                   (student_id, attendance_date, status, first_seen, last_seen, detection_count)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (student_id, today, status, timestamp.isoformat(), timestamp.isoformat()),
            )
        return dict(student)

    def record_detections_bulk(self, entries: list[dict]) -> None:
        """Record many sightings in a single transaction (used for seeding/demos)."""
        with self.connection() as conn:
            for entry in entries:
                self._record_detection(conn, **entry)

    def set_attendance_status(
        self, student_id: int, attendance_date: str, status: str, notes: str = ""
    ) -> None:
        valid_statuses = {"Present", "Late", "Absent", "Excused"}
        if status not in valid_statuses:
            raise ValueError(f"status must be one of {sorted(valid_statuses)}")
        with self.connection() as conn:
            self._set_attendance_status(conn, student_id, attendance_date, status, notes)

    def _set_attendance_status(
        self,
        conn: sqlite3.Connection,
        student_id: int,
        attendance_date: str,
        status: str,
        notes: str = "",
    ) -> None:
        valid_statuses = {"Present", "Late", "Absent", "Excused"}
        if status not in valid_statuses:
            raise ValueError(f"status must be one of {sorted(valid_statuses)}")
        conn.execute(
            """INSERT INTO attendance (student_id, attendance_date, status, notes)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(student_id, attendance_date) DO UPDATE SET
                   status = excluded.status, notes = excluded.notes""",
            (student_id, attendance_date, status, notes.strip() or None),
        )

    def set_attendance_status_bulk(self, entries: list[dict]) -> None:
        """Apply many manual status changes in a single transaction."""
        with self.connection() as conn:
            for entry in entries:
                self._set_attendance_status(conn, **entry)

    def clear_attendance(self, student_id: int, attendance_date: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM attendance WHERE student_id = ? AND attendance_date = ?",
                (student_id, attendance_date),
            )

    def attendance_for_date(self, attendance_date: str | date) -> list[dict]:
        day = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT s.id AS student_id, s.roll_number, s.name, s.department, s.beacon_address,
                          COALESCE(a.status, 'Not marked') AS status, a.first_seen, a.last_seen,
                          COALESCE(a.detection_count, 0) AS detection_count, a.notes
                   FROM students s
                   LEFT JOIN attendance a ON a.student_id = s.id AND a.attendance_date = ?
                   WHERE s.active = 1
                   ORDER BY s.roll_number""",
                (day,),
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_detections(self, limit: int = 50) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT d.*, s.roll_number, s.name AS student_name
                   FROM detection_log d LEFT JOIN students s ON s.id = d.student_id
                   ORDER BY d.seen_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def summary(self, attendance_date: str | date) -> dict[str, int]:
        records = self.attendance_for_date(attendance_date)
        return {
            "registered": len(records),
            "present": sum(row["status"] in {"Present", "Late"} for row in records),
            "late": sum(row["status"] == "Late" for row in records),
            "absent": sum(row["status"] in {"Absent", "Not marked"} for row in records),
        }

    # --- Student management (additive helpers) -------------------------------
    def get_student(self, student_id: int) -> dict | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return dict(row) if row else None

    def update_student(
        self,
        student_id: int,
        roll_number: str,
        name: str,
        department: str,
        beacon_address: str,
    ) -> None:
        with self.connection() as conn:
            conn.execute(
                """UPDATE students
                   SET roll_number = ?, name = ?, department = ?, beacon_address = ?
                   WHERE id = ?""",
                (
                    roll_number.strip(),
                    name.strip(),
                    department.strip(),
                    normalize_address(beacon_address),
                    student_id,
                ),
            )

    def delete_student(self, student_id: int) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM students WHERE id = ?", (student_id,))

    # --- Detection log helpers ----------------------------------------------
    def clear_detection_log(self) -> None:
        with self.connection() as conn:
            conn.execute("DELETE FROM detection_log")

    def detection_stats(self) -> dict[str, int]:
        with self.connection() as conn:
            row = conn.execute(
                """SELECT COUNT(*) AS total,
                          COALESCE(SUM(student_id IS NOT NULL), 0) AS matched,
                          COALESCE(SUM(student_id IS NULL), 0) AS unknown,
                          COALESCE(MAX(rssi), 0) AS best_rssi
                   FROM detection_log"""
            ).fetchone()
        return {key: int(row[key]) for key in row.keys()}

    # --- Analytics & reporting ----------------------------------------------
    def student_summary(self, start: str | date, end: str | date) -> list[dict]:
        """Per-student attendance totals across an inclusive date range."""
        start_day = start.isoformat() if isinstance(start, date) else start
        end_day = end.isoformat() if isinstance(end, date) else end
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT s.id AS student_id, s.roll_number, s.name, s.department,
                          COALESCE(SUM(a.status = 'Present'), 0) AS present,
                          COALESCE(SUM(a.status = 'Late'), 0) AS late,
                          COALESCE(SUM(a.status = 'Absent'), 0) AS absent,
                          COALESCE(SUM(a.status = 'Excused'), 0) AS excused,
                          COUNT(a.id) AS marked
                   FROM students s
                   LEFT JOIN attendance a
                     ON a.student_id = s.id AND a.attendance_date BETWEEN ? AND ?
                   WHERE s.active = 1
                   GROUP BY s.id
                   ORDER BY s.roll_number""",
                (start_day, end_day),
            ).fetchall()
        summaries = []
        for row in rows:
            item = dict(row)
            marked = item["marked"] or 0
            present = item["present"] + item["late"]
            item["attendance_rate"] = round(present / marked * 100, 1) if marked else 0.0
            summaries.append(item)
        return summaries

    def daily_trend(self, start: str | date, end: str | date) -> list[dict]:
        """Present/late/absent counts per day across an inclusive date range."""
        start_day = start.isoformat() if isinstance(start, date) else start
        end_day = end.isoformat() if isinstance(end, date) else end
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT attendance_date,
                          COALESCE(SUM(status IN ('Present', 'Late')), 0) AS present,
                          COALESCE(SUM(status = 'Late'), 0) AS late,
                          COALESCE(SUM(status = 'Absent'), 0) AS absent
                   FROM attendance
                   WHERE attendance_date BETWEEN ? AND ?
                   GROUP BY attendance_date
                   ORDER BY attendance_date""",
                (start_day, end_day),
            ).fetchall()
        return [dict(row) for row in rows]

    def department_breakdown(self, attendance_date: str | date) -> list[dict]:
        day = attendance_date.isoformat() if isinstance(attendance_date, date) else attendance_date
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT s.department,
                          COUNT(s.id) AS registered,
                          COALESCE(SUM(a.status IN ('Present', 'Late')), 0) AS present,
                          COALESCE(SUM(a.status = 'Late'), 0) AS late
                   FROM students s
                   LEFT JOIN attendance a
                     ON a.student_id = s.id AND a.attendance_date = ?
                   WHERE s.active = 1
                   GROUP BY s.department
                   ORDER BY s.department""",
                (day,),
            ).fetchall()
        return [dict(row) for row in rows]

    def low_attendance_students(
        self, start: str | date, end: str | date, threshold: float = 75.0
    ) -> list[dict]:
        """Active students whose attendance rate is below the threshold."""
        return [row for row in self.student_summary(start, end) if row["attendance_rate"] < threshold]

    def attendance_between(self, start: str | date, end: str | date) -> list[dict]:
        """All marked attendance rows in an inclusive date range, newest first."""
        start_day = start.isoformat() if isinstance(start, date) else start
        end_day = end.isoformat() if isinstance(end, date) else end
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT a.attendance_date, s.roll_number, s.name, s.department,
                          a.status, a.first_seen, a.last_seen, a.detection_count, a.notes
                   FROM attendance a
                   JOIN students s ON s.id = a.student_id
                   WHERE a.attendance_date BETWEEN ? AND ?
                   ORDER BY a.attendance_date DESC, s.roll_number""",
                (start_day, end_day),
            ).fetchall()
        return [dict(row) for row in rows]
