import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, render_template, request
from auth import login_required
from db import get_conn, get_attempt_summary, get_attempts, get_time_breakdown, get_topics, track_page_time

progress_bp = Blueprint("progress", __name__)


def _fmt_seconds_today(total: int) -> str:
    m = total // 60
    s = total % 60
    if m >= 60:
        return f"{m}m"
    return f"{m}m {s}s"


def _fmt_seconds_week(total: int) -> str:
    m = total // 60
    return f"{m}m"


@progress_bp.route("/progress")
@login_required
def progress_page():
    conn = get_conn()
    user_id = g.user_id
    track_page_time(conn, "My Progress")

    summary = get_attempt_summary(conn, user_id=user_id)

    today_raw = get_time_breakdown(conn, user_id, days=1)
    week_raw = get_time_breakdown(conn, user_id, days=7)

    today_max = max((r["total_seconds"] or 0 for r in today_raw), default=1) or 1
    week_max = max((r["total_seconds"] or 0 for r in week_raw), default=1) or 1

    today_time = [
        {
            "page_name": r["page_name"],
            "label": _fmt_seconds_today(r["total_seconds"] or 0),
            "pct": round((r["total_seconds"] or 0) / today_max * 100),
        }
        for r in today_raw
    ]
    week_time = [
        {
            "page_name": r["page_name"],
            "label": _fmt_seconds_week(r["total_seconds"] or 0),
            "pct": round((r["total_seconds"] or 0) / week_max * 100),
        }
        for r in week_raw
    ]

    topic_filter = request.args.get("topic", "all")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    topic_id_filter = None if topic_filter == "all" else topic_filter
    attempts = get_attempts(
        conn,
        topic_id=topic_id_filter,
        date_from=date_from or None,
        date_to=date_to or None,
        user_id=user_id,
    )

    table_rows = []
    for a in attempts:
        table_rows.append({
            "Date": a["created_at"][:10] if a["created_at"] else "—",
            "Topic": (a.get("topic_id") or "").replace("_", " ").title(),
            "Paper": (a.get("paper_id") or "").upper().replace("_", "-"),
            "Year": a.get("year") or "—",
            "Marks": a.get("marks") or "—",
            "Words": (
                (a.get("word_count_intro") or 0)
                + (a.get("word_count_body") or 0)
                + (a.get("word_count_conclusion") or 0)
            ),
        })

    recent = attempts[:5]

    all_topics = get_topics(conn)

    top_topic_display = None
    if summary.get("top_topic"):
        top_topic_display = summary["top_topic"].replace("_", " ").title()

    return render_template(
        "progress.html",
        active_page="progress",
        summary=summary,
        top_topic_display=top_topic_display,
        today_time=today_time,
        week_time=week_time,
        topic_filter=topic_filter,
        date_from=date_from,
        date_to=date_to,
        all_topics=all_topics,
        table_rows=table_rows,
        recent=recent,
    )


@progress_bp.route("/progress/review")
@login_required
def answer_review():
    conn = get_conn()
    user_id = g.user_id
    track_page_time(conn, "Answer Review")

    row = conn.execute(
        "SELECT subscription_tier FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    is_pro = bool(row and row["subscription_tier"] == "pro")

    return render_template(
        "answer_review.html",
        active_page="answer_review",
        is_pro=is_pro,
    )
