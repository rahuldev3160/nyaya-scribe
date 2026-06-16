import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, redirect, render_template, request, url_for
from auth import login_required
from db import get_conn, track_page_time

upsc_dashboard_bp = Blueprint("upsc_dashboard", __name__)

UPSC_EXAM_ID = "upsc_eco_opt"

PAPER_LABELS = {
    "upsc_p1": "Paper I · Theory",
    "upsc_p2": "Paper II · Indian Economy",
}

_STATE_META = {
    "UNVISITED": "not yet started",
    "IN_STUDY": "in progress",
    "PARTIAL": "partially done",
    "VERIFIED": "fully verified ✓",
    "DECAYING": "needs a quick refresh",
    "FLAGGED": "needs more practice",
}

_STATE_DISPLAY = {
    "UNVISITED": "Not Started",
    "IN_STUDY": "In Progress",
    "FLAGGED": "Needs Work",
    "PARTIAL": "Partially Done",
    "VERIFIED": "Verified",
    "DECAYING": "Needs Refresh",
}

_FOCUS_NEXT = {
    "UNVISITED": ("Begin Study", "IN_STUDY"),
    "FLAGGED": ("Resume", "IN_STUDY"),
    "DECAYING": ("Resume", "IN_STUDY"),
    "IN_STUDY": ("Mark Partial", "PARTIAL"),
    "PARTIAL": ("Mark Verified", "VERIFIED"),
    "VERIFIED": ("Verified ✓", "VERIFIED"),
}

STATE_ORDER = ["UNVISITED", "IN_STUDY", "FLAGGED", "PARTIAL", "VERIFIED", "DECAYING"]

STATE_COLORS = {
    "UNVISITED": "#9AA0A6",
    "IN_STUDY": "#FDD663",
    "FLAGGED": "#8AB4F8",
    "PARTIAL": "#81C995",
    "VERIFIED": "#81C995",
    "DECAYING": "#F28B82",
}

STATE_EMOJI = {
    "UNVISITED": "○",
    "IN_STUDY": "◑",
    "FLAGGED": "⚑",
    "PARTIAL": "◕",
    "VERIFIED": "✓",
    "DECAYING": "↓",
}


def _init_user(conn, uid):
    if conn.execute(
        "SELECT 1 FROM gap_states WHERE user_id=? AND exam_id=? LIMIT 1",
        (uid, UPSC_EXAM_ID),
    ).fetchone():
        return
    topics = conn.execute(
        "SELECT topic_id, paper_id FROM topics WHERE exam_id=? AND topic_level='topic'",
        (UPSC_EXAM_ID,),
    ).fetchall()
    for t in topics:
        conn.execute(
            "INSERT OR IGNORE INTO gap_states (user_id, topic_id, exam_id, paper_id, state, attempt_count) VALUES (?,?,?,?,?,0)",
            (uid, t["topic_id"], UPSC_EXAM_ID, t["paper_id"], "UNVISITED"),
        )
    conn.commit()


def _get_topics(conn, uid, paper_id=None):
    paper_clause = "AND t.paper_id=?" if paper_id else ""
    rows = conn.execute(
        f"""SELECT t.topic_id, t.topic_name, t.paper_id,
               gs.state,
               COALESCE(bs.base_priority_score, 0.5) AS base_priority_score,
               COALESCE(bs.pyq_count, 0) AS pyq_count,
               COUNT(DISTINCT q.question_id) AS total_q,
               COUNT(DISTINCT ma.answer_id) AS answers_ready,
               COALESCE(um.mastery_level, 0.0) AS mastery_level
        FROM topics t
        LEFT JOIN gap_states gs ON gs.user_id=? AND gs.topic_id=t.topic_id AND gs.exam_id=?
        LEFT JOIN topic_base_scores bs ON bs.topic_id=t.topic_id AND bs.exam_id=t.exam_id
        LEFT JOIN pyq_questions q ON q.topic_id=t.topic_id AND q.exam_id=t.exam_id
        LEFT JOIN model_answers ma ON ma.question_id=q.question_id AND ma.exam_id=q.exam_id
        LEFT JOIN user_mastery um ON um.user_id=? AND um.topic_id=t.topic_id AND um.exam_id=?
        WHERE t.exam_id=? AND t.topic_level='topic' {paper_clause}
        GROUP BY t.topic_id
        ORDER BY base_priority_score DESC""",
        [uid, UPSC_EXAM_ID, uid, UPSC_EXAM_ID, UPSC_EXAM_ID] + ([paper_id] if paper_id else []),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_recommended_question(conn, user_id):
    stats = conn.execute("""
        SELECT q.topic_id, COUNT(*) as cnt,
               AVG(COALESCE(da.weighted_score, CASE da.self_rating WHEN 'got_it' THEN 8.0 WHEN 'partial' THEN 5.0 WHEN 'missed' THEN 2.0 ELSE NULL END)) as avg_score,
               MAX(da.created_at) as last_at
        FROM descriptive_attempts da
        JOIN pyq_questions q ON da.question_id=q.question_id AND da.exam_id=q.exam_id
        WHERE da.exam_id='upsc_eco_opt' AND da.user_id=?
        GROUP BY q.topic_id
    """, (user_id,)).fetchall()
    stats_by_topic = {r["topic_id"]: dict(r) for r in stats}

    topics = conn.execute("""
        SELECT topic_id, paper_id, base_priority_score
        FROM topic_base_scores WHERE exam_id='upsc_eco_opt'
        ORDER BY base_priority_score DESC
    """).fetchall()

    for t in topics:
        s = stats_by_topic.get(t["topic_id"])
        if s is None or s["avg_score"] is None or s["avg_score"] < 6.0:
            q = conn.execute("""
                SELECT question_id, question_text, marks, year
                FROM pyq_questions WHERE topic_id=? AND exam_id='upsc_eco_opt'
                ORDER BY year DESC LIMIT 1
            """, (t["topic_id"],)).fetchone()
            if q:
                return {
                    "topic_id": t["topic_id"],
                    "topic_label": t["topic_id"].replace("_", " ").title(),
                    "paper_id": t["paper_id"],
                    **dict(q),
                    "attempt_count": s["cnt"] if s else 0,
                    "base_priority_score": t["base_priority_score"],
                }
    return None


def _compute_readiness_score(conn, user_id):
    total_row = conn.execute(
        "SELECT COUNT(*) FROM gap_states WHERE user_id=? AND exam_id='upsc_eco_opt'",
        (user_id,),
    ).fetchone()
    total_upsc_topics = total_row[0] if total_row else 0
    if total_upsc_topics == 0:
        return 0

    breadth_row = conn.execute("""
        SELECT COUNT(DISTINCT q.topic_id)
        FROM descriptive_attempts da
        JOIN pyq_questions q ON da.question_id=q.question_id AND da.exam_id=q.exam_id
        WHERE da.exam_id='upsc_eco_opt' AND da.user_id=?
    """, (user_id,)).fetchone()
    topics_with_attempts = breadth_row[0] if breadth_row else 0

    quality_row = conn.execute("""
        SELECT AVG(COALESCE(da.weighted_score, CASE da.self_rating WHEN 'got_it' THEN 8.0 WHEN 'partial' THEN 5.0 WHEN 'missed' THEN 2.0 ELSE NULL END))
        FROM descriptive_attempts da
        WHERE da.exam_id='upsc_eco_opt' AND da.user_id=?
    """, (user_id,)).fetchone()
    avg_q = quality_row[0] if (quality_row and quality_row[0] is not None) else None

    breadth = (topics_with_attempts / total_upsc_topics) * 50
    quality = (avg_q / 10) * 50 if avg_q is not None else 0
    return max(0, min(100, int(breadth + quality)))


def _daily_attempts(conn, user_id):
    row = conn.execute("""
        SELECT COUNT(*) FROM descriptive_attempts
        WHERE exam_id='upsc_eco_opt' AND user_id=? AND date(created_at)=date('now')
    """, (user_id,)).fetchone()
    return row[0] if row else 0


def _set_state(conn, uid, topic_id, new_state):
    conn.execute(
        "UPDATE gap_states SET state=?, last_active_at=datetime('now') WHERE user_id=? AND topic_id=? AND exam_id=?",
        (new_state, uid, topic_id, UPSC_EXAM_ID),
    )
    conn.commit()


@upsc_dashboard_bp.route("/upsc")
@login_required
def upsc_dashboard_page():
    ies_conn = get_conn()
    track_page_time(ies_conn, "UPSC Dashboard")
    user_id = g.user_id

    if not g.upsc_conn:
        return render_template("upsc_dashboard.html", active_page="upsc_dashboard", db_missing=True)

    conn = g.upsc_conn
    _init_user(conn, user_id)

    try:
        row = g.upsc_conn.execute(
            "SELECT exam_date FROM exam_configurations WHERE exam_id='upsc_eco_opt'"
        ).fetchone()
        upsc_date_str = row[0] if row else "2026-08-22"
    except Exception:
        upsc_date_str = "2026-08-22"
    d = (datetime.strptime(upsc_date_str, "%Y-%m-%d").date() - datetime.today().date()).days

    all_topics = _get_topics(conn, user_id)

    attempt_stats_rows = conn.execute("""
        SELECT q.topic_id,
               COUNT(*) as cnt,
               AVG(COALESCE(da.weighted_score, CASE da.self_rating WHEN 'got_it' THEN 8.0 WHEN 'partial' THEN 5.0 WHEN 'missed' THEN 2.0 ELSE NULL END)) as avg_score
        FROM descriptive_attempts da
        JOIN pyq_questions q ON da.question_id=q.question_id AND da.exam_id=q.exam_id
        WHERE da.exam_id='upsc_eco_opt' AND da.user_id=?
        GROUP BY q.topic_id
    """, (user_id,)).fetchall()
    attempt_stats = {r["topic_id"]: dict(r) for r in attempt_stats_rows}

    rec_question = _get_recommended_question(conn, user_id)
    readiness_score = _compute_readiness_score(conn, user_id)
    daily_done = _daily_attempts(conn, user_id)

    topics_by_paper = {}
    for t in all_topics:
        topics_by_paper.setdefault(t["paper_id"], []).append(t)
    state_counts = {}
    for t in all_topics:
        s = t["state"] or "UNVISITED"
        state_counts[s] = state_counts.get(s, 0) + 1

    verified = state_counts.get("VERIFIED", 0)
    total_t = len(all_topics)
    in_progress = state_counts.get("IN_STUDY", 0) + state_counts.get("PARTIAL", 0)
    total_q = sum(t["total_q"] for t in all_topics)
    total_ans = sum(t["answers_ready"] for t in all_topics)
    ans_pct = int(100 * total_ans / total_q) if total_q else 0
    readiness_pct = int(100 * verified / total_t) if total_t else 0

    day_color = "#F28B82" if d <= 30 else "#FDD663" if d <= 60 else "#8AB4F8"
    ip_color = "#FDD663" if in_progress > 0 else "#9AA0A6"
    r_color = "#F28B82" if readiness_pct < 20 else "#FDD663" if readiness_pct < 50 else "#81C995"

    papers_data = []
    for paper_id, paper_label in PAPER_LABELS.items():
        topics = topics_by_paper.get(paper_id, [])
        p_verified = sum(1 for t in topics if (t["state"] or "UNVISITED") == "VERIFIED")
        p_total = len(topics)
        p_pct = int(100 * p_verified / p_total) if p_total else 0
        p_color = "#F28B82" if p_pct < 20 else "#FDD663" if p_pct < 50 else "#81C995"
        topic_rows = []
        for t in topics:
            state = t["state"] or "UNVISITED"
            btn_label, next_state = _FOCUS_NEXT.get(state, ("Begin Study", "IN_STUDY"))
            ts = attempt_stats.get(t["topic_id"])
            t_count = ts["cnt"] if ts else 0
            t_avg = ts["avg_score"] if (ts and ts["avg_score"] is not None) else None
            bps = t.get("base_priority_score") or 0
            if t_avg is not None and t_avg >= 7.0:
                t_color = "green"
            elif t_avg is not None and t_avg < 4.0:
                t_color = "red"
            elif t_count == 0 and bps >= 0.7:
                t_color = "red"
            else:
                t_color = "grey"
            topic_rows.append({
                **t,
                "_state": state,
                "_btn_label": btn_label,
                "_next_state": next_state,
                "_mastery_pct": int((t["mastery_level"] or 0) * 100),
                "_name": t["topic_name"] or t["topic_id"].replace("_", " ").title(),
                "_ans_bar_pct": int(100 * (t["answers_ready"] or 0) / (t["total_q"] or 1)),
                "_state_meta": _STATE_META.get(state, ""),
                "_attempt_count": t_count,
                "_avg_score": t_avg,
                "_color_indicator": t_color,
            })
        papers_data.append({
            "id": paper_id,
            "label": paper_label,
            "pct": p_pct,
            "color": p_color,
            "verified": p_verified,
            "total": p_total,
            "topics": topic_rows,
        })

    state_overview = [
        {
            "state": s,
            "count": state_counts.get(s, 0),
            "color": STATE_COLORS[s],
            "emoji": STATE_EMOJI[s],
            "label": _STATE_DISPLAY.get(s, s),
        }
        for s in STATE_ORDER
    ]

    return render_template(
        "upsc_dashboard.html",
        active_page="upsc_dashboard",
        db_missing=False,
        days_left=d,
        day_color=day_color,
        verified=verified,
        total_t=total_t,
        in_progress=in_progress,
        ip_color=ip_color,
        total_ans=total_ans,
        total_q=total_q,
        ans_pct=ans_pct,
        readiness_pct=readiness_pct,
        r_color=r_color,
        papers_data=papers_data,
        state_overview=state_overview,
        rec_question=rec_question,
        readiness_score=readiness_score,
        daily_done=daily_done,
    )


@upsc_dashboard_bp.route("/upsc/topics/<topic_id>/state", methods=["POST"])
@login_required
def upsc_topic_state(topic_id):
    new_state = request.form.get("new_state", "")
    VALID = {"UNVISITED", "IN_STUDY", "PARTIAL", "VERIFIED", "FLAGGED", "DECAYING"}
    if new_state in VALID and g.upsc_conn:
        _set_state(g.upsc_conn, g.user_id, topic_id, new_state)
    if new_state == "IN_STUDY":
        paper_row = g.upsc_conn.execute(
            "SELECT paper_id FROM topics WHERE topic_id=? AND exam_id=? AND topic_level='topic'",
            (topic_id, UPSC_EXAM_ID),
        ).fetchone() if g.upsc_conn else None
        paper_param = f"&paper={paper_row['paper_id']}" if paper_row else ""
        return redirect(url_for("upsc.mains") + f"?topic={topic_id}{paper_param}")
    return redirect(url_for("upsc_dashboard.upsc_dashboard_page") + "#upsc-papers")
