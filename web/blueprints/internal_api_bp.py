"""Internal API blueprint -- /internal/v1/* -- service-to-service routes for Nyaya Arena.

Guarded by a static X-Arena-Api-Key header (constant-time compare against the
ARENA_SERVICE_API_KEY env var), not Scribe's own user-session auth. Every route
here is stateless: it reads existing content tables and writes nothing back to
rbi_attempts, feature_gates, or user_feature_usage -- see Nyaya Arena's
docs/API_CONTRACTS.md (Contract 2) and docs/decisions.md DECIDE-09/DECIDE-10.

Deviation from the written contract (flag for a contract-doc correction, not a
bug here): Contract 2 assumed descriptive/rubric-based content for
exam_id='rbi'. The actual rbi_questions table is MCQ (4 options, correct_option
A-D), no rubric/marks columns, no per-question language variants. This
blueprint implements deterministic MCQ fetch+score for 'rbi' -- closer in shape
to Recall's Contract 1 than to Scribe's own descriptive _score_answer() -- and
returns LANGUAGE_NOT_SUPPORTED for anything but 'en', since there is nothing
here for a language field to select between yet.
"""
import hmac
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, jsonify, request

internal_api_bp = Blueprint("internal_api", __name__, url_prefix="/internal/v1")

_DEFAULT_MARKING_SCHEME = {"correct": 1, "wrong": -0.25, "unattempted": 0}
_KNOWN_EXAM_IDS = {"rbi"}


def _error(code: str, message: str, status: int, details: dict | None = None):
    return jsonify({"error": {"code": code, "message": message, "details": details or {}}}), status


@internal_api_bp.before_request
def _check_arena_key():
    expected = os.environ.get("ARENA_SERVICE_API_KEY")
    if not expected:
        # Fail closed: an unconfigured key disables every internal route, not just auth.
        return _error("AUTH_FAILED", "Internal API not configured.", 401)
    provided = request.headers.get("X-Arena-Api-Key", "")
    if not hmac.compare_digest(provided, expected):
        return _error("AUTH_FAILED", "Missing or invalid X-Arena-Api-Key.", 401)


def _unknown_exam(exam_id: str):
    return _error("NOT_FOUND", f"Unknown exam_id: {exam_id}", 404, {"code": "UNKNOWN_EXAM_ID"})


def _unsupported_language(exam_id: str, language: str):
    return _error(
        "INVALID_PARAMS",
        f"language '{language}' not supported for exam_id '{exam_id}'.",
        400,
        {"code": "LANGUAGE_NOT_SUPPORTED", "exam_id": exam_id, "supported_languages": ["en"]},
    )


@internal_api_bp.route("/exams/<exam_id>/questions", methods=["GET"])
def get_exam_questions(exam_id):
    if exam_id not in _KNOWN_EXAM_IDS:
        return _unknown_exam(exam_id)

    language = request.args.get("language", "en")
    if language != "en":
        return _unsupported_language(exam_id, language)

    raw_count = request.args.get("count", "")
    try:
        count = int(raw_count)
    except ValueError:
        return _error("INVALID_PARAMS", "count must be an integer.", 400)
    if not (1 <= count <= 50):
        return _error("INVALID_PARAMS", "count must be between 1 and 50.", 400)

    topic = request.args.get("topic")
    difficulty = request.args.get("difficulty")

    conn = g.rbi_conn
    if conn is None:
        return _unknown_exam(exam_id)

    where = []
    params: list = []
    if topic:
        where.append("topic = ?")
        params.append(topic)
    if difficulty:
        where.append("difficulty = ?")
        params.append(difficulty)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    rows = conn.execute(
        f"SELECT id, question, option_a, option_b, option_c, option_d, subject, topic, difficulty "
        f"FROM rbi_questions {where_sql} ORDER BY RANDOM() LIMIT ?",
        (*params, count),
    ).fetchall()

    if len(rows) < count:
        available = conn.execute(
            f"SELECT COUNT(*) AS n FROM rbi_questions {where_sql}", params
        ).fetchone()["n"]
        return _error(
            "NOT_FOUND", "Not enough questions match the given filters.", 404,
            {"code": "INSUFFICIENT_QUESTIONS", "available_count": available},
        )

    questions = [
        {
            "question_id": r["id"],
            "question_text": r["question"],
            "options": {"A": r["option_a"], "B": r["option_b"], "C": r["option_c"], "D": r["option_d"]},
            "subject": r["subject"],
            "topic": r["topic"],
            "difficulty": r["difficulty"],
            "language": "en",
        }
        for r in rows
    ]
    return jsonify({"exam_id": exam_id, "count": len(questions), "questions": questions})


@internal_api_bp.route("/exams/<exam_id>/score", methods=["POST"])
def score_exam_attempt(exam_id):
    if exam_id not in _KNOWN_EXAM_IDS:
        return _unknown_exam(exam_id)

    body = request.get_json(silent=True) or {}
    answers = body.get("answers")
    if not isinstance(answers, list) or not answers:
        return _error("INVALID_PARAMS", "answers must be a non-empty list.", 400)

    language = body.get("language", "en")
    if language != "en":
        return _unsupported_language(exam_id, language)

    scheme = body.get("marking_scheme") or _DEFAULT_MARKING_SCHEME
    for key in ("correct", "wrong", "unattempted"):
        if key not in scheme:
            return _error("INVALID_PARAMS", f"marking_scheme missing '{key}'.", 400)

    conn = g.rbi_conn
    if conn is None:
        return _unknown_exam(exam_id)

    question_ids = [a.get("question_id") for a in answers]
    if any(qid is None for qid in question_ids):
        return _error("INVALID_PARAMS", "Every answer needs a question_id.", 400)

    placeholders = ",".join("?" for _ in question_ids)
    rows = conn.execute(
        f"SELECT id, correct_option, explanation FROM rbi_questions WHERE id IN ({placeholders})",
        question_ids,
    ).fetchall()
    by_id = {r["id"]: r for r in rows}

    unknown = [qid for qid in question_ids if qid not in by_id]
    if unknown:
        return _error(
            "NOT_FOUND", "One or more question_ids are unknown.", 404,
            {"code": "UNKNOWN_QUESTION_IDS", "unknown_ids": unknown},
        )

    results = []
    score = 0.0
    correct_count = wrong_count = unattempted_count = 0
    for a in answers:
        qid = a["question_id"]
        selected = a.get("selected_option")
        row = by_id[qid]
        correct_option = row["correct_option"]
        if selected is None:
            marks_awarded = scheme["unattempted"]
            unattempted_count += 1
            is_correct = None
        elif selected == correct_option:
            marks_awarded = scheme["correct"]
            correct_count += 1
            is_correct = True
        else:
            marks_awarded = scheme["wrong"]
            wrong_count += 1
            is_correct = False
        score += marks_awarded
        results.append({
            "question_id": qid,
            "selected_option": selected,
            "correct_option": correct_option,
            "is_correct": is_correct,
            "marks_awarded": marks_awarded,
            "explanation": row["explanation"],
        })

    max_score = len(answers) * scheme["correct"]
    return jsonify({
        "score": round(score, 2),
        "max_score": max_score,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "unattempted_count": unattempted_count,
        "results": results,
    })
