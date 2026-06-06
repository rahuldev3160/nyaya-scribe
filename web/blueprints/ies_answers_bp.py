"""IES Model Answers blueprint — /ies/answers and /ies/diagram/<dtype>.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, render_template, request

from auth import login_required
from db import EXAM_ID, get_conn, get_topics, get_questions, jl, track_page_time

ies_answers_bp = Blueprint("ies_answers", __name__)

_DTYPE_ALIASES = {
    "is-lm curve": "is_lm_curve",
    "is_lm_bp_curve": "is_lm_curve",
    "isoquant-isocost tangency diagram": "isoquant",
    "isoquant diagram illustrating elasticity of substitution": "isoquant",
    "isoquant diagram showing unit elasticity of substitution": "isoquant",
    "isoquant map showing factor substitution under different ρ values": "isoquant",
    "isoquant intersection diagram (factor intensity reversal)": "isoquant",
    "expansion path / isoquant-isocost diagram": "isoquant",
    "isoquant-isocost diagram with expansion path": "isoquant",
    "long-run phillips curve (friedman's natural rate hypothesis)": "phillips_curve",
    "environmental kuznets curve": "lorenz_curve",
    "environmental kuznets curve (inverted-u)": "lorenz_curve",
    "lewis two-sector structural transformation diagram": "growth_model",
    "production possibilities curve": "production_function",
    "production possibility frontier (capital goods vs. wage goods)": "production_function",
}


def _norm_dtype(dtype):
    d = (dtype or "").lower().strip()
    return _DTYPE_ALIASES.get(d, d.replace(" ", "_").replace("-", "_"))


_PAPER_LABELS = {
    "ge_01": "GE Paper I",
    "ge_02": "GE Paper II",
    "ge_03": "GE Paper III",
    "ge_04": "GE Paper IV",
}


@ies_answers_bp.route("/ies/answers")
@login_required
def answers():
    conn = get_conn()
    track_page_time(conn, "model_answers")

    from diagrams import COVERED_TYPES

    paper = request.args.get("paper", "ge_01")
    topic_id = request.args.get("topic", "")
    year_filter = request.args.get("year", "")
    show_all = request.args.get("show_all", "0") == "1"

    all_topics = get_topics(conn, paper_id=paper)

    if not topic_id and all_topics:
        topic_id = all_topics[0]["topic_id"]

    current_topic = next((t for t in all_topics if t["topic_id"] == topic_id), None)

    all_questions = get_questions(conn, topic_id=topic_id if topic_id else None,
                                  paper_id=paper)

    # Collect distinct years for navigation
    years = sorted({q["year"] for q in all_questions if q["year"]}, reverse=True)

    # Default to most recent year when no filter is specified
    if not year_filter and not show_all and years:
        year_filter = str(years[0])

    # Filter by year unless show_all
    if year_filter and not show_all:
        filtered_qs = [q for q in all_questions if str(q["year"]) == year_filter]
    elif show_all:
        filtered_qs = all_questions
    else:
        filtered_qs = all_questions

    from table_renderer import render_table

    # Batch-fetch all answers in one query instead of N individual queries
    answer_qids = [q["question_id"] for q in filtered_qs if q.get("answer_id")]
    answers_map: dict = {}
    if answer_qids:
        placeholders = ",".join("?" * len(answer_qids))
        rows = conn.execute(
            f"""SELECT ma.*, q.question_text, q.marks, q.year, q.paper_id,
                       q.topic_id, q.answer_length,
                       r.rubric_points, r.key_terms, r.diagram_expected, r.diagram_type
                FROM model_answers ma
                JOIN pyq_questions q ON ma.question_id=q.question_id AND ma.exam_id=q.exam_id
                LEFT JOIN question_rubrics r ON q.question_id=r.question_id AND q.exam_id=r.exam_id
                WHERE ma.question_id IN ({placeholders}) AND ma.exam_id=?""",
            answer_qids + [EXAM_ID],
        ).fetchall()
        for row in rows:
            answers_map[row["question_id"]] = dict(row)

    for q in filtered_qs:
        q["_key_terms"] = jl(q.get("key_terms"))
        q["_rubric_pts"] = jl(q.get("rubric_points"))
        q["_answer"] = None
        if q.get("answer_id"):
            ans = answers_map.get(q["question_id"])
            if ans:
                ans["_data_points"] = jl(ans.get("data_points"))
                ans["_schemes"] = jl(ans.get("schemes_referenced"))
                ans["_key_terms_used"] = jl(ans.get("key_terms_used"))
                ans["_labels"] = jl(ans.get("diagram_labels"))
                ans["_norm_dtype"] = _norm_dtype(ans.get("diagram_type") or "")
                if ans.get("diagram_type") == "table" and ans.get("diagram_description"):
                    ans["_table_html"] = render_table(ans["diagram_description"])
                else:
                    ans["_table_html"] = ""
                q["_answer"] = ans

    answers_ready = sum(1 for q in filtered_qs if q.get("_answer"))

    return render_template(
        "ies_answers.html",
        active_page="model_answers",
        paper=paper,
        paper_label=_PAPER_LABELS.get(paper, paper.upper()),
        all_topics=all_topics,
        topic_id=topic_id,
        current_topic=current_topic,
        years=years,
        year_filter=year_filter,
        show_all=show_all,
        filtered_qs=filtered_qs,
        answers_ready=answers_ready,
        covered_types=list(COVERED_TYPES),
        paper_labels=_PAPER_LABELS,
    )


@ies_answers_bp.route("/ies/diagram/<dtype>.png")
def diagram_png(dtype):
    import io
    import matplotlib.pyplot as plt
    from flask import Response
    from diagrams import get_standard_diagram, COVERED_TYPES

    normalized = _norm_dtype(dtype.replace("_", " "))
    if normalized not in COVERED_TYPES:
        normalized = dtype.replace("-", "_")
        if normalized not in COVERED_TYPES:
            return "Not found", 404

    fig = get_standard_diagram(normalized)
    if not fig:
        return "Not found", 404

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor="#1C1C1E", edgecolor="none", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return Response(buf.getvalue(), content_type="image/png",
                    headers={"Cache-Control": "max-age=3600"})
