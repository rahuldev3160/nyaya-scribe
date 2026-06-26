"""Essay Paper blueprint — /upsc/essay"""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, redirect, render_template, request
from auth import login_required

essay_bp = Blueprint("essay", __name__)


def _jl(s) -> list:
    if not s:
        return []
    try:
        r = json.loads(s)
        return r if isinstance(r, list) else []
    except Exception:
        return []


def _jd(s) -> dict:
    if not s:
        return {}
    try:
        r = json.loads(s)
        return r if isinstance(r, dict) else {}
    except Exception:
        return {}


def _parse_dimensions(json_str: str) -> list[dict]:
    raw = json.loads(json_str) if json_str else []
    if not isinstance(raw, list):
        return []
    return raw


@essay_bp.route("/upsc/essay")
@login_required
def essay_landing():
    if not g.upsc_gs_conn:
        return render_template(
            "essay_landing.html",
            active_page="upsc_essay",
            error="Essay database not found.",
            essay_rows=[],
            theme_rows=[],
            active_tab="practice",
            filters={},
        )

    active_tab = request.args.get("tab", "practice")
    if active_tab not in ("practice", "pyq", "pattern"):
        active_tab = "practice"

    sel_year = request.args.get("year")
    if sel_year:
        try:
            sel_year = int(sel_year)
        except (ValueError, TypeError):
            sel_year = None

    sel_section = request.args.get("section")
    sel_theme = request.args.get("theme")
    hot_only = request.args.get("hot") == "1"

    filters = {
        "tab": active_tab,
        "year": sel_year,
        "section": sel_section,
        "theme": sel_theme,
        "hot": hot_only,
    }

    where_clauses = []
    params = []

    if active_tab == "practice":
        where_clauses.append("q.content_type = 'practice'")
        where_clauses.append("q.generation_year = 2026")
    elif active_tab == "pyq":
        where_clauses.append("q.content_type = 'pyq'")
        if sel_year:
            where_clauses.append("q.year_appeared = ?")
            params.append(sel_year)

    if sel_section:
        where_clauses.append("q.section = ?")
        params.append(sel_section)

    if sel_theme:
        where_clauses.append("q.theme_tag = ?")
        params.append(sel_theme)

    if hot_only:
        where_clauses.append("q.is_high_probability = 1")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    raw_rows = g.upsc_gs_conn.execute(
        f"""SELECT q.essay_id, q.prompt, q.section, q.theme_tag, q.hook_type_id,
                   q.framework_id, q.word_limit, q.marks, q.year_appeared,
                   q.content_type, q.generation_year, q.difficulty,
                   q.is_high_probability, q.backing_note,
                   COUNT(ma.answer_id) AS answer_count
            FROM essay_questions q
            LEFT JOIN essay_model_answers ma ON q.essay_id = ma.essay_id
            {where_sql}
            GROUP BY q.essay_id
            ORDER BY q.year_appeared DESC, q.section, q.essay_id""",
        params,
    ).fetchall()

    essay_rows = [dict(r) for r in raw_rows]

    theme_rows = g.upsc_gs_conn.execute(
        """SELECT theme_tag, theme_label, frequency_count, typical_section,
                  year_appearances, example_questions, fy26_ca_hook, trend,
                  probability_2026
           FROM essay_theme_analysis
           ORDER BY frequency_count DESC"""
    ).fetchall()
    theme_rows = [dict(r) for r in theme_rows]

    return render_template(
        "essay_landing.html",
        active_page="upsc_essay",
        essay_rows=essay_rows,
        theme_rows=theme_rows,
        active_tab=active_tab,
        filters=filters,
        error=None,
    )


@essay_bp.route("/upsc/essay/framework-guide")
@login_required
def essay_framework():
    return render_template(
        "essay_framework.html",
        active_page="upsc_essay",
    )


@essay_bp.route("/upsc/essay/pyq")
@login_required
def essay_pyq():
    if not g.upsc_gs_conn:
        return render_template(
            "essay_landing.html",
            active_page="upsc_essay",
            error="Essay database not found.",
            essay_rows=[],
            theme_rows=[],
            active_tab="pyq",
            filters={},
        )

    sel_year = request.args.get("year")
    if sel_year:
        try:
            sel_year = int(sel_year)
        except (ValueError, TypeError):
            sel_year = None

    params = ["pyq"]
    year_clause = ""
    if sel_year:
        year_clause = "AND q.year_appeared = ?"
        params.append(sel_year)

    raw_rows = g.upsc_gs_conn.execute(
        f"""SELECT q.essay_id, q.prompt, q.section, q.theme_tag, q.hook_type_id,
                   q.framework_id, q.word_limit, q.marks, q.year_appeared,
                   q.content_type, q.generation_year, q.difficulty,
                   q.is_high_probability, q.backing_note,
                   COUNT(ma.answer_id) AS answer_count
            FROM essay_questions q
            LEFT JOIN essay_model_answers ma ON q.essay_id = ma.essay_id
            WHERE q.content_type = ?
            {year_clause}
            GROUP BY q.essay_id
            ORDER BY q.year_appeared DESC, q.section, q.essay_id""",
        params,
    ).fetchall()

    essay_rows = [dict(r) for r in raw_rows]

    return render_template(
        "essay_landing.html",
        active_page="upsc_essay",
        essay_rows=essay_rows,
        theme_rows=[],
        active_tab="pyq",
        filters={"tab": "pyq", "year": sel_year},
        error=None,
    )


@essay_bp.route("/upsc/essay/<essay_id>")
@login_required
def essay_detail(essay_id: str):
    if not g.upsc_gs_conn:
        return render_template(
            "essay_detail.html",
            active_page="upsc_essay",
            essay=None,
            answer=None,
            dimension_entries=[],
            error="Essay database not found.",
        )

    essay_row = g.upsc_gs_conn.execute(
        """SELECT essay_id, prompt, section, theme_tag, hook_type_id, framework_id,
                  word_limit, marks, year_appeared, content_type, generation_year,
                  difficulty, is_high_probability, backing_note
           FROM essay_questions
           WHERE essay_id = ?""",
        (essay_id,),
    ).fetchone()

    if not essay_row:
        return render_template(
            "essay_detail.html",
            active_page="upsc_essay",
            essay=None,
            answer=None,
            dimension_entries=[],
            error="Essay question not found.",
        )

    essay = dict(essay_row)

    answer_row = g.upsc_gs_conn.execute(
        """SELECT answer_id, essay_id, intro_hook, intro_hook_type, intro_context,
                  intro_thesis, intro_signpost, body_dimensions_json, body_challenges,
                  body_solutions, body_synthesis_para, concl_synthesis,
                  concl_way_forward, concl_philosophical, concl_closing_line,
                  total_word_count
           FROM essay_model_answers
           WHERE essay_id = ?""",
        (essay_id,),
    ).fetchone()

    answer = dict(answer_row) if answer_row else None

    dimension_entries = []
    if answer and answer.get("body_dimensions_json"):
        try:
            raw = json.loads(answer["body_dimensions_json"])
            if isinstance(raw, list):
                dimension_entries = raw
        except Exception:
            dimension_entries = []

    submitted = request.args.get("submitted") == "1"

    return render_template(
        "essay_detail.html",
        active_page="upsc_essay",
        essay=essay,
        answer=answer,
        dimension_entries=dimension_entries,
        submitted=submitted,
        error=None,
    )


@essay_bp.route("/upsc/essay/<essay_id>/submit", methods=["POST"])
@login_required
def essay_submit(essay_id: str):
    intro_text = request.form.get("intro_text", "").strip()
    body_text = request.form.get("body_text", "").strip()
    conclusion_text = request.form.get("conclusion_text", "").strip()
    full_text = request.form.get("full_text", "").strip()

    if not full_text:
        full_text = "\n\n".join(p for p in [intro_text, body_text, conclusion_text] if p)

    word_count_raw = request.form.get("word_count", "").strip()
    try:
        word_count = int(word_count_raw) if word_count_raw else len(full_text.split())
    except ValueError:
        word_count = len(full_text.split())

    attempt_id = str(uuid.uuid4())
    submitted_at = datetime.now(timezone.utc).isoformat()

    g.upsc_gs_conn.execute(
        """INSERT INTO essay_attempts
               (attempt_id, user_id, essay_id, intro_text, body_text,
                conclusion_text, full_text, word_count, submitted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            attempt_id,
            g.user_id,
            essay_id,
            intro_text,
            body_text,
            conclusion_text,
            full_text,
            word_count,
            submitted_at,
        ),
    )
    g.upsc_gs_conn.commit()

    return redirect(f"/upsc/essay/{essay_id}?submitted=1")
