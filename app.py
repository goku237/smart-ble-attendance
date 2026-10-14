from __future__ import annotations

import html
from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st

from attendance.config import APP_TIMEZONE, DB_PATH, LATE_CUTOFF
from attendance.database import AttendanceRepository
from attendance.scanner import scan_once
from attendance.simulator import seed_sample_students, simulate_detections


STATUS_OPTIONS = ["Present", "Late", "Absent", "Excused"]
STATUS_CLASS = {
    "Present": "present",
    "Late": "late",
    "Absent": "absent",
    "Excused": "excused",
    "Not marked": "notmarked",
}
ENTERABLE_STATUSES = STATUS_OPTIONS + ["Not marked"]

THEME_CSS = """
<style>
.stApp {
    background:
        radial-gradient(1200px 600px at 8% -12%, #eef2ff 0%, transparent 55%),
        radial-gradient(1000px 520px at 112% 6%, #f5f3ff 0%, transparent 50%),
        #f8fafc;
}
.block-container { padding-top: 2.2rem; max-width: 1250px; }

.hero {
    background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 48%, #9333ea 100%);
    border-radius: 22px;
    padding: 30px 34px;
    color: #ffffff;
    box-shadow: 0 20px 42px -20px rgba(79, 70, 229, .7);
    margin-bottom: 14px;
}
.hero h1 { font-size: 2.05rem; margin: 0 0 8px; font-weight: 800; letter-spacing: -0.03em; }
.hero p { margin: 0; opacity: .92; font-size: 1rem; }
.hero .tag {
    display: inline-block; margin-top: 16px; padding: 5px 13px; border-radius: 999px;
    background: rgba(255, 255, 255, .16); border: 1px solid rgba(255, 255, 255, .3);
    font-size: .78rem; font-weight: 600; letter-spacing: .02em;
}

[data-testid="stMetric"] {
    background: #ffffff; border: 1px solid #ececf5; border-radius: 16px;
    padding: 16px 18px; box-shadow: 0 8px 26px -20px rgba(15, 23, 42, .5);
    transition: transform .15s ease, box-shadow .15s ease;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 16px 32px -20px rgba(79, 70, 229, .55); }
[data-testid="stMetricLabel"] p {
    font-weight: 700; color: #64748b; font-size: .78rem;
    text-transform: uppercase; letter-spacing: .05em;
}
[data-testid="stMetricValue"] { font-weight: 800; color: #1e1b4b; }

.stButton > button, .stDownloadButton > button {
    border-radius: 12px; font-weight: 600; border: 1px solid #e2e8f0;
    transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover { transform: translateY(-1px); }
.stButton > button[kind="primary"] {
    background: linear-gradient(120deg, #4f46e5, #7c3aed); border: none;
    box-shadow: 0 12px 24px -14px rgba(79, 70, 229, .95);
}

.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] { border-radius: 12px 12px 0 0; padding: 9px 18px; font-weight: 600; }
.stTabs [aria-selected="true"] { background: #eef2ff; color: #4338ca; }

[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #e2e8f0; }
[data-testid="stSidebar"] .stButton > button { background: #1e293b; border-color: #334155; color: #e2e8f0; }
[data-testid="stSidebar"] .stButton > button[kind="primary"] { background: linear-gradient(120deg, #6366f1, #8b5cf6); border: none; }

.brand { display: flex; align-items: center; gap: 12px; padding: 4px 0 6px; }
.brand-dot {
    display: grid; place-items: center; width: 46px; height: 46px; border-radius: 14px;
    background: linear-gradient(135deg, #6366f1, #a855f7); font-size: 1.4rem;
    box-shadow: 0 10px 22px -12px rgba(99, 102, 241, .9);
}
.brand-title { font-size: 1.08rem; font-weight: 800; color: #f8fafc; letter-spacing: -.02em; }
.brand-sub { font-size: .76rem; color: #94a3b8; }
.side-stat { display: flex; justify-content: space-between; padding: 7px 0; border-bottom: 1px dashed #1e293b; font-size: .86rem; }
.side-stat span:first-child { color: #94a3b8; }
.side-stat span:last-child { color: #f1f5f9; font-weight: 700; }

.pill {
    display: inline-block; padding: 3px 11px; border-radius: 999px;
    font-size: .74rem; font-weight: 700; letter-spacing: .01em;
}
.pill.present { background: #dcfce7; color: #15803d; }
.pill.late { background: #fef3c7; color: #b45309; }
.pill.absent { background: #fee2e2; color: #b91c1c; }
.pill.excused { background: #dbeafe; color: #1d4ed8; }
.pill.notmarked { background: #e2e8f0; color: #475569; }

.sboard { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; margin-top: 6px; }
.sboard-card {
    background: #ffffff; border: 1px solid #ececf5; border-radius: 14px; padding: 14px 16px;
    box-shadow: 0 8px 22px -20px rgba(15, 23, 42, .6);
}
.sboard-name { font-weight: 700; color: #1e1b4b; font-size: .95rem; }
.sboard-roll { font-size: .76rem; color: #94a3b8; margin-bottom: 10px; }
</style>
"""


def inject_theme() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>Smart Attendance Using BLE</h1>
            <p>Detect registered Bluetooth Low Energy beacons nearby and keep a live,
               local attendance record — no cloud, no internet required.</p>
            <span class="tag">LIVE PROXIMITY CHECK-IN</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pill(status: str) -> str:
    css = STATUS_CLASS.get(status, "notmarked")
    return f'<span class="pill {css}">{html.escape(status)}</span>'


def status_board(records: list[dict]) -> None:
    cards = []
    for row in records:
        cards.append(
            f'<div class="sboard-card">'
            f'<div class="sboard-name">{html.escape(str(row["name"]))}</div>'
            f'<div class="sboard-roll">{html.escape(str(row["roll_number"]))} · '
            f'{html.escape(str(row["department"]))}</div>'
            f'{pill(row["status"])}'
            f"</div>"
        )
    st.markdown(f'<div class="sboard">{"".join(cards)}</div>', unsafe_allow_html=True)


def parse_cutoff(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return time(9, 15)


def attendance_csv(rows: list[dict], columns: list[str] | None = None) -> bytes:
    frame = pd.DataFrame(rows)
    if columns:
        frame = frame[[column for column in columns if column in frame.columns]]
    return frame.to_csv(index=False).encode("utf-8")


st.set_page_config(
    page_title="Smart BLE Attendance",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()

repo = AttendanceRepository()
repo.initialize()

defaults = {
    "scan_results": None,
    "scan_note": None,
    "last_scan_at": None,
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


hero()

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-dot">📡</div>
            <div>
                <div class="brand-title">BLE Attendance</div>
                <div class="brand-sub">Smart proximity check-in</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.subheader("Scanner")
    timeout = st.slider("Scan duration (seconds)", 3, 20, 8)
    use_cutoff = st.toggle("Auto-mark late arrivals", value=False,
                           help="When enabled, the first sighting of the day after the cutoff is marked Late.")
    cutoff_time = st.time_input("Late after", value=parse_cutoff(LATE_CUTOFF), disabled=not use_cutoff)
    late_after = cutoff_time if use_cutoff else None

    if st.button("Scan now", type="primary", width="stretch"):
        with st.spinner("Scanning for nearby BLE devices..."):
            try:
                scanned = scan_once(repo, timeout, late_after=late_after)
                matched = [item for item in scanned if item["registered_student"]]
                st.session_state.scan_results = scanned
                st.session_state.scan_note = (
                    "success",
                    f"Found {len(scanned)} device(s), matched {len(matched)} student(s).",
                )
                st.session_state.last_scan_at = datetime.now()
            except Exception as exc:
                st.session_state.scan_note = ("error", f"Scan could not run: {exc}")
        st.rerun()

    if st.button("Run demo simulation", width="stretch"):
        names = simulate_detections(repo)
        st.session_state.scan_note = (
            "success",
            "Recorded simulated sightings for: " + (", ".join(names) if names else "no students"),
        )
        st.rerun()

    if st.session_state.scan_note:
        kind, message = st.session_state.scan_note
        (st.success if kind == "success" else st.error)(message)

    if st.session_state.last_scan_at:
        st.caption(f"Last scan: {st.session_state.last_scan_at.strftime('%d %b %H:%M:%S')}")

    if st.session_state.scan_results is not None:
        if st.button("Clear scan results", width="stretch"):
            st.session_state.scan_results = None
            st.session_state.scan_note = None
            st.session_state.last_scan_at = None
            st.rerun()

    st.divider()
    quick = repo.summary(date.today())
    st.markdown("#### Today at a glance")
    st.markdown(
        f"""
        <div class="side-stat"><span>Registered</span><span>{quick['registered']}</span></div>
        <div class="side-stat"><span>Present</span><span>{quick['present']}</span></div>
        <div class="side-stat"><span>Late</span><span>{quick['late']}</span></div>
        <div class="side-stat"><span>Absent / unmarked</span><span>{quick['absent']}</span></div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    if st.button("Seed sample students", width="stretch"):
        added = seed_sample_students(repo)
        st.success(f"Added {added} sample student(s).")
    if st.button("Refresh data", width="stretch"):
        st.rerun()
    st.caption(f"DB: {DB_PATH.name}  ·  {APP_TIMEZONE}")

dashboard, analytics, students_page, logs_page = st.tabs(
    ["📊 Dashboard", "📈 Analytics", "👥 Students", "🗂️ Detection log"]
)

with dashboard:
    selected_date = st.date_input("Attendance date", value=date.today())
    summary = repo.summary(selected_date)
    records = repo.attendance_for_date(selected_date)
    rate = round(summary["present"] / summary["registered"] * 100, 1) if summary["registered"] else 0.0

    cols = st.columns(4)
    cols[0].metric("Registered", summary["registered"])
    cols[1].metric("Present", summary["present"])
    cols[2].metric("Late", summary["late"])
    cols[3].metric("Absent / unmarked", summary["absent"])
    st.progress(min(rate / 100, 1.0), text=f"Attendance rate for {selected_date.strftime('%d %b %Y')}: {rate}%")

    if st.session_state.scan_results is not None:
        with st.expander(f"🔎 Latest scan — {len(st.session_state.scan_results)} device(s)", expanded=True):
            scan_df = pd.DataFrame(st.session_state.scan_results)
            if not scan_df.empty:
                scan_df = scan_df.rename(
                    columns={
                        "address": "Address",
                        "name": "Advertised name",
                        "rssi": "RSSI (dBm)",
                        "registered_student": "Matched student",
                    }
                )
                st.dataframe(scan_df, hide_index=True, width="stretch")

    st.subheader("Daily attendance")
    if not records:
        st.info("Register students to start recording attendance.")
    else:
        view = pd.DataFrame(records).reset_index(drop=True)
        st.dataframe(
            view.drop(columns=["student_id"]),
            hide_index=True,
            width="stretch",
        )
        st.download_button(
            "⬇️ Download CSV",
            attendance_csv(records),
            file_name=f"attendance-{selected_date.isoformat()}.csv",
            mime="text/csv",
        )
        with st.expander("🎚️ Visual status board"):
            status_board(records)

        st.subheader("Correct attendance")
        st.caption("Edit any cell below and save. Use “Not marked” to clear an entry.")
        editable = view[["roll_number", "name", "department", "status", "detection_count", "notes"]].copy()
        edited = st.data_editor(
            editable,
            key=f"editor-{selected_date.isoformat()}",
            hide_index=True,
            width="stretch",
            disabled=["roll_number", "name", "department", "detection_count"],
            column_config={
                "status": st.column_config.SelectboxColumn(
                    "Status", options=ENTERABLE_STATUSES, required=True
                ),
                "notes": st.column_config.TextColumn("Notes"),
                "detection_count": st.column_config.NumberColumn("Sightings"),
            },
        )
        if st.button("💾 Save changes", key=f"save-{selected_date.isoformat()}"):
            changes = 0
            for index in range(len(view)):
                student_id = int(view.at[index, "student_id"])
                old_status = view.at[index, "status"]
                old_notes = view.at[index, "notes"] or ""
                new_status = edited.at[index, "status"]
                new_notes = edited.at[index, "notes"] or ""
                if new_status == old_status and new_notes == old_notes:
                    continue
                if new_status == "Not marked":
                    repo.clear_attendance(student_id, selected_date.isoformat())
                else:
                    repo.set_attendance_status(
                        student_id, selected_date.isoformat(), new_status, new_notes
                    )
                changes += 1
            if changes:
                st.success(f"Updated {changes} record(s).")
                st.rerun()
            else:
                st.info("No changes to save.")

with analytics:
    st.subheader("Attendance analytics")
    default_start = date.today() - timedelta(days=6)
    range_cols = st.columns(2)
    start_date = range_cols[0].date_input("From", value=default_start, key="range-start")
    end_date = range_cols[1].date_input("To", value=date.today(), key="range-end")
    if start_date > end_date:
        st.warning("The start date is after the end date.")
        start_date, end_date = end_date, start_date

    summary_rows = repo.student_summary(start_date, end_date)
    total_marked = sum(row["marked"] for row in summary_rows)
    total_present = sum(row["present"] + row["late"] for row in summary_rows)
    overall = round(total_present / total_marked * 100, 1) if total_marked else 0.0
    active_count = len(summary_rows)

    kpi = st.columns(3)
    kpi[0].metric("Overall attendance", f"{overall}%")
    kpi[1].metric("Attendance records", total_marked)
    kpi[2].metric("Active students", active_count)

    trend = repo.daily_trend(start_date, end_date)
    if trend:
        trend_df = pd.DataFrame(trend).set_index("attendance_date")
        trend_df = trend_df.rename(
            columns={"present": "Present", "late": "Late", "absent": "Absent"}
        )
        st.markdown("##### Daily presence trend")
        st.line_chart(trend_df, height=320, color=["#4f46e5", "#f59e0b", "#ef4444"])
    else:
        st.info("No attendance recorded in this range yet.")

    dept = repo.department_breakdown(end_date)
    if dept:
        dept_df = pd.DataFrame(dept).set_index("department")
        dept_df = dept_df.rename(columns={"registered": "Registered", "present": "Present", "late": "Late"})
        st.markdown(f"##### Department breakdown — {end_date.strftime('%d %b %Y')}")
        st.bar_chart(dept_df[["Registered", "Present"]], height=300, color=["#c7d2fe", "#4f46e5"])

    if summary_rows:
        st.markdown("##### Per-student attendance")
        table = pd.DataFrame(summary_rows).drop(columns=["student_id"])
        st.dataframe(
            table,
            hide_index=True,
            width="stretch",
            column_config={
                "attendance_rate": st.column_config.ProgressColumn(
                    "Attendance %", min_value=0, max_value=100, format="%.1f%%"
                ),
                "marked": st.column_config.NumberColumn("Days marked"),
            },
        )
        st.download_button(
            "⬇️ Download range report (CSV)",
            attendance_csv(summary_rows, columns=list(table.columns)),
            file_name=f"attendance-report-{start_date.isoformat()}-to-{end_date.isoformat()}.csv",
            mime="text/csv",
        )

        st.markdown("##### Students needing attention")
        threshold = st.slider("Flag below attendance %", 0, 100, 75, step=5)
        at_risk = [row for row in summary_rows if row["attendance_rate"] < threshold]
        if at_risk:
            st.dataframe(
                pd.DataFrame(at_risk).drop(columns=["student_id"]),
                hide_index=True,
                width="stretch",
            )
        else:
            st.success(f"All students are at or above {threshold}%.")

    st.markdown("##### Full attendance log in range")
    range_rows = repo.attendance_between(start_date, end_date)
    if range_rows:
        st.dataframe(pd.DataFrame(range_rows), hide_index=True, width="stretch")
    else:
        st.caption("Nothing recorded for this range.")

with students_page:
    left, right = st.columns([1, 1.4])
    with left:
        st.subheader("Register student")
        with st.form("add-student", clear_on_submit=True):
            roll = st.text_input("Roll number")
            name = st.text_input("Full name")
            department = st.text_input("Department", value="Computer Science")
            beacon = st.text_input("BLE address", placeholder="AA:BB:CC:DD:EE:FF")
            submitted = st.form_submit_button("Register")
        if submitted:
            if not all([roll.strip(), name.strip(), department.strip(), beacon.strip()]):
                st.warning("Complete every field.")
            else:
                try:
                    repo.add_student(roll, name, department, beacon)
                    st.success("Student registered.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not register student: {exc}")

    with right:
        st.subheader("Manage students")
        all_students = repo.list_students()
        if not all_students:
            st.info("No registered students yet.")
        else:
            query = st.text_input("Search", placeholder="Filter by name, roll, department or address")
            filtered = [
                student
                for student in all_students
                if not query
                or query.lower() in " ".join(str(value) for value in student.values()).lower()
            ]
            directory = pd.DataFrame(filtered if filtered else all_students)
            directory["active"] = directory["active"].map({1: "Yes", 0: "No"})
            st.dataframe(
                directory.drop(columns=["id"]),
                hide_index=True,
                width="stretch",
            )
            st.download_button(
                "⬇️ Export directory (CSV)",
                attendance_csv(all_students),
                file_name="students.csv",
                mime="text/csv",
            )

            labels = {f"{s['roll_number']} — {s['name']}": s for s in all_students}
            picked = st.selectbox("Select a student to edit", list(labels), key="manage-pick")
            student = labels[picked]
            sid = int(student["id"])

            with st.form(f"edit-{sid}"):
                edit_cols = st.columns(2)
                new_roll = edit_cols[0].text_input("Roll number", student["roll_number"], key=f"roll-{sid}")
                new_name = edit_cols[1].text_input("Full name", student["name"], key=f"name-{sid}")
                new_dept = edit_cols[0].text_input("Department", student["department"], key=f"dept-{sid}")
                new_beacon = edit_cols[1].text_input("BLE address", student["beacon_address"], key=f"beacon-{sid}")
                if st.form_submit_button("Save changes"):
                    try:
                        repo.update_student(sid, new_roll, new_name, new_dept, new_beacon)
                        st.success("Student updated.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not update student: {exc}")

            action_cols = st.columns(2)
            is_active = bool(student["active"])
            if action_cols[0].button("Deactivate" if is_active else "Activate", key=f"toggle-{sid}"):
                repo.set_student_active(sid, not is_active)
                st.rerun()
            if action_cols[1].button("🗑️ Delete student", key=f"delete-{sid}"):
                st.session_state["confirm-delete"] = sid
            if st.session_state.get("confirm-delete") == sid:
                st.warning(f"Delete {student['name']} and all their attendance records? This cannot be undone.")
                confirm_cols = st.columns(2)
                if confirm_cols[0].button("Yes, delete", type="primary", key=f"confirm-yes-{sid}"):
                    repo.delete_student(sid)
                    st.session_state.pop("confirm-delete", None)
                    st.success("Student deleted.")
                    st.rerun()
                if confirm_cols[1].button("Cancel", key=f"confirm-no-{sid}"):
                    st.session_state.pop("confirm-delete", None)
                    st.rerun()

with logs_page:
    st.subheader("Detection log")
    stats = repo.detection_stats()
    stat_cols = st.columns(4)
    stat_cols[0].metric("Total sightings", stats["total"])
    stat_cols[1].metric("Matched", stats["matched"])
    stat_cols[2].metric("Unknown devices", stats["unknown"])
    stat_cols[3].metric("Strongest RSSI", f"{stats['best_rssi']} dBm")

    filter_cols = st.columns([1, 1, 1])
    only_matched = filter_cols[0].toggle("Only matched students", value=False)
    only_unknown = filter_cols[1].toggle("Only unknown devices", value=False)
    limit = filter_cols[2].slider("Max rows", 10, 500, 100, step=10)

    logs = repo.recent_detections(limit)
    frame = pd.DataFrame(logs)
    if frame.empty:
        st.info("No detections logged yet.")
    else:
        if only_matched:
            frame = frame[frame["student_id"].notna()]
        if only_unknown:
            frame = frame[frame["student_id"].isna()]
        display = frame.rename(
            columns={
                "roll_number": "Roll",
                "student_name": "Student",
                "device_address": "Address",
                "device_name": "Advertised name",
                "rssi": "RSSI (dBm)",
                "seen_at": "Seen at",
            }
        ).drop(columns=["id", "student_id"], errors="ignore")
        st.dataframe(display, hide_index=True, width="stretch")
        st.download_button(
            "⬇️ Export log (CSV)",
            attendance_csv(display.to_dict("records")),
            file_name="detection-log.csv",
            mime="text/csv",
        )

    confirm_clear = st.checkbox("Confirm clearing the entire detection log")
    if st.button("🧹 Clear detection log", disabled=not confirm_clear):
        repo.clear_detection_log()
        st.success("Detection log cleared.")
        st.rerun()
