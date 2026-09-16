"""UPSC Economics Optional blueprint — /upsc/eco

Per-topic question browsing + attempt-submission for Eco-Optional. The topic dashboard
(upsc_dashboard_bp.py) only ever showed topic-level progress; there was no route to view a
topic's actual questions or submit an attempt against upsc_eco_opt.db's `descriptive_attempts`
table (present in schema since PLAN-024 Phase 1's m067 migration, but never written to). This
blueprint fills that gap, reusing the exact same table shape / scoring pattern as
ies_quiz_bp.py and upsc_bp.py's GS Mains detail route.
"""
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
from flask import Blueprint, g, redirect, render_template, request, url_for
from auth import login_required
from db import can_use_feature, increment_feature_usage

upsc_eco_bp = Blueprint("upsc_eco", __name__)

_EXAM_ID = "upsc_eco_opt"

_ANTHROPIC_CLIENT = None

_WC_GUIDE = {
    (0, 7): (25, 55, 20), (7, 12): (35, 90, 25),
    (12, 18): (50, 140, 30), (18, 25): (60, 190, 40), (25, 999): (80, 340, 80),
}


def _wc(marks):
    if not marks:
        return _WC_GUIDE[(7, 12)]
    for (lo, hi), guide in _WC_GUIDE.items():
        if lo <= marks < hi:
            return guide
    return _WC_GUIDE[(7, 12)]


def _jl(s) -> list:
    if not s:
        return []
    try:
        r = json.loads(s)
        return r if isinstance(r, list) else []
    except Exception:
        return []


def _get_client():
    global _ANTHROPIC_CLIENT
    if _ANTHROPIC_CLIENT is None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            return None
        _ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=key)
    return _ANTHROPIC_CLIENT


_SCORE_TOOL = {
    "name": "score_answer",
    "description": "Score a UPSC Economics Optional descriptive answer across 5 dimensions",
    "input_schema": {
        "type": "object",
        "properties": {
            "content_accuracy": {"type": "number", "description": "Correct economic theory/data, 0-10"},
            "structure":        {"type": "number", "description": "Intro/body/conclusion flow, 0-10"},
            "analytical_depth": {"type": "number", "description": "Beyond definitions, applies theory/models, 0-10"},
            "evidence":         {"type": "number", "description": "Data points, diagrams described, examples, 0-10"},
            "language":         {"type": "number", "description": "Clarity, conciseness, economics terminology, 0-10"},
            "feedback":         {"type": "string", "description": "One sentence of specific feedback"},
        },
        "required": ["content_accuracy", "structure", "analytical_depth", "evidence", "language", "feedback"],
    },
}


def _score_eco_answer(question_text: str, marks: int, rubric_pts: list, intro: str, body: str, conclusion: str) -> dict | None:
    """Score an Eco-Optional answer. Same forced-tool-use pattern as ies_quiz_bp._score_answer."""
    client = _get_client()
    if not client:
        return None
    answer = "\n\n".join(filter(None, [intro, body, conclusion]))
    if not answer.strip():
        return None
    rubric_str = "\n".join(f"- {p}" for p in (rubric_pts or [])) or "No rubric provided."
    prompt = (
        f"Question ({marks}m): {question_text}\n\n"
        f"Rubric points:\n{rubric_str}\n\n"
        f"Student answer:\n{answer}"
    )
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system="You are a UPSC Economics Optional evaluator. Score concisely and fairly.",
            messages=[{"role": "user", "content": prompt}],
            tools=[_SCORE_TOOL],
            tool_choice={"type": "tool", "name": "score_answer"},
        )
        for block in resp.content:
            if block.type == "tool_use" and block.name == "score_answer":
                inp = block.input
                dims = {k: round(float(inp.get(k, 0)), 1) for k in
                        ["content_accuracy", "structure", "analytical_depth", "evidence", "language"]}
                weighted = round(sum(dims.values()) / len(dims), 2)
                return {"dimensions": dims, "weighted_score": weighted,
                        "feedback": inp.get("feedback", ""), "model": "claude-haiku-4-5-20251001"}
    except Exception:
        pass
    return None


def _get_topic(conn, topic_id: str) -> dict | None:
    row = conn.execute(
        "SELECT topic_id, topic_name, paper_id FROM topics WHERE topic_id=? AND exam_id=? AND topic_level='topic'",
        (topic_id, _EXAM_ID),
    ).fetchone()
    return dict(row) if row else None


def _get_questions(conn, topic_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT q.question_id, q.question_text, q.marks, q.year, q.paper_id, q.topic_id,
                  ma.answer_id
           FROM pyq_questions q
           LEFT JOIN model_answers ma ON ma.question_id=q.question_id AND ma.exam_id=q.exam_id
           WHERE q.exam_id=? AND q.topic_id=?
           ORDER BY q.marks DESC, q.year DESC""",
        (_EXAM_ID, topic_id),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_question(conn, question_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM pyq_questions WHERE question_id=? AND exam_id=?",
        (question_id, _EXAM_ID),
    ).fetchone()
    return dict(row) if row else None


def _get_answer(conn, question_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM model_answers WHERE question_id=? AND exam_id=?",
        (question_id, _EXAM_ID),
    ).fetchone()
    return dict(row) if row else None


def _get_rubric(conn, question_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM question_rubrics WHERE question_id=? AND exam_id=?",
        (question_id, _EXAM_ID),
    ).fetchone()
    return dict(row) if row else None


@upsc_eco_bp.route("/upsc/eco/<topic_id>")
@login_required
def eco_topic(topic_id):
    conn = g.upsc_conn
    if not conn:
        return render_template(
            "upsc_eco_topic.html", active_page="upsc_dashboard",
            topic=None, questions=[], error="Eco-Optional database not found.",
        )

    topic = _get_topic(conn, topic_id)
    if not topic:
        return render_template(
            "upsc_eco_topic.html", active_page="upsc_dashboard",
            topic=None, questions=[], error="Topic not found.",
        )

    show_all = request.args.get("show_all", "0") == "1"
    sel_year = request.args.get("year")
    if sel_year:
        try:
            sel_year = int(sel_year)
        except (ValueError, TypeError):
            sel_year = None

    questions_all = _get_questions(conn, topic_id)
    has_ans = [q for q in questions_all if q["answer_id"]]
    no_ans = [q for q in questions_all if not q["answer_id"]]

    display_qs = questions_all if show_all else has_ans
    available_years = sorted(set(q["year"] for q in display_qs if q["year"]), reverse=True)

    if sel_year is None and not show_all and available_years:
        sel_year = available_years[0]

    filtered_qs = (
        [q for q in display_qs if q["year"] == sel_year] if sel_year else display_qs
    )

    return render_template(
        "upsc_eco_topic.html",
        active_page="upsc_dashboard",
        topic=topic,
        questions=filtered_qs,
        available_years=available_years,
        sel_year=sel_year,
        show_all=show_all,
        has_ans_count=len(has_ans),
        no_ans_count=len(no_ans),
        error=None,
    )


@upsc_eco_bp.route("/upsc/eco/<topic_id>/q/<question_id>")
@login_required
def eco_question(topic_id, question_id):
    conn = g.upsc_conn
    question = _get_question(conn, question_id) if conn else None
    if not question:
        return render_template(
            "upsc_eco_question.html", active_page="upsc_dashboard",
            topic_id=topic_id, question=None, error="Question not found.",
        )

    question["_key_concepts"] = _jl(question.get("key_concepts"))

    rubric = _get_rubric(conn, question_id)
    rubric_pts = _jl(rubric.get("rubric_points")) if rubric else []

    model_answer = _get_answer(conn, question_id)

    submitted = request.args.get("submitted") == "1"
    attempt_id = request.args.get("attempt_id", "")
    attempt = None
    if attempt_id:
        row = conn.execute(
            "SELECT * FROM descriptive_attempts WHERE attempt_id=? AND user_id=? AND exam_id=?",
            (attempt_id, g.user_id, _EXAM_ID),
        ).fetchone()
        if row:
            attempt = dict(row)
            if attempt.get("scores_json"):
                try:
                    attempt["_scores"] = json.loads(attempt["scores_json"])
                except (ValueError, TypeError):
                    attempt["_scores"] = None

    _, quota_reason = can_use_feature(g.user_id, "ai_scoring") if g.user_id else (False, "not_enabled")

    history_rows = conn.execute(
        """SELECT weighted_score, created_at, model_revealed, revealed_at, input_mode
           FROM descriptive_attempts
           WHERE user_id=? AND question_id=? AND exam_id=?
           ORDER BY created_at DESC""",
        (g.user_id, question_id, _EXAM_ID),
    ).fetchall()
    attempts = [
        {
            "score_value": r["weighted_score"] * 10 if r["weighted_score"] is not None else None,
            "score_label": f"{r['weighted_score']:.1f}/10" if r["weighted_score"] is not None else "Not scored",
            "timestamp": r["created_at"],
            "model_revealed": bool(r["model_revealed"]),
            "revealed_at": r["revealed_at"],
            "input_mode": r["input_mode"] or "typed",
        }
        for r in history_rows
    ]

    wc = _wc(question.get("marks"))

    return render_template(
        "upsc_eco_question.html",
        active_page="upsc_dashboard",
        topic_id=topic_id,
        question=question,
        rubric_pts=rubric_pts,
        model_answer=model_answer,
        wc=wc,
        submitted=submitted,
        attempt=attempt,
        attempts=attempts,
        quota_reason=quota_reason,
        error=None,
    )


@upsc_eco_bp.route("/upsc/eco/<topic_id>/q/<question_id>/submit", methods=["POST"])
@login_required
def eco_question_submit(topic_id, question_id):
    conn = g.upsc_conn
    question = _get_question(conn, question_id) if conn else None
    if not question:
        return redirect(url_for("upsc_eco.eco_topic", topic_id=topic_id))

    intro = request.form.get("intro", "").strip()
    body = request.form.get("body", "").strip()
    conclusion = request.form.get("conclusion", "").strip()

    conn.execute(
        "INSERT INTO descriptive_attempts "
        "(user_id, question_id, exam_id, quiz_mode, "
        "user_answer_intro, user_answer_body, user_answer_conclusion, "
        "word_count_intro, word_count_body, word_count_conclusion, session_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            g.user_id, question_id, _EXAM_ID, "detail",
            intro or None, body or None, conclusion or None,
            len(intro.split()) if intro else 0,
            len(body.split()) if body else 0,
            len(conclusion.split()) if conclusion else 0,
            uuid.uuid4().hex[:12],
        ),
    )
    conn.commit()
    attempt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    allowed, _ = can_use_feature(g.user_id, "ai_scoring")
    if allowed:
        rubric = _get_rubric(conn, question_id)
        rubric_pts = _jl(rubric.get("rubric_points")) if rubric else []
        result = _score_eco_answer(
            question["question_text"], question.get("marks") or 0,
            rubric_pts, intro, body, conclusion,
        )
        if result:
            conn.execute(
                "UPDATE descriptive_attempts SET scores_json=?, weighted_score=? WHERE attempt_id=?",
                (json.dumps(result), result["weighted_score"], attempt_id),
            )
            conn.commit()
            increment_feature_usage(g.user_id, "ai_scoring")

    return redirect(url_for(
        "upsc_eco.eco_question", topic_id=topic_id, question_id=question_id,
        submitted=1, attempt_id=attempt_id,
    ))
