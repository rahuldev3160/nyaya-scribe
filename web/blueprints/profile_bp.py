import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from auth import login_required
from db import get_conn, log_event, track_page_time

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
    user_id = g.user_id
    track_page_time(conn, "Profile")

    try:
        conn.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
        conn.commit()
    except Exception:
        pass

    if request.method == "POST":
        phone = request.form.get("phone_number", "").strip()
        old_row = conn.execute(
            "SELECT phone_number FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        old_phone = old_row["phone_number"] if old_row else None
        conn.execute(
            "UPDATE users SET phone_number=? WHERE user_id=?",
            (phone, user_id),
        )
        conn.commit()
        try:
            if phone != (old_phone or ""):
                log_event(conn, "config_changed", payload={"field": "phone_number", "old_value": old_phone, "new_value": phone})
        except Exception:
            pass
        flash("Contact details saved.", "success")
        return redirect(url_for("profile_bp.profile_page"))

    user = conn.execute(
        "SELECT display_name, email, avatar_url, created_at, subscription_tier, phone_number, "
        "exam_focus, exam_date, onboarding_completed FROM users WHERE user_id=?",
        (user_id,),
    ).fetchone()

    answers_graded = conn.execute(
        "SELECT COUNT(*) FROM descriptive_attempts WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    mcqs_attempted = conn.execute(
        "SELECT COUNT(*) FROM return_quiz_attempts WHERE user_id=?", (user_id,)
    ).fetchone()[0]

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
