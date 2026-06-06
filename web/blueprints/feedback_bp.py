import uuid
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from auth import login_required
from db import get_nyaya_conn

feedback_bp = Blueprint("feedback", __name__)

CATEGORIES = [
    ("bug",     "Bug",             "#F28B82"),
    ("feature", "Feature Request", "#8AB4F8"),
    ("issue",   "Issue",           "#FDD663"),
    ("other",   "Other",           "#9AA0A6"),
]

STATUS_COLORS = {
    "open":         "#F28B82",
    "acknowledged": "#FDD663",
    "resolved":     "#81C995",
}


@feedback_bp.route("/feedback", methods=["GET"])
@login_required
def feedback_list():
    conn = get_nyaya_conn()
    feedbacks = conn.execute(
        "SELECT f.*, u.display_name, u.email "
        "FROM user_feedback f "
        "LEFT JOIN users u ON f.user_id = u.user_id "
        "ORDER BY f.created_at DESC"
    ).fetchall()

    items = [dict(f) for f in feedbacks]
    return render_template(
        "feedback.html",
        active_page="feedback",
        items=items,
        categories=CATEGORIES,
        status_colors=STATUS_COLORS,
        my_user_id=g.user_id,
    )


@feedback_bp.route("/feedback/submit", methods=["POST"])
@login_required
def feedback_submit():
    conn = get_nyaya_conn()
    category = request.form.get("category", "bug")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title:
        flash("Title is required.", "error")
        return redirect(url_for("feedback.feedback_list"))

    valid_cats = {c[0] for c in CATEGORIES}
    if category not in valid_cats:
        category = "other"

    conn.execute(
        "INSERT INTO user_feedback (feedback_id, user_id, category, title, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (uuid.uuid4().hex[:12], g.user_id, category, title, description),
    )
    conn.commit()
    flash("Feedback submitted.", "success")
    return redirect(url_for("feedback.feedback_list"))
