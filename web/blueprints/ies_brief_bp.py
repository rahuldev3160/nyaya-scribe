"""Study Brief blueprint — /ies/brief"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, render_template, request
from auth import login_required
from db import get_conn, get_topics, get_study_brief, log_event, track_page_time, EXAM_ID

ies_brief_bp = Blueprint("ies_brief", __name__)

PAPER_LABELS = {
    "ge_01": "GE-01 Micro/Macro",
    "ge_02": "GE-02 Stats/Math",
    "ge_03": "GE-03 Indian Economy",
    "ge_04": "GE-04 Economic Policy",
}


@ies_brief_bp.route("/ies/brief")
@login_required
def brief():
    conn = get_conn()
    track_page_time(conn, "Study Brief")

    paper = request.args.get("paper", "ge_01")
    if paper not in PAPER_LABELS:
        paper = "ge_01"

    topics = get_topics(conn, paper)
    topic_opts = {t["topic_id"]: t["topic_name"] for t in topics}

    default_topic = list(topic_opts.keys())[0] if topic_opts else None
    topic_id = request.args.get("topic", default_topic)
    if topic_id not in topic_opts:
        topic_id = default_topic

    brief_data = get_study_brief(conn, topic_id) if topic_id else None

    score = 0
    pyq_count = 0
    years_asked = 0
    plain_text = ""

    if brief_data and brief_data["topic"] and topic_id:
        bs = brief_data["base_score"]
        score = bs.get("base_priority_score", 0) or 0
        pyq_count = bs.get("pyq_count", 0) or 0
        years_asked = bs.get("distinct_years", 0) or 0

        log_event(
            "topic_opened",
            entity_type="topic", entity_id=topic_id, exam_id=EXAM_ID,
            payload={"paper_id": paper, "priority_score": round(score, 4)},
        )

        t = brief_data["topic"]
        lines = [
            f"IES 2026 STUDY CONTEXT: {t.get('topic_name', '')}",
            f"Paper: {paper.upper().replace('_', '-')} | Priority: {score:.3f} | PYQs: {pyq_count} across {years_asked} years",
            "",
        ]
        if brief_data["subtopics"]:
            lines += ["SYLLABUS:"] + [f"  • {s}" for s in brief_data["subtopics"]] + [""]
        if brief_data["key_terms"]:
            lines += ["KEY TERMS:"] + [f"  • {k}" for k in brief_data["key_terms"]] + [""]
        if brief_data["diagrams"]:
            lines += ["DIAGRAMS:"] + [f"  • {d} ({c}x)" for d, c in brief_data["diagrams"].items()] + [""]
        lines.append(f"TOP {len(brief_data['questions'])} QUESTIONS:")
        lines.append("-" * 60)
        for i, q in enumerate(brief_data["questions"], 1):
            m  = f"{q['marks']}m" if q["marks"] else "?m"
            wc = f"/{q['answer_length']}w" if q["answer_length"] else ""
            lines += ["", f"Q{i}. [{q['year']} | {m}{wc}]", q["question_text"]]
            if q["rubric_points"]:
                lines.append(f"   Rubric ({len(q['rubric_points'])} points):")
                for rp in q["rubric_points"]:
                    lines.append(f"   [{rp.get('section_hint', '')}] {rp.get('point', '')}")
        plain_text = "\n".join(lines)
    else:
        brief_data = None

    return render_template(
        "ies_brief.html",
        active_page="study_brief",
        paper=paper,
        paper_labels=PAPER_LABELS,
        topics=topics,
        topic_id=topic_id,
        topic_opts=topic_opts,
        brief=brief_data,
        plain_text=plain_text,
        score=score,
        pyq_count=pyq_count,
        years_asked=years_asked,
    )
