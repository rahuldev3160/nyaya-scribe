"""IES 2026 Dashboard blueprint — /dashboard and /ies/topics/<id>/state."""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, redirect, render_template, request, url_for
from auth import login_required
from db import (
    EXAM_ID, get_conn, get_nyaya_conn, get_user_id, init_user,
    get_topics, get_true_readiness, get_paper_coverage,
    set_topic_state, is_crunch_mode, get_study_path,
    track_page_time, _open_conn,
)

dashboard_bp = Blueprint("dashboard", __name__)

PAPERS = [
    ("ge_01", "GE-01 · Micro & Macro"),
    ("ge_02", "GE-02 · Stats & Math"),
    ("ge_03", "GE-03 · Indian Economy"),
    ("ge_04", "GE-04 · Eco Policy"),
]

_STATE_DISPLAY = {
    "UNVISITED": "Not Started", "IN_STUDY": "In Progress", "FLAGGED": "Needs Work",
    "PARTIAL": "Partially Done", "VERIFIED": "Verified", "DECAYING": "Needs Refresh",
}

_STATE_META = {
    "UNVISITED": "not yet started",
    "IN_STUDY":  "in progress",
    "PARTIAL":   "partially done — test yourself to verify",
    "VERIFIED":  "fully verified ✓",
    "DECAYING":  "studied before — needs a quick refresh",
    "FLAGGED":   "scored below 50% in quiz — needs more practice",
}

_STATE_COLORS = {
    "UNVISITED": "#9AA0A6", "IN_STUDY": "#FDD663", "FLAGGED": "#8AB4F8",
    "PARTIAL": "#81C995", "VERIFIED": "#81C995", "DECAYING": "#F28B82",
}

_STATE_EMOJI = {
    "UNVISITED": "○", "IN_STUDY": "◑", "FLAGGED": "⚑",
    "PARTIAL": "◕", "VERIFIED": "✓", "DECAYING": "↓",
}

_NEXT_STATE = {
    "UNVISITED": ("Begin Study",  "IN_STUDY"),
    "FLAGGED":   ("Resume",       "IN_STUDY"),
    "DECAYING":  ("Resume",       "IN_STUDY"),
    "IN_STUDY":  ("Mark Partial", "PARTIAL"),
    "PARTIAL":   ("Mark Verified","VERIFIED"),
    "VERIFIED":  ("Verified ✓",   "VERIFIED"),
}

_FOCUS_LABEL = {
    "UNVISITED": "→ Begin Topic",
    "FLAGGED":   "Resume",
    "DECAYING":  "Resume",
    "IN_STUDY":  "Mark Partial",
    "PARTIAL":   "Mark Verified",
}


def _days_left() -> int:
    try:
        conn = _open_conn()
        row = conn.execute(
            "SELECT exam_date FROM exam_configurations WHERE exam_id='ies_2026'"
        ).fetchone()
        conn.close()
        exam_str = row[0] if row else "2026-06-19"
    except Exception:
        exam_str = "2026-06-19"
    return (datetime.strptime(exam_str, "%Y-%m-%d").date() - datetime.today().date()).days


def _priority_label(score: float) -> str:
    if score >= 0.85: return "Top priority"
    if score >= 0.60: return "High priority"
    if score >= 0.40: return "Medium priority"
    return "Lower priority"


def _get_topic_attempt_stats(conn, user_id: str) -> dict:
    """Returns {topic_id: {cnt, avg_score, last_at}} for ies_2026."""
    rows = conn.execute(
        "SELECT q.topic_id, COUNT(*) as cnt, "
        "AVG(COALESCE(da.weighted_score, CASE da.self_rating WHEN 'got_it' THEN 8.0 WHEN 'partial' THEN 5.0 WHEN 'missed' THEN 2.0 ELSE NULL END)) as avg_score, "
        "MAX(da.created_at) as last_at "
        "FROM descriptive_attempts da "
        "JOIN pyq_questions q ON da.question_id=q.question_id AND da.exam_id=q.exam_id "
        "WHERE da.exam_id='ies_2026' AND da.user_id=? "
        "GROUP BY q.topic_id",
        (user_id,)
    ).fetchall()
    return {r["topic_id"]: {"cnt": r["cnt"], "avg_score": r["avg_score"], "last_at": r["last_at"]} for r in rows}


def _get_recommended_question(conn, user_id: str, topic_stats: dict) -> dict | None:
    topics = conn.execute(
        "SELECT topic_id, paper_id, base_priority_score "
        "FROM topic_base_scores WHERE exam_id='ies_2026' "
        "ORDER BY base_priority_score DESC"
    ).fetchall()

    chosen_topic = None
    for row in topics:
        tid = row["topic_id"]
        st = topic_stats.get(tid)
        if st is None or (st["avg_score"] is not None and st["avg_score"] < 6.0):
            chosen_topic = row
            break

    if not chosen_topic:
        return None

    q = conn.execute(
        "SELECT question_id, question_text, marks, year FROM pyq_questions "
        "WHERE topic_id=? AND exam_id='ies_2026' ORDER BY year DESC LIMIT 1",
        (chosen_topic["topic_id"],)
    ).fetchone()
    if not q:
        return None

    st = topic_stats.get(chosen_topic["topic_id"])
    return {
        "topic_id": chosen_topic["topic_id"],
        "topic_label": chosen_topic["topic_id"].replace("_", " ").title(),
        "paper_id": chosen_topic["paper_id"],
        "question_id": q["question_id"],
        "question_text": q["question_text"][:200] if q["question_text"] else "",
        "marks": q["marks"],
        "year": q["year"],
        "base_priority_score": chosen_topic["base_priority_score"],
        "attempt_count": st["cnt"] if st else 0,
    }


def _compute_readiness_score(conn, user_id: str, topic_stats: dict) -> int:
    total_topics = conn.execute(
        "SELECT COUNT(DISTINCT topic_id) FROM topic_base_scores WHERE exam_id='ies_2026'"
    ).fetchone()[0]
    if not total_topics:
        return 0

    topics_with_attempts = len(topic_stats)
    breadth = (topics_with_attempts / total_topics) * 50

    all_scores = conn.execute(
        "SELECT COALESCE(weighted_score, CASE self_rating WHEN 'got_it' THEN 8.0 WHEN 'partial' THEN 5.0 WHEN 'missed' THEN 2.0 ELSE NULL END) as score "
        "FROM descriptive_attempts WHERE exam_id='ies_2026' AND user_id=? "
        "AND (weighted_score IS NOT NULL OR self_rating IS NOT NULL)",
        (user_id,)
    ).fetchall()
    if all_scores:
        avg = sum(r["score"] for r in all_scores) / len(all_scores)
        quality = (avg / 10.0) * 50
    else:
        quality = 0

    return max(0, min(100, int(breadth + quality)))


def _daily_attempts(conn, user_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM descriptive_attempts "
        "WHERE exam_id='ies_2026' AND user_id=? AND date(created_at)=date('now')",
        (user_id,)
    ).fetchone()[0]


def _topic_color_indicator(topic_id: str, base_priority_score: float, topic_stats: dict) -> tuple:
    """Returns (_attempt_count, _avg_score, _color_indicator)."""
    st = topic_stats.get(topic_id)
    if st is None:
        color = "red" if (base_priority_score or 0) >= 0.7 else "grey"
        return 0, None, color
    avg = st["avg_score"]
    if avg is not None and avg < 4.0:
        return st["cnt"], avg, "red"
    if avg is not None and avg >= 7.0:
        return st["cnt"], avg, "green"
    return st["cnt"], avg, "grey"


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    conn = get_conn()
    nyaya_conn = get_nyaya_conn()
    user_id = g.user_id
    init_user(conn, user_id)
    track_page_time(conn, "Dashboard", exam_id=EXAM_ID)

    onb = nyaya_conn.execute(
        "SELECT onboarding_completed, exam_focus FROM users WHERE user_id=?", (user_id,)
    ).fetchone()
    onboarding_incomplete = not onb or not onb["onboarding_completed"] or not onb["exam_focus"]

    # ── New hero data ──────────────────────────────────────────────────────────
    topic_stats = _get_topic_attempt_stats(conn, user_id)
    rec_question = _get_recommended_question(conn, user_id, topic_stats)
    readiness_score = _compute_readiness_score(conn, user_id, topic_stats)
    daily_done = _daily_attempts(conn, user_id)

    # ── Metrics ────────────────────────────────────────────────────────────────
    d = _days_left()
    total_a = conn.execute(
        "SELECT COUNT(*) FROM model_answers WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]
    total_q = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]
    verified_count = conn.execute(
        "SELECT COUNT(*) FROM gap_states WHERE exam_id=? AND user_id=? AND state='VERIFIED'",
        (EXAM_ID, user_id)
    ).fetchone()[0]
    total_t = conn.execute(
        "SELECT COUNT(*) FROM gap_states WHERE exam_id=? AND user_id=?",
        (EXAM_ID, user_id)
    ).fetchone()[0]
    readiness = get_true_readiness(conn)
    ans_pct = int(100 * total_a / total_q) if total_q else 0
    day_color = "#F28B82" if d <= 14 else "#8AB4F8"
    r_pct = readiness["formula_pct"]
    r_color = "#F28B82" if r_pct < 20 else "#FDD663" if r_pct < 50 else "#81C995"

    # ── Cross-exam banner ──────────────────────────────────────────────────────
    exam_focus = json.loads(onb["exam_focus"] or '["ies"]') if onb and onb["exam_focus"] else ["ies"]
    other_exams = [e for e in exam_focus if e != "ies"]
    other_exam_links = {
        "rbi":  ("/rbi",  "🏦 RBI DEPR Dashboard (14th June)"),
        "upsc": ("/upsc", "🎓 UPSC Eco Optional Dashboard (~Aug 2026)"),
    }

    # ── Study path banner ──────────────────────────────────────────────────────
    study_path = get_study_path(conn, user_id)

    # ── Today's Focus (top 3 active/priority topics) ───────────────────────────
    all_topics = get_topics(conn)
    focus_topics = [t for t in all_topics if (t["state"] or "UNVISITED") in ("IN_STUDY", "DECAYING", "FLAGGED")]
    if len(focus_topics) < 3:
        unvisited = sorted(
            [t for t in all_topics if (t["state"] or "UNVISITED") == "UNVISITED"],
            key=lambda x: -(x["base_priority_score"] or 0)
        )
        focus_topics = focus_topics + unvisited
    focus_topics = focus_topics[:3]

    for t in focus_topics:
        s = t["state"] or "UNVISITED"
        t["_state"] = s
        t["_state_display"] = _STATE_DISPLAY.get(s, s)
        t["_state_meta"] = _STATE_META.get(s, "")
        t["_state_color"] = _STATE_COLORS.get(s, "#9AA0A6")
        t["_mastery_pct"] = round((t.get("mastery_level") or 0) * 100)
        t["_focus_label"] = _FOCUS_LABEL.get(s, "Begin Study")
        t["_priority_label"] = _priority_label(t["base_priority_score"] or 0)
        t["_display_name"] = t["topic_id"].replace("_", " ").title()
        t["_paper_label"] = t["paper_id"].upper().replace("_", "-")

    # ── Paper tabs data ────────────────────────────────────────────────────────
    paper_cov = {p["paper_id"]: p for p in get_paper_coverage(conn)}
    topics_by_paper = {}
    for t in all_topics:
        topics_by_paper.setdefault(t["paper_id"], []).append(t)
    papers_data = []
    for paper_id, paper_label in PAPERS:
        topics = topics_by_paper.get(paper_id, [])
        pc = paper_cov.get(paper_id, {})
        cov_pct = pc.get("coverage_pct", 0.0) or 0.0
        cov_color = "#F28B82" if cov_pct < 20 else "#FDD663" if cov_pct < 50 else "#81C995"
        for t in topics:
            s = t["state"] or "UNVISITED"
            t["_state"] = s
            t["_state_display"] = _STATE_DISPLAY.get(s, s)
            t["_state_color"] = _STATE_COLORS.get(s, "#9AA0A6")
            t["_display_name"] = t["topic_id"].replace("_", " ").title()
            t["_priority_label"] = _priority_label(t["base_priority_score"] or 0)
            btn_label, next_state = _NEXT_STATE.get(s, ("Begin Study", "IN_STUDY"))
            t["_btn_label"] = btn_label
            t["_next_state"] = next_state
            cnt, avg, color = _topic_color_indicator(t["topic_id"], t["base_priority_score"] or 0, topic_stats)
            t["_attempt_count"] = cnt
            t["_avg_score"] = avg
            t["_color_indicator"] = color
        papers_data.append({
            "paper_id": paper_id,
            "label": paper_label,
            "topics": topics,
            "cov_pct": cov_pct,
            "cov_color": cov_color,
            "cov_done": pc.get("covered_count", 0),
            "cov_total": pc.get("topic_count", len(topics)),
        })

    # ── State summary ──────────────────────────────────────────────────────────
    state_counts = {}
    for t in all_topics:
        s = t["state"] or "UNVISITED"
        state_counts[s] = state_counts.get(s, 0) + 1
    STATE_ORDER = ["UNVISITED", "IN_STUDY", "FLAGGED", "PARTIAL", "VERIFIED", "DECAYING"]
    state_summary = [
        {
            "state": s,
            "display": _STATE_DISPLAY.get(s, s),
            "count": state_counts.get(s, 0),
            "color": _STATE_COLORS[s],
            "emoji": _STATE_EMOJI[s],
        }
        for s in STATE_ORDER
    ]

    # ── IES micro-progress ─────────────────────────────────────────────────────
    micro_descriptive = conn.execute(
        "SELECT COUNT(*) FROM descriptive_attempts WHERE exam_id=? AND user_id=?",
        (EXAM_ID, user_id)
    ).fetchone()[0]
    micro_mcq = conn.execute(
        "SELECT COUNT(*) FROM return_quiz_attempts WHERE exam_id=? AND user_id=?",
        (EXAM_ID, user_id)
    ).fetchone()[0]
    try:
        micro_recent_rows = conn.execute(
            "SELECT da.created_at, q.topic_id, da.self_rating, "
            "(COALESCE(da.word_count_intro,0)+COALESCE(da.word_count_body,0)"
            "+COALESCE(da.word_count_conclusion,0)) AS words "
            "FROM descriptive_attempts da "
            "LEFT JOIN pyq_questions q ON da.question_id=q.question_id AND da.exam_id=q.exam_id "
            "WHERE da.exam_id=? AND da.user_id=? "
            "ORDER BY da.created_at DESC LIMIT 5",
            (EXAM_ID, user_id)
        ).fetchall()
    except Exception:
        micro_recent_rows = []
    micro_recent = [dict(r) for r in micro_recent_rows]

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        d=d,
        day_color=day_color,
        total_a=total_a,
        total_q=total_q,
        ans_pct=ans_pct,
        verified_count=verified_count,
        total_t=total_t,
        readiness=readiness,
        readiness_score=readiness_score,
        r_color=r_color,
        crunch_mode=is_crunch_mode(),
        other_exams=other_exams,
        other_exam_links=other_exam_links,
        study_path=study_path,
        focus_topics=focus_topics,
        papers_data=papers_data,
        state_summary=state_summary,
        papers=PAPERS,
        micro_descriptive=micro_descriptive,
        micro_mcq=micro_mcq,
        micro_recent=micro_recent,
        onboarding_incomplete=onboarding_incomplete,
        rec_question=rec_question,
        daily_done=daily_done,
    )


@dashboard_bp.route("/ies/topics/<topic_id>/state", methods=["POST"])
@login_required
def set_state(topic_id):
    conn = get_conn()
    new_state = request.form.get("state")
    trigger = request.form.get("trigger", "ui_dashboard")
    valid_states = {"UNVISITED", "IN_STUDY", "PARTIAL", "VERIFIED", "DECAYING", "FLAGGED"}
    if new_state in valid_states:
        set_topic_state(conn, topic_id, new_state, trigger, user_id=g.user_id)
    if new_state == "IN_STUDY" and trigger in ("ui_advance", "ui_focus_start"):
        paper_row = conn.execute(
            "SELECT paper_id FROM topics WHERE topic_id=? AND exam_id=? AND topic_level='topic'",
            (topic_id, EXAM_ID),
        ).fetchone()
        paper_param = f"&paper={paper_row['paper_id']}" if paper_row else ""
        return redirect(url_for("ies_answers.answers") + f"?topic={topic_id}{paper_param}")
    return redirect(request.referrer or url_for("dashboard.dashboard"))
