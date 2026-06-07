"""IES Return Quiz blueprint — /ies/return-quiz (MCQ mastery check)."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, current_app, g, redirect, render_template, request, session, url_for
from auth import login_required
from db import (
    EXAM_ID, get_conn, get_mcq_questions, get_topics, get_true_readiness,
    init_user, log_event, submit_return_quiz, track_page_time,
)

ies_return_quiz_bp = Blueprint("ies_return_quiz", __name__)

PAPERS = [
    ("ge_01", "GE-01 · Micro & Macro"),
    ("ge_02", "GE-02 · Stats & Math"),
    ("ge_03", "GE-03 · Indian Economy"),
    ("ge_04", "GE-04 · Eco Policy"),
]
PAPER_IDS = [p[0] for p in PAPERS]

_STATE_ORDER = {"FLAGGED": 0, "PARTIAL": 1, "IN_STUDY": 2, "DECAYING": 3, "UNVISITED": 4, "VERIFIED": 5}
_STATE_ICON = {"VERIFIED": "✅", "PARTIAL": "🟡", "FLAGGED": "🔴", "DECAYING": "🔁"}


def _topics_sorted(conn, paper_id):
    topics = get_topics(conn, paper_id)
    return sorted(
        topics,
        key=lambda t: (_STATE_ORDER.get(t["state"] or "UNVISITED", 9), -(t.get("base_priority_score") or 0))
    )


@ies_return_quiz_bp.route("/ies/return-quiz")
@login_required
def return_quiz():
    conn = get_conn()
    user_id = g.user_id
    init_user(conn, user_id)
    track_page_time(conn, "Return Quiz")

    paper = request.args.get("paper", "ge_01")
    if paper not in PAPER_IDS:
        paper = "ge_01"

    topics = _topics_sorted(conn, paper)
    topic_ids = [t["topic_id"] for t in topics]
    default_topic = topic_ids[0] if topic_ids else ""
    topic_id = request.args.get("topic", default_topic)
    if topic_id not in topic_ids:
        topic_id = default_topic

    topic_info = next((t for t in topics if t["topic_id"] == topic_id), None)
    questions = get_mcq_questions(conn, topic_id) if topic_id else []

    readiness = get_true_readiness(conn)

    # Check for result in session
    result_key = f"rq_result_{topic_id}"
    show_result = request.args.get("result") == "1" and result_key in session
    last_result = session.get(result_key) if show_result else None

    # Compute per-question review data if showing results
    question_reviews = []
    if last_result:
        submitted_answers = last_result.get("answers", {})
        for q in questions:
            qid = q["question_id"]
            user_ans = submitted_answers.get(qid, "")
            opts = sorted([o for o in [
                q.get("correct_answer"), q.get("option_b"),
                q.get("option_c"), q.get("option_d")
            ] if o])
            is_correct = user_ans.strip() == (q["correct_answer"] or "").strip()
            question_reviews.append({
                "q": q, "user_ans": user_ans, "is_correct": is_correct,
                "opts": opts,
                "dim": q.get("dimension_id") or "concept",
            })

    # Topic labels for selectbox
    topic_labels = []
    for t in topics:
        mastery_pct = int((t.get("mastery_level") or 0.0) * 100)
        icon = _STATE_ICON.get(t["state"] or "UNVISITED", "○")
        topic_labels.append({
            "id": t["topic_id"],
            "name": t["topic_name"],
            "label": f"{icon} {t['topic_name']} ({mastery_pct}%)",
        })

    # Next topic for navigation
    curr_idx = topic_ids.index(topic_id) if topic_id in topic_ids else 0
    next_topic = topics[(curr_idx + 1) % len(topics)] if topics else None

    # Session ID for fresh quiz
    session_key = f"rq_session_{topic_id}"
    if session_key not in session:
        session[session_key] = str(uuid.uuid4())
    session_id = session[session_key]

    error_msg = session.pop("rq_error", None)

    return render_template(
        "ies_return_quiz.html",
        active_page="return_quiz",
        papers=PAPERS,
        paper=paper,
        topics=topics,
        topic_labels=topic_labels,
        topic_id=topic_id,
        topic_info=topic_info,
        questions=questions,
        readiness=readiness,
        show_result=show_result,
        last_result=last_result,
        question_reviews=question_reviews,
        next_topic=next_topic,
        session_id=session_id,
        error_msg=error_msg,
    )


@ies_return_quiz_bp.route("/ies/return-quiz/submit", methods=["POST"])
@login_required
def submit():
    conn = get_conn()
    paper = request.form.get("paper", "ge_01")
    topic_id = request.form.get("topic_id", "")
    session_id = request.form.get("session_id", str(uuid.uuid4()))

    questions = get_mcq_questions(conn, topic_id)
    if not questions:
        return redirect(url_for("ies_return_quiz.return_quiz", paper=paper, topic=topic_id))

    # Collect answers from form
    answers = {}
    for q in questions:
        qid = q["question_id"]
        answers[qid] = request.form.get(f"ans_{qid}", "")

    # Check all answered
    unanswered = [i + 1 for i, q in enumerate(questions) if not answers.get(q["question_id"])]
    if unanswered:
        # Redirect back with error in session
        session["rq_error"] = f"Please answer Q{', Q'.join(str(n) for n in unanswered)} before submitting."
        return redirect(url_for("ies_return_quiz.return_quiz", paper=paper, topic=topic_id))

    # Grade
    try:
        result = submit_return_quiz(conn, topic_id, answers, session_id, user_id=g.user_id)
    except Exception as e:
        current_app.logger.error(
            "submit_return_quiz failed user=%s topic=%s: %s", g.user_id, topic_id, e, exc_info=True
        )
        session["rq_error"] = "Something went wrong saving your quiz — please try again."
        return redirect(url_for("ies_return_quiz.return_quiz", paper=paper, topic=topic_id))

    if result:
        log_event("return_quiz_submitted", entity_type="topic", entity_id=topic_id,
                  exam_id=EXAM_ID,
                  payload={"score": round(result["score"], 4), "correct": result["correct"],
                           "total": result["total"], "session_id": session_id})

    # Store result in session
    session[f"rq_result_{topic_id}"] = {
        "result": result,
        "answers": answers,
    }
    # Reset session_id for next attempt
    session[f"rq_session_{topic_id}"] = str(uuid.uuid4())

    return redirect(url_for(
        "ies_return_quiz.return_quiz",
        paper=paper, topic=topic_id, result="1"
    ))
