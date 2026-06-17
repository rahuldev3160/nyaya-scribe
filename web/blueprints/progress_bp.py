import datetime
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, render_template
from auth import login_required
from db import get_conn, get_nyaya_conn, track_page_time

progress_bp = Blueprint("progress", __name__)

# Maps page_name values in user_events to exam labels for the macro time view.
_PAGE_EXAM = {
    "Dashboard":         "IES 2026",
    "Quiz":              "IES 2026",
    "Return Quiz":       "IES 2026",
    "model_answers":     "IES 2026",
    "Study Brief":       "IES 2026",
    "RBI Dashboard":     "RBI Grade B",
    "RBI Prep":          "RBI Grade B",
    "UPSC Dashboard":    "UPSC Mains",
    "upsc_mains":        "UPSC Mains",
    "English Dashboard": "English",
    "English Practice":  "English",
}

_EXAM_ORDER  = ["IES 2026", "RBI Grade B", "UPSC Mains", "English"]
_EXAM_COLORS = {
    "IES 2026":    "#8AB4F8",
    "RBI Grade B": "#81C995",
    "UPSC Mains":  "#FDD663",
    "English":     "#C084FC",
}
_EXAM_LINKS = {
    "IES 2026":    "/dashboard",
    "RBI Grade B": "/rbi",
    "UPSC Mains":  "/upsc",
    "English":     "/english/dashboard",
}
def _get_exam_dates() -> list[dict]:
    _DATA = Path(__file__).parent.parent.parent / "data"
    exams = [
        {"exam_id": "ies_2026",    "name": "IES 2026",     "fallback": "2026-06-19", "link": "/dashboard", "color": "#8AB4F8", "db": "ies.db"},
        {"exam_id": "rbi_depr",    "name": "RBI Grade B",  "fallback": "2026-06-14", "link": "/rbi",       "color": "#81C995", "db": "rbi.db"},
        {"exam_id": "upsc_eco_opt","name": "UPSC Eco Opt", "fallback": "2026-08-22", "link": "/upsc",      "color": "#FDD663", "db": "upsc_eco_opt.db"},
    ]
    result = []
    for e in exams:
        date_str = e["fallback"]
        try:
            db_path = _DATA / e["db"]
            if db_path.exists():
                conn = sqlite3.connect(str(db_path))
                row = conn.execute(
                    "SELECT exam_date FROM exam_configurations WHERE exam_id=?", (e["exam_id"],)
                ).fetchone()
                conn.close()
                if row and row[0]:
                    date_str = row[0]
        except Exception:
            pass
        result.append({
            "name": e["name"],
            "date": datetime.date.fromisoformat(date_str),
            "link": e["link"],
            "color": e["color"],
        })
    return result


def _seconds_label(s: int) -> str:
    m = s // 60
    if m >= 60:
        return f"{m // 60}h {m % 60}m"
    return f"{m}m"


@progress_bp.route("/progress")
@login_required
def progress_page():
    conn = get_conn()
    user_id = g.user_id
    track_page_time(conn, "My Progress")
    nc = get_nyaya_conn()

    def _time_rows(days: int) -> list[dict]:
        rows = nc.execute(
            "SELECT entity_id AS page_name, "
            "SUM(CAST(json_extract(payload,'$.duration_s') AS INTEGER)) AS total_seconds "
            "FROM user_events "
            "WHERE user_id=? AND event_type='page_view' "
            "AND created_at >= datetime('now', ? || ' days') "
            "GROUP BY entity_id ORDER BY total_seconds DESC",
            (user_id, f"-{days}"),
        ).fetchall()
        return [dict(r) for r in rows]

    def _to_exam_buckets(raw: list[dict]) -> list[dict]:
        buckets: dict[str, int] = {}
        for r in raw:
            exam = _PAGE_EXAM.get(r["page_name"] or "", None)
            if exam:
                buckets[exam] = buckets.get(exam, 0) + (r["total_seconds"] or 0)
        mx = max(buckets.values(), default=1) or 1
        return [
            {
                "exam":  exam,
                "label": _seconds_label(buckets.get(exam, 0)),
                "pct":   round(buckets.get(exam, 0) / mx * 100),
                "color": _EXAM_COLORS[exam],
                "link":  _EXAM_LINKS[exam],
                "secs":  buckets.get(exam, 0),
            }
            for exam in _EXAM_ORDER
            if buckets.get(exam, 0) > 0
        ]

    today_buckets = _to_exam_buckets(_time_rows(1))
    week_buckets  = _to_exam_buckets(_time_rows(7))

    today_date = datetime.date.today()
    exam_dates = _get_exam_dates()
    countdowns = [
        {**e,
         "days_left": max((e["date"] - today_date).days, 0),
         "past":      (e["date"] - today_date).days < 0,
         "urgent":    0 <= (e["date"] - today_date).days <= 7,
        }
        for e in exam_dates
    ]

    return render_template(
        "progress.html",
        active_page="progress",
        today_buckets=today_buckets,
        week_buckets=week_buckets,
        countdowns=countdowns,
    )


@progress_bp.route("/progress/review")
@login_required
def answer_review():
    conn = get_conn()
    nyaya_conn = get_nyaya_conn()
    user_id = g.user_id
    track_page_time(conn, "Answer Review")

    row = nyaya_conn.execute(
        "SELECT subscription_tier FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    is_pro = bool(row and row["subscription_tier"] == "pro")

    return render_template(
        "answer_review.html",
        active_page="answer_review",
        is_pro=is_pro,
    )
