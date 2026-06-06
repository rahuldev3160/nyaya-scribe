"""IES Quiz blueprint — /ies/quiz (descriptive with model answer comparison)."""
import random
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, redirect, render_template, request, url_for
from auth import login_required
from db import EXAM_ID, get_answer, get_conn, get_questions, get_topics, jl, track_page_time

ies_quiz_bp = Blueprint("ies_quiz", __name__)

DEFAULT_QID = "ge_01_0001"

WC_GUIDE = {
    (0, 7): (25, 55, 20), (7, 12): (35, 90, 25),
    (12, 18): (50, 140, 30), (18, 25): (60, 190, 40), (25, 999): (80, 340, 80),
}

_Q_PREFIX = re.compile(r"^Q\s*\d+[a-z]?[\.\) ]*\s*", re.IGNORECASE)
_SUB_PREFIX = re.compile(r"^[a-z]\.\s+", re.IGNORECASE)

PAPER_LABELS = {
    "ge_01": "GE-01", "ge_02": "GE-02", "ge_03": "GE-03", "ge_04": "GE-04",
}


def _wc(marks):
    if not marks:
        return WC_GUIDE[(7, 12)]
    for (lo, hi), g in WC_GUIDE.items():
        if lo <= marks < hi:
            return g
    return WC_GUIDE[(7, 12)]


def _concept(text: str, max_chars: int = 60) -> str:
    clean = _Q_PREFIX.sub("", (text or "").strip())
    clean = _SUB_PREFIX.sub("", clean.strip())
    return clean[:max_chars] + ("…" if len(clean) > max_chars else "")


def _q_label(q, idx: int = None) -> str:
    paper = (q["paper_id"] or "").upper().replace("_", "-")
    num = f" · #{idx:04d}" if idx is not None else ""
    return f"{q['year']} · {paper} · {_concept(q['question_text'])} · {q['marks']}m{num}"


@ies_quiz_bp.route("/ies/quiz")
@login_required
def quiz():
    conn = get_conn()
    track_page_time(conn, "Quiz", exam_id=EXAM_ID)

    # Load prior attempt if redirected from submit
    attempt_id = request.args.get("attempt_id", "")
    attempt = None
    if attempt_id:
        row = conn.execute(
            "SELECT * FROM descriptive_attempts WHERE attempt_id=? AND user_id=?",
            (attempt_id, g.user_id),
        ).fetchone()
        if row:
            attempt = dict(row)

    # All answered questions, sorted year DESC
    all_qs = sorted(
        [q for q in get_questions(conn) if q.get("answer_id")],
        key=lambda q: (-(q["year"] or 0), q["paper_id"] or "", q["question_id"])
    )
    all_qids = {q["question_id"] for q in all_qs}
    global_idx = {q["question_id"]: i + 1 for i, q in enumerate(all_qs)}

    mode = request.args.get("mode", "year-wise")
    years = sorted(set(q["year"] for q in all_qs if q["year"]), reverse=True)

    topics_by_paper = {}
    topic_opts = {}
    selected_paper = request.args.get("paper", "ge_01")
    selected_topic = request.args.get("topic", "")

    if mode == "year-wise":
        year_str = request.args.get("year", str(years[0]) if years else "")
        if year_str == "all":
            qs = all_qs
        else:
            try:
                yr = int(year_str)
                qs = [q for q in all_qs if q["year"] == yr]
            except (ValueError, TypeError):
                qs = all_qs
                year_str = "all"
        qs_with_labels = [(q["question_id"], _q_label(q, i + 1)) for i, q in enumerate(qs)]
    elif mode == "by-topic":
        topics_list = get_topics(conn, selected_paper)
        topic_opts = {t["topic_id"]: t["topic_name"] for t in topics_list}
        # If topic from a different paper was requested, auto-switch paper so dropdown is coherent
        if selected_topic and selected_topic not in topic_opts:
            row = conn.execute(
                "SELECT paper_id FROM topics WHERE topic_id=? AND exam_id=? AND topic_level='topic'",
                (selected_topic, EXAM_ID),
            ).fetchone()
            if row:
                selected_paper = row["paper_id"]
                topics_list = get_topics(conn, selected_paper)
                topic_opts = {t["topic_id"]: t["topic_name"] for t in topics_list}
        if not selected_topic and topics_list:
            selected_topic = topics_list[0]["topic_id"]
        qs = sorted(
            [q for q in all_qs if q.get("topic_id") == selected_topic],
            key=lambda q: (-(q["year"] or 0), -(q["marks"] or 0))
        )
        qs_with_labels = [
            (q["question_id"], _q_label(q, global_idx.get(q["question_id"])))
            for q in qs
        ]
        year_str = ""
    else:  # random
        qs = all_qs
        qs_with_labels = [(q["question_id"], _q_label(q)) for q in qs]
        year_str = ""

    qids = [q["question_id"] for q in qs]
    qid = request.args.get("qid", "")

    if mode == "random":
        if not qid or qid not in all_qids:
            qid = random.choice(all_qs)["question_id"] if all_qs else DEFAULT_QID
    else:
        if not qid or qid not in qids:
            qid = qids[0] if qids else DEFAULT_QID

    selected_q = next((q for q in qs if q["question_id"] == qid), None)
    if not selected_q and all_qs:
        selected_q = all_qs[0]
        qid = selected_q["question_id"]

    # Compute next question id for navigation
    if qids and qid in qids:
        next_qid = qids[(qids.index(qid) + 1) % len(qids)]
    else:
        next_qid = qid

    marks = selected_q["marks"] if selected_q else None
    wc = _wc(marks)
    rubric_pts = jl(selected_q.get("rubric_points")) if selected_q else []

    # Fetch model answer text for the selected question (not included in get_questions to avoid
    # loading full text for all 1200+ questions on every page view)
    if selected_q and selected_q.get("answer_id"):
        ma = get_answer(conn, selected_q["question_id"])
        if ma:
            selected_q = {**selected_q,
                          "intro_text": ma.get("intro_text") or "",
                          "body_text": ma.get("body_text") or "",
                          "conclusion_text": ma.get("conclusion_text") or ""}

    return render_template(
        "ies_quiz.html",
        active_page="quiz",
        mode=mode,
        year_str=year_str if mode == "year-wise" else "",
        years=years,
        paper=selected_paper,
        paper_labels=PAPER_LABELS,
        topic_id=selected_topic,
        topic_opts=topic_opts,
        qs_with_labels=qs_with_labels,
        qid=qid,
        next_qid=next_qid,
        selected_q=selected_q,
        marks=marks,
        wc=wc,
        rubric_pts=rubric_pts,
        total_qs=len(all_qs),
        attempt=attempt,
    )


@ies_quiz_bp.route("/ies/quiz/submit", methods=["POST"])
@login_required
def quiz_submit():
    conn = get_conn()
    qid = request.form.get("qid", "")
    intro = request.form.get("intro", "").strip()
    body = request.form.get("body", "").strip()
    conclusion = request.form.get("conclusion", "").strip()
    mode = request.form.get("mode", "year-wise")
    year_str = request.form.get("year_str", "")
    paper = request.form.get("paper", "ge_01")
    topic_id = request.form.get("topic_id", "")

    conn.execute(
        "INSERT INTO descriptive_attempts "
        "(user_id, question_id, exam_id, quiz_mode, "
        "user_answer_intro, user_answer_body, user_answer_conclusion, "
        "word_count_intro, word_count_body, word_count_conclusion, session_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            g.user_id, qid, EXAM_ID, mode,
            intro or None, body or None, conclusion or None,
            len(intro.split()) if intro else 0,
            len(body.split()) if body else 0,
            len(conclusion.split()) if conclusion else 0,
            uuid.uuid4().hex[:12],
        ),
    )
    conn.commit()
    attempt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    return redirect(url_for(
        "ies_quiz.quiz",
        mode=mode, qid=qid, attempt_id=attempt_id,
        year=year_str, paper=paper, topic=topic_id,
    ))


@ies_quiz_bp.route("/ies/quiz/rate", methods=["POST"])
@login_required
def quiz_rate():
    conn = get_conn()
    attempt_id = request.form.get("attempt_id", "")
    rating = request.form.get("rating", "")
    mode = request.form.get("mode", "year-wise")
    qid = request.form.get("qid", "")
    year_str = request.form.get("year_str", "")
    paper = request.form.get("paper", "ge_01")
    topic_id = request.form.get("topic_id", "")

    if rating in ("got_it", "partial", "missed") and attempt_id:
        conn.execute(
            "UPDATE descriptive_attempts SET self_rating=? WHERE attempt_id=? AND user_id=?",
            (rating, attempt_id, g.user_id),
        )
        conn.commit()

    return redirect(url_for(
        "ies_quiz.quiz",
        mode=mode, qid=qid, attempt_id=attempt_id,
        year=year_str, paper=paper, topic=topic_id,
    ))
