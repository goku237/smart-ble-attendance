from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from attendance.config import DB_PATH
from attendance.database import AttendanceRepository
from attendance.scanner import scan_once
from attendance.simulator import seed_sample_students, simulate_detections


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart BLE attendance manager")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="SQLite database location")
    sub = parser.add_subparsers(dest="command", required=True)
    init_parser = sub.add_parser("init", help="Create the attendance database")
    init_parser.add_argument("--sample-data", action="store_true")
    scan_parser = sub.add_parser("scan", help="Scan nearby BLE devices and record matching students")
    scan_parser.add_argument("--timeout", type=float, default=8.0)
    sim_parser = sub.add_parser("simulate", help="Record synthetic beacon sightings")
    sim_parser.add_argument("--count", type=int, default=None)
    export_parser = sub.add_parser("export", help="Export a daily attendance CSV")
    export_parser.add_argument("--date", default=date.today().isoformat())
    export_parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    repo = AttendanceRepository(args.db)
    repo.initialize()
    if args.command == "init":
        added = seed_sample_students(repo) if args.sample_data else 0
        print(f"Database ready: {args.db}. Sample students added: {added}")
    elif args.command == "scan":
        results = scan_once(repo, args.timeout)
        matches = [r for r in results if r["registered_student"]]
        print(f"Found {len(results)} BLE device(s); matched {len(matches)} student(s).")
        for result in matches:
            print(f"  Present: {result['registered_student']} ({result['address']})")
    elif args.command == "simulate":
        names = simulate_detections(repo, args.count)
        print("Simulated attendance for: " + (", ".join(names) if names else "no students registered"))
    elif args.command == "export":
        rows = repo.attendance_for_date(args.date)
        output = args.output or Path(f"attendance-{args.date}.csv")
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["student_id", "roll_number", "name", "status"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Exported {len(rows)} row(s) to {output}")


if __name__ == "__main__":
    main()
