"""RBI English Descriptive timed-writing simulator — /rbi/english-sim (PLAN-021 Area 4).

Rahul's actual 2026 RBI Grade B failure: passed the Economics MCQ portion but did not
complete the English Descriptive paper (Essay + Precis + Reading Comprehension, 90
minutes total) in time. This is a pacing/completion problem, not a content-quality
problem -- so the simulator's job is to make time cost visible (live words/min, a
post-submission pacing report), not to grade quality. An optional, separate essay
quality score is available but never required.

Per-section behavior: WARN on overrun, never hard-cut (Rahul's explicit choice,
2026-08-30) -- the training goal is awareness, not exact exam-day replication.
"""
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, redirect, render_template, request, url_for
from auth import login_required
from db import get_user_id, log_event, track_page_time
from rbi_english_sim_content import pick_content

rbi_english_sim_bp = Blueprint("rbi_english_sim", __name__)

DEFAULT_SECTION_BUDGET_S = 30 * 60  # even 30/30/30 split of the 90-minute paper;
# the real per-section mark split is officially unconfirmed (PLAN-021 Area 1) --
# don't hardcode a disputed weighting as if it were fact.


def _get_client():
    try:
        import anthropic, os
        key = os.environ.get("ANTHROPIC_API_KEY")
        return anthropic.Anthropic(api_key=key) if key else None
    except Exception:
        return None


_RBI_ESSAY_SCORE_TOOL = {
    "name": "score_rbi_essay",
    "description": "Score an RBI Grade B English Descriptive essay answer.",
    "input_schema": {
        "type": "object",
        "properties": {
            "content_score": {"type": "number", "description": "0-10: relevance, argument quality, structure"},
            "language_score": {"type": "number", "description": "0-10: grammar, vocabulary, clarity"},
            "feedback": {"type": "string"},
        },
        "required": ["content_score", "language_score", "feedback"],
    },
}


def _score_rbi_essay(prompt_text: str, essay_text: str):
    """Optional, separate quality pass -- never required to use the timer/pacing feature.
    Deliberately NOT reusing essay_bp.py's _score_essay (that function's prompt is hardcoded
    to UPSC's 125-mark/1200-word essay; RBI's is much shorter and scored differently -- a
    self-contained scorer here avoids touching the live UPSC essay-scoring code path at all)."""
    client = _get_client()
    if not client or not essay_text or not essay_text.strip():
        return None
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=(
                "You are an RBI Grade B English Descriptive paper examiner. Score the essay "
                "for content quality and language separately, 0-10 each. Be fair and specific."
            ),
            messages=[{"role": "user", "content": f"Essay prompt:\n{prompt_text}\n\nStudent essay:\n{essay_text}"}],
            tools=[_RBI_ESSAY_SCORE_TOOL],
            tool_choice={"type": "tool", "name": "score_rbi_essay"},
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "score_rbi_essay":
                inp = block.input
                return {
                    "content_score": min(10, max(0, round(float(inp.get("content_score", 0)), 1))),
                    "language_score": min(10, max(0, round(float(inp.get("language_score", 0)), 1))),
                    "feedback": inp.get("feedback", ""),
                    "model": "claude-haiku-4-5-20251001",
                }
    except Exception:
        pass
    return None


def _build_pacing_report(data: dict) -> dict:
    """The actual missing signal from 2026: did each section get finished, and when."""
    sections = []
    text_keys = {"essay": "essay_text", "precis": "precis_text", "rc": "rc_answer_text"}
    for key, label in (("essay", "Essay"), ("precis", "Precis"), ("rc", "Reading Comprehension")):
        time_s = data.get(f"{key}_time_s") or 0
        budget_s = data.get(f"{key}_budget_s") or DEFAULT_SECTION_BUDGET_S
        text = data.get(text_keys[key]) or ""
        over_by = max(0, time_s - budget_s)
        sections.append({
            "label": label,
            "time_s": time_s,
            "budget_s": budget_s,
            "over_budget": over_by > 0,
            "over_by_s": over_by,
            "word_count": len(text.split()) if text else 0,
            "completed": bool(text.strip()) if text else False,
        })
    total_time_s = data.get("total_time_s") or sum(s["time_s"] for s in sections)
    all_completed = all(s["completed"] for s in sections)
    return {
        "sections": sections,
        "total_time_s": total_time_s,
        "all_sections_completed": all_completed,
        "sections_over_budget": [s["label"] for s in sections if s["over_budget"]],
    }


@rbi_english_sim_bp.route("/rbi/english-sim")
@login_required
def landing():
    conn = g.rbi_conn
    track_page_time(conn, "RBI English Sim Landing")
    uid = get_user_id()
    recent = conn.execute(
        "SELECT session_id, submitted_at, total_time_s FROM rbi_english_sim_attempts "
        "WHERE user_id=? AND submitted_at IS NOT NULL ORDER BY submitted_at DESC LIMIT 5",
        (uid,)
    ).fetchall()
    return render_template(
        "rbi_english_sim_landing.html",
        active_page="rbi_english_sim",
        recent=[dict(r) for r in recent],
        budget_min=DEFAULT_SECTION_BUDGET_S // 60,
    )


@rbi_english_sim_bp.route("/rbi/english-sim/start", methods=["POST"])
@login_required
def start():
    conn = g.rbi_conn
    uid = get_user_id()
    session_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO rbi_english_sim_attempts "
        "(user_id, session_id, essay_budget_s, precis_budget_s, rc_budget_s, started_at) "
        "VALUES (?,?,?,?,?,datetime('now'))",
        (uid, session_id, DEFAULT_SECTION_BUDGET_S, DEFAULT_SECTION_BUDGET_S, DEFAULT_SECTION_BUDGET_S)
    )
    conn.commit()
    log_event("rbi_english_sim_started", exam_id="rbi_grade_b")
    return redirect(url_for("rbi_english_sim.attempt_session", session_id=session_id))


@rbi_english_sim_bp.route("/rbi/english-sim/session/<session_id>")
@login_required
def attempt_session(session_id):
    conn = g.rbi_conn
    uid = get_user_id()
    row = conn.execute(
        "SELECT * FROM rbi_english_sim_attempts WHERE session_id=? AND user_id=?",
        (session_id, uid)
    ).fetchone()
    if not row:
        return redirect(url_for("rbi_english_sim.landing"))
    if row["submitted_at"]:
        return redirect(url_for("rbi_english_sim.results", session_id=session_id))

    content = pick_content(session_id)
    track_page_time(conn, "RBI English Sim Attempt")
    return render_template(
        "rbi_english_sim_session.html",
        active_page="rbi_english_sim",
        session_id=session_id,
        content=content,
        essay_budget_s=row["essay_budget_s"],
        precis_budget_s=row["precis_budget_s"],
        rc_budget_s=row["rc_budget_s"],
        total_budget_s=row["essay_budget_s"] + row["precis_budget_s"] + row["rc_budget_s"],
    )


@rbi_english_sim_bp.route("/rbi/english-sim/session/<session_id>/submit", methods=["POST"])
@login_required
def submit(session_id):
    conn = g.rbi_conn
    uid = get_user_id()
    row = conn.execute(
        "SELECT * FROM rbi_english_sim_attempts WHERE session_id=? AND user_id=?",
        (session_id, uid)
    ).fetchone()
    if not row or row["submitted_at"]:
        return redirect(url_for("rbi_english_sim.landing"))

    form = request.form
    data = {
        "essay_text": form.get("essay_text", ""),
        "precis_text": form.get("precis_text", ""),
        "rc_answer_text": form.get("rc_answer_text", ""),
        "essay_time_s": int(form.get("essay_time_s", 0) or 0),
        "precis_time_s": int(form.get("precis_time_s", 0) or 0),
        "rc_time_s": int(form.get("rc_time_s", 0) or 0),
        "essay_budget_s": row["essay_budget_s"],
        "precis_budget_s": row["precis_budget_s"],
        "rc_budget_s": row["rc_budget_s"],
    }
    data["total_time_s"] = data["essay_time_s"] + data["precis_time_s"] + data["rc_time_s"]
    wpm_samples_raw = form.get("wpm_samples_json", "[]")
    try:
        wpm_samples = json.loads(wpm_samples_raw)
    except (ValueError, TypeError):
        wpm_samples = []

    pacing_report = _build_pacing_report(data)

    essay_score = None
    if form.get("request_essay_score") == "1":
        content = pick_content(session_id)
        essay_score = _score_rbi_essay(content["essay"]["prompt"], data["essay_text"])

    conn.execute("""
        UPDATE rbi_english_sim_attempts SET
            essay_text=?, precis_text=?, rc_answer_text=?,
            essay_time_s=?, precis_time_s=?, rc_time_s=?, total_time_s=?,
            wpm_samples_json=?, pacing_report_json=?, essay_score_json=?,
            submitted_at=datetime('now')
        WHERE session_id=? AND user_id=?
    """, (
        data["essay_text"], data["precis_text"], data["rc_answer_text"],
        data["essay_time_s"], data["precis_time_s"], data["rc_time_s"], data["total_time_s"],
        json.dumps(wpm_samples), json.dumps(pacing_report),
        json.dumps(essay_score) if essay_score else None,
        session_id, uid,
    ))
    conn.commit()
    log_event("rbi_english_sim_submitted", exam_id="rbi_grade_b")
    return redirect(url_for("rbi_english_sim.results", session_id=session_id))


@rbi_english_sim_bp.route("/rbi/english-sim/session/<session_id>/results")
@login_required
def results(session_id):
    conn = g.rbi_conn
    uid = get_user_id()
    row = conn.execute(
        "SELECT * FROM rbi_english_sim_attempts WHERE session_id=? AND user_id=?",
        (session_id, uid)
    ).fetchone()
    if not row or not row["submitted_at"]:
        return redirect(url_for("rbi_english_sim.landing"))

    pacing_report = json.loads(row["pacing_report_json"]) if row["pacing_report_json"] else {}
    essay_score = json.loads(row["essay_score_json"]) if row["essay_score_json"] else None
    wpm_samples = json.loads(row["wpm_samples_json"]) if row["wpm_samples_json"] else []

    return render_template(
        "rbi_english_sim_results.html",
        active_page="rbi_english_sim",
        pacing_report=pacing_report,
        essay_score=essay_score,
        wpm_samples=wpm_samples,
        row=dict(row),
    )
