"""UPSC blueprint — /upsc/mains"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, render_template, request
from auth import login_required

upsc_bp = Blueprint("upsc", __name__)

_EXAM_ID = "upsc_eco_opt"

_PAPER_LABELS = {
    "upsc_p1": "Paper I — Theory",
    "upsc_p2": "Paper II — Indian Economy",
}


def _jl(s) -> list:
    if not s:
        return []
    try:
        r = json.loads(s)
        return r if isinstance(r, list) else []
    except Exception:
        return []


def _get_topics(conn, paper_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT topic_id, topic_name FROM topics
           WHERE exam_id=? AND paper_id=? AND topic_level='topic'
           ORDER BY topic_id""",
        (_EXAM_ID, paper_id),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_questions(conn, topic_id: str, paper_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT q.question_id, q.question_text, q.marks, q.year, q.paper_id,
                  q.topic_id, q.answer_length,
                  r.rubric_points, r.key_terms, r.diagram_expected, r.diagram_type,
                  ma.answer_id
           FROM pyq_questions q
           LEFT JOIN question_rubrics r ON q.question_id=r.question_id AND q.exam_id=r.exam_id
           LEFT JOIN model_answers ma ON q.question_id=ma.question_id AND q.exam_id=ma.exam_id
           WHERE q.exam_id=? AND q.topic_id=? AND q.paper_id=?
           ORDER BY q.marks DESC NULLS LAST, q.year DESC""",
        (_EXAM_ID, topic_id, paper_id),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_answer(conn, question_id: str) -> dict | None:
    row = conn.execute(
        "SELECT ma.* FROM model_answers ma WHERE ma.question_id=? AND ma.exam_id=?",
        (question_id, _EXAM_ID),
    ).fetchone()
    return dict(row) if row else None


@upsc_bp.route("/upsc/mains")
@login_required
def mains():
    if not g.upsc_conn:
        return render_template(
            "upsc_mains.html",
            active_page="upsc_mains",
            error="UPSC database not found.",
            paper_labels=_PAPER_LABELS,
        )

    paper = request.args.get("paper", "upsc_p1")
    if paper not in _PAPER_LABELS:
        paper = "upsc_p1"

    show_all = request.args.get("show_all", "0") == "1"

    sel_year = request.args.get("year")
    if sel_year:
        try:
            sel_year = int(sel_year)
        except (ValueError, TypeError):
            sel_year = None

    topics = _get_topics(g.upsc_conn, paper)
    topic_opts = {t["topic_id"]: t["topic_name"] for t in topics}
    default_topic = topics[0]["topic_id"] if topics else None
    topic_id = request.args.get("topic", default_topic)

    # If topic_id given but not in current paper, auto-detect the correct paper
    if topic_id and topic_id not in topic_opts:
        row = g.upsc_conn.execute(
            "SELECT paper_id FROM topics WHERE topic_id=? AND exam_id=? AND topic_level='topic'",
            (topic_id, _EXAM_ID),
        ).fetchone()
        if row:
            paper = row["paper_id"]
            topics = _get_topics(g.upsc_conn, paper)
            topic_opts = {t["topic_id"]: t["topic_name"] for t in topics}
            default_topic = topics[0]["topic_id"] if topics else None
        else:
            topic_id = default_topic

    questions_all = _get_questions(g.upsc_conn, topic_id, paper) if topic_id else []
    has_ans = [q for q in questions_all if q["answer_id"]]
    no_ans = [q for q in questions_all if not q["answer_id"]]

    display_qs = questions_all if show_all else has_ans
    available_years = sorted(
        set(q["year"] for q in display_qs if q["year"]), reverse=True
    )

    # Default to most recent year when no year is specified
    if sel_year is None and not show_all and available_years:
        sel_year = available_years[0]

    filtered_qs = (
        [q for q in display_qs if q["year"] == sel_year] if sel_year else display_qs
    )

    # Fetch answers and parse JSON fields
    answers = {}
    for q in filtered_qs:
        if q["answer_id"]:
            ans = _get_answer(g.upsc_conn, q["question_id"])
            if ans:
                ans["_data_points"] = _jl(ans.get("data_points"))
                ans["_schemes"] = _jl(ans.get("schemes_referenced"))
                ans["_key_terms"] = _jl(ans.get("key_terms_used"))
                answers[q["question_id"]] = ans

    # Parse per-question JSON fields
    for q in filtered_qs:
        q["_key_terms"] = _jl(q.get("key_terms"))
        q["_rubric_pts"] = _jl(q.get("rubric_points"))

    return render_template(
        "upsc_mains.html",
        active_page="upsc_mains",
        paper=paper,
        paper_labels=_PAPER_LABELS,
        topics=topics,
        topic_opts=topic_opts,
        topic_id=topic_id,
        topic_name=topic_opts.get(topic_id, topic_id) if topic_id else "",
        paper_label=_PAPER_LABELS.get(paper, paper),
        questions=filtered_qs,
        answers=answers,
        available_years=available_years,
        sel_year=sel_year,
        show_all=show_all,
        has_ans_count=len(has_ans),
        no_ans_count=len(no_ans),
        error=None,
    )
