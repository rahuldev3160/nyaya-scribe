"""Ethics Paper blueprint — /upsc/ethics"""
import json
import uuid
from datetime import datetime

from flask import Blueprint, g, redirect, render_template, request, url_for

from auth import login_required

ethics_paper_bp = Blueprint("ethics_paper", __name__)

_ETHICS_YEARS = list(range(2019, 2026))


def _jl(s) -> list:
    if not s:
        return []
    try:
        r = json.loads(s)
        return r if isinstance(r, list) else []
    except Exception:
        return []


def _paper_title(paper_id: str) -> str:
    if paper_id.startswith("ethics_pyq_"):
        year = paper_id.replace("ethics_pyq_", "")
        return f"GS4 Ethics {year}"
    row = g.upsc_gs_conn.execute(
        "SELECT paper_title FROM ethics_practice_papers WHERE paper_id=?", (paper_id,)
    ).fetchone()
    return row["paper_title"] if row else paper_id


@ethics_paper_bp.route("/upsc/ethics")
@login_required
def ethics_landing():
    conn = g.upsc_gs_conn

    practice_paper_rows = conn.execute(
        "SELECT paper_id, paper_title, difficulty, theme_focus, total_marks FROM ethics_practice_papers ORDER BY paper_id"
    ).fetchall()
    practice_papers = [dict(r) for r in practice_paper_rows]

    concept_rows_raw = conn.execute(
        "SELECT concept_label, frequency_count, section_preference, fy26_probability, typical_marks FROM ethics_concept_analysis ORDER BY frequency_count DESC"
    ).fetchall()
    concept_rows = [dict(r) for r in concept_rows_raw]

    scenario_rows_raw = conn.execute(
        "SELECT scenario_label, frequency_count, core_dilemma_type, fy26_probability FROM ethics_scenario_analysis ORDER BY frequency_count DESC"
    ).fetchall()
    scenario_rows = [dict(r) for r in scenario_rows_raw]

    active_tab = request.args.get("tab", "practice")

    return render_template(
        "ethics_landing.html",
        active_page="upsc_ethics",
        practice_papers=practice_papers,
        years=_ETHICS_YEARS,
        concept_rows=concept_rows,
        scenario_rows=scenario_rows,
        active_tab=active_tab,
    )


@ethics_paper_bp.route("/upsc/ethics/framework-guide")
@login_required
def ethics_framework():
    return render_template(
        "ethics_framework.html",
        active_page="upsc_ethics",
    )


@ethics_paper_bp.route("/upsc/ethics/<paper_id>")
@login_required
def ethics_paper(paper_id):
    conn = g.upsc_gs_conn

    question_rows = conn.execute(
        "SELECT * FROM ethics_questions WHERE paper_id=? ORDER BY section, sequence_order",
        (paper_id,),
    ).fetchall()
    question_rows = [dict(r) for r in question_rows]

    for q in question_rows:
        q["_concept_tags"] = _jl(q.get("concept_tags"))
        q["_thinker_tags"] = _jl(q.get("thinker_tags"))

    attempt_count_rows = conn.execute(
        "SELECT question_id, COUNT(*) as cnt FROM ethics_attempts WHERE user_id=? GROUP BY question_id",
        (g.user_id,),
    ).fetchall()
    attempt_counts = {r["question_id"]: r["cnt"] for r in attempt_count_rows}

    section_a_rows = [q for q in question_rows if q.get("section") == "A"]

    section_b_questions = [q for q in question_rows if q.get("section") == "B"]
    section_b_groups = _group_section_b(section_b_questions)

    title = _paper_title(paper_id)

    return render_template(
        "ethics_paper.html",
        active_page="upsc_ethics",
        paper_id=paper_id,
        paper_title=title,
        section_a_rows=section_a_rows,
        section_b_groups=section_b_groups,
        attempt_counts=attempt_counts,
    )


def _group_section_b(questions: list) -> list:
    """Group Section B sub-questions by their base question prefix.

    e.g. ethics_pyq_2024_b01_a and ethics_pyq_2024_b01_b share prefix b01.
    Questions without a sub_part suffix are treated as standalone groups.
    """
    seen = {}
    ordered_keys = []

    for q in questions:
        qid = q["question_id"]
        sub_part = q.get("sub_part") or ""
        # Derive group key: strip trailing _a/_b/_c/_d to get parent prefix
        if sub_part and sub_part.lower() in ("a", "b", "c", "d"):
            # group key = question_id without the trailing _<sub_part>
            suffix = "_" + sub_part.lower()
            if qid.endswith(suffix):
                group_key = qid[: -len(suffix)]
            else:
                group_key = qid
        else:
            group_key = qid

        if group_key not in seen:
            seen[group_key] = {
                "preamble": q.get("case_preamble") or "",
                "sub_questions": [],
            }
            ordered_keys.append(group_key)
        # Update preamble: use the first non-empty one we encounter
        if not seen[group_key]["preamble"] and q.get("case_preamble"):
            seen[group_key]["preamble"] = q["case_preamble"]
        seen[group_key]["sub_questions"].append(q)

    return [seen[k] for k in ordered_keys]


@ethics_paper_bp.route("/upsc/ethics/<paper_id>/q/<question_id>", methods=["GET", "POST"])
@login_required
def ethics_question(paper_id, question_id):
    conn = g.upsc_gs_conn

    question_row = conn.execute(
        "SELECT * FROM ethics_questions WHERE question_id=?", (question_id,)
    ).fetchone()
    if not question_row:
        return render_template(
            "ethics_question.html",
            active_page="upsc_ethics",
            question=None,
            model_answer=None,
            prev_attempt=None,
            paper_id=paper_id,
            submitted=False,
            error="Question not found.",
        )

    question = dict(question_row)
    question["_concept_tags"] = _jl(question.get("concept_tags"))
    question["_thinker_tags"] = _jl(question.get("thinker_tags"))

    if request.method == "POST":
        action = request.form.get("action", "submit_attempt")

        if action == "submit_attempt":
            attempt_text = request.form.get("attempt_text", "").strip()
            try:
                word_count = int(request.form.get("word_count", 0))
            except (ValueError, TypeError):
                word_count = len(attempt_text.split()) if attempt_text else 0

            attempt_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO ethics_attempts
                   (attempt_id, user_id, question_id, attempt_text, word_count, submitted_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                (attempt_id, g.user_id, question_id, attempt_text, word_count),
            )
            conn.commit()
            return redirect(
                url_for("ethics_paper.ethics_question", paper_id=paper_id, question_id=question_id, submitted=1)
            )

        if action == "self_rate":
            attempt_id = request.form.get("attempt_id", "")
            self_rating = request.form.get("self_rating", "")
            self_notes = request.form.get("self_notes", "")
            model_revealed = int(request.form.get("model_revealed", 1))
            conn.execute(
                """UPDATE ethics_attempts
                   SET self_rating=?, self_notes=?, model_revealed=?, revealed_at=datetime('now')
                   WHERE attempt_id=? AND user_id=?""",
                (self_rating, self_notes, model_revealed, attempt_id, g.user_id),
            )
            conn.commit()
            return redirect(
                url_for("ethics_paper.ethics_question", paper_id=paper_id, question_id=question_id, submitted=1)
            )

        if action == "reveal":
            attempt_id = request.form.get("attempt_id", "")
            conn.execute(
                """UPDATE ethics_attempts
                   SET model_revealed=1, revealed_at=datetime('now')
                   WHERE attempt_id=? AND user_id=?""",
                (attempt_id, g.user_id),
            )
            conn.commit()
            return redirect(
                url_for("ethics_paper.ethics_question", paper_id=paper_id, question_id=question_id, submitted=1)
            )

    model_answer_row = conn.execute(
        "SELECT * FROM ethics_model_answers WHERE question_id=?", (question_id,)
    ).fetchone()
    model_answer = None
    if model_answer_row:
        model_answer = dict(model_answer_row)
        model_answer["_thinkers_cited"] = _jl(model_answer.get("thinkers_cited"))
        model_answer["_frameworks_used"] = _jl(model_answer.get("frameworks_used"))

    prev_attempt_row = conn.execute(
        """SELECT * FROM ethics_attempts
           WHERE user_id=? AND question_id=?
           ORDER BY submitted_at DESC LIMIT 1""",
        (g.user_id, question_id),
    ).fetchone()
    prev_attempt = dict(prev_attempt_row) if prev_attempt_row else None

    submitted = request.args.get("submitted") == "1"

    return render_template(
        "ethics_question.html",
        active_page="upsc_ethics",
        question=question,
        model_answer=model_answer,
        prev_attempt=prev_attempt,
        paper_id=paper_id,
        submitted=submitted,
        error=None,
    )
