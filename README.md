# Smart Attendance Using BLE

A college-ready attendance system that detects registered Bluetooth Low Energy (BLE) beacons nearby and records daily attendance in SQLite. It includes a Streamlit dashboard, an asynchronous BLE scanner, manual registration, CSV export, and a simulation mode for demos without physical beacons.

## Features

- Register students against a beacon MAC address / BLE device address.
- Scan nearby BLE devices with `bleak` and match them to registered students.
- Create one attendance record per student per day; repeated sightings update `last_seen` and `detection_count`.
- Live dashboard with today’s presence, student directory, detection log, and CSV download.
- Simulation mode uses real registration records and synthetic sightings, ideal for a classroom presentation.
- Local SQLite database—no cloud account or internet required.

### Dashboard features

- **Dashboard tab** — KPI cards, attendance-rate progress bar, a visual status board, inline attendance correction with a spreadsheet-style editor, and CSV export.
- **Analytics tab** — date-range reports, daily presence trend chart, department breakdown, per-student attendance rate, at-risk/defaulter list, and range CSV export.
- **Students tab** — search the directory, edit roll/name/department/beacon, activate/deactivate or delete students, and export the directory.
- **Detection log tab** — sighting statistics, matched/unknown filters, RSSI info, CSV export, and a guarded "clear log" action.
- **Optional late cut-off** — the sidebar can auto-mark a first sighting after a configurable local time as `Late` (off by default, so existing behaviour is unchanged).
- Modern themed UI powered by `.streamlit/config.toml` plus a built-in custom stylesheet.

## Project layout

```
app.py                    Streamlit dashboard
cli.py                    Command-line setup, scan, simulation and export
.streamlit/config.toml    Dashboard theme
attendance/
  config.py               Paths, timezone and late cut-off settings
  database.py             SQLite schema and data-access layer
  scanner.py              BLE scan and beacon matching service
  simulator.py            Hardware-free demonstration helpers
tests/test_database.py    Core database tests
```

## Setup

1. Install Python 3.10 or newer.
2. Create and activate a virtual environment.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Create the database and sample records:

   ```powershell
   python cli.py init --sample-data
   ```

4. Start the dashboard:

   ```powershell
   streamlit run app.py
   ```

The database is stored at `data/attendance.db` by default. Override it with the `ATTENDANCE_DB_PATH` environment variable if required.

## Using real BLE beacons

1. Program each beacon (or use a BLE phone app) to advertise consistently.
2. Find its BLE address using `python cli.py scan`.
3. Register that address with the student in **Students** on the dashboard.
4. Run **Scan now** in the dashboard or `python cli.py scan` periodically.

BLE addresses may be randomized by some phones, and operating systems can restrict scanning permissions. Dedicated beacons with stable addresses are most reliable. On Linux, Bluetooth permissions may require the user to be in the `bluetooth` group. On Windows, turn Bluetooth on and allow device discovery.

## Commands

```powershell
python cli.py init --sample-data     # Create database and optional example students
python cli.py scan --timeout 8       # Scan and store real nearby detections
python cli.py simulate --count 3     # Store fake sightings for a demo
python cli.py export --date 2026-10-14
python -m unittest discover -s tests -v
```

## Attendance rule

When a registered beacon is detected, its student is marked **Present** for the current local date. The first detection establishes check-in time; later detections are preserved as last-seen time and a count. An instructor can mark a student **Late**, **Absent**, or **Excused** manually from the dashboard.

## Limitations and ethical notes

BLE proximity is an aid, not proof of identity: beacons can be shared, relayed, or left behind. Use this as one input to attendance, publish a privacy notice, collect only needed data, protect the database, and provide a correction process. Do not use the system for covert tracking.
