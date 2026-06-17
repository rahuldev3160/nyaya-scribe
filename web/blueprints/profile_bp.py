import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_DATA = Path(__file__).parent.parent.parent / "data"

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from auth import login_required
from db import get_conn, get_nyaya_conn, log_event, track_page_time

profile_bp = Blueprint("profile_bp", __name__)

EXAM_LABELS = {
    "ies": "IES 2026",
    "rbi": "RBI DEPR",
    "upsc": "UPSC Eco Optional",
}


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile_page():
    conn = get_conn()
    nyaya_conn = get_nyaya_conn()
    user_id = g.user_id
    track_page_time(conn, "Profile")

    if request.method == "POST":
        phone = request.form.get("phone_number", "").strip()
        old_row = nyaya_conn.execute(
            "SELECT phone_number FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        old_phone = old_row["phone_number"] if old_row else None
        nyaya_conn.execute(
            "UPDATE users SET phone_number=? WHERE user_id=?",
            (phone, user_id),
        )
        nyaya_conn.commit()
        try:
            if phone != (old_phone or ""):
                log_event("config_changed", payload={"field": "phone_number", "old_value": old_phone, "new_value": phone})
        except Exception:
            pass
        flash("Contact details saved.", "success")
        return redirect(url_for("profile_bp.profile_page"))

    user = nyaya_conn.execute(
        "SELECT display_name, email, avatar_url, created_at, subscription_tier, phone_number, "
        "exam_focus, exam_date, onboarding_completed FROM users WHERE user_id=?",
        (user_id,),
    ).fetchone()

    ies_answers = conn.execute(
        "SELECT COUNT(*) FROM descriptive_attempts WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    upsc_answers = 0
    upsc_mcqs = 0
    upsc_db = _DATA / "upsc_eco_opt.db"
    if upsc_db.exists():
        try:
            _upsc = sqlite3.connect(str(upsc_db), check_same_thread=False)
            _upsc.row_factory = sqlite3.Row
            upsc_answers = _upsc.execute(
                "SELECT COUNT(*) FROM descriptive_attempts WHERE user_id=?", (user_id,)
            ).fetchone()[0]
            upsc_mcqs = _upsc.execute(
                "SELECT COUNT(*) FROM return_quiz_attempts WHERE user_id=?", (user_id,)
            ).fetchone()[0]
            _upsc.close()
        except Exception:
            pass

    answers_graded = ies_answers + upsc_answers

    ies_mcqs = conn.execute(
        "SELECT COUNT(*) FROM return_quiz_attempts WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    rbi_mcqs = 0
    rbi_db = _DATA / "rbi.db"
    if rbi_db.exists():
        try:
            _rbi = sqlite3.connect(str(rbi_db), check_same_thread=False)
            _rbi.row_factory = sqlite3.Row
            rbi_mcqs = _rbi.execute(
                "SELECT COUNT(*) FROM rbi_attempts WHERE user_id=?", (user_id,)
            ).fetchone()[0]
            _rbi.close()
        except Exception:
            pass

    mcqs_attempted = ies_mcqs + rbi_mcqs + upsc_mcqs

    exam_focus_list = []
    if user and user["exam_focus"]:
        try:
            exam_focus_list = json.loads(user["exam_focus"])
        except Exception:
            pass

    return render_template(
        "profile.html",
        active_page="profile",
        user=user,
        answers_graded=answers_graded,
        mcqs_attempted=mcqs_attempted,
        exam_focus_list=exam_focus_list,
        exam_labels=EXAM_LABELS,
    )


@profile_bp.route("/upgrade")
@login_required
def upgrade():
    return render_template("upgrade.html", active_page="upgrade")


@profile_bp.route("/upgrade/interest", methods=["POST"])
@login_required
def upgrade_interest():
    nc = get_nyaya_conn()
    email = request.form.get("email", "").strip()[:200]
    nc.execute(
        "INSERT INTO user_events (user_id, event_type, event_data, created_at) "
        "VALUES (?, 'upgrade_interest', ?, datetime('now'))",
        (g.user_id, json.dumps({"email": email})),
    )
    nc.commit()
    return render_template("upgrade.html", active_page="upgrade", submitted=True)
