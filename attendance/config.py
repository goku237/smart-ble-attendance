from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "attendance.db"
DB_PATH = Path(os.environ.get("ATTENDANCE_DB_PATH", DEFAULT_DB_PATH))
APP_TIMEZONE = os.environ.get("ATTENDANCE_TIMEZONE", "Asia/Kolkata")

# Local time after which a first sighting of the day is recorded as "Late".
LATE_CUTOFF = os.environ.get("ATTENDANCE_LATE_CUTOFF", "09:15")
