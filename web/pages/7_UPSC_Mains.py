"""UPSC Economics Optional — Model Answers browser."""
import html as html_module
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from styles import apply_theme, chip

st.set_page_config(page_title="UPSC Eco Optional · Model Answers", layout="wide", page_icon="🎓")
apply_theme()

# ── Constants ─────────────────────────────────────────────────────────────────
_DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc.db"
_EXAM_ID = "upsc_eco_opt"

_PAPER_LABELS = {
    "upsc_p1": "Paper I — Theory",
    "upsc_p2": "Paper II — Indian Economy",
}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _jl(s) -> list:
    if not s:
        return []
    try:
        result = json.loads(s)
        return result if isinstance(result, list) else []
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
           LEFT JOIN question_rubrics r
               ON q.question_id=r.question_id AND q.exam_id=r.exam_id
           LEFT JOIN model_answers ma
               ON q.question_id=ma.question_id AND q.exam_id=ma.exam_id
           WHERE q.exam_id=? AND q.topic_id=? AND q.paper_id=?
           ORDER BY q.marks DESC NULLS LAST, q.year DESC""",
        (_EXAM_ID, topic_id, paper_id),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_answer(conn, question_id: str):
    row = conn.execute(
        """SELECT ma.*
           FROM model_answers ma
           WHERE ma.question_id=? AND ma.exam_id=?""",
        (question_id, _EXAM_ID),
    ).fetchone()
    return dict(row) if row else None


# ── Renderers ─────────────────────────────────────────────────────────────────

def _render_answer_sections(ans: dict) -> None:
    wc_i = ans.get("wc_intro") or 0
    wc_b = ans.get("wc_body") or 0
    wc_c = ans.get("wc_conclusion") or 0
    total_wc = wc_i + wc_b + wc_c
    st.markdown(
        f'<div style="font-size:0.78rem;color:#9AA0A6;margin-bottom:10px">'
        f'Total: <strong style="color:#E8EAED">{total_wc} words</strong></div>',
        unsafe_allow_html=True,
    )

    for label, key, wc, color in [
        ("Introduction", "intro_text", wc_i, "#8AB4F8"),
        ("Body", "body_text", wc_b, "#C084FC"),
        ("Conclusion", "conclusion_text", wc_c, "#81C995"),
    ]:
        text = (ans.get(key) or "").strip()
        st.markdown(
            f'<div style="border-left:3px solid {color};padding:4px 0 4px 12px;'
            f'margin:14px 0 6px;background:rgba(255,255,255,0.025);border-radius:0 6px 6px 0">'
            f'<span style="color:{color};font-size:0.8rem;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:.06em">{label} · {wc}w</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if text:
            st.markdown(text)
        else:
            st.markdown('<em style="color:#9AA0A6">Not generated</em>', unsafe_allow_html=True)


def _render_rubric(rubric_points_raw) -> None:
    rubric_pts = _jl(rubric_points_raw)
    if not rubric_pts:
        st.info("No rubric available for this question.")
        return
    section_colors = {"intro": "#8AB4F8", "body": "#C084FC", "conclusion": "#81C995"}
    for rp in rubric_pts:
        section = rp.get("section_hint", "body").lower()
        color = section_colors.get(section, "#9AA0A6")
        st.markdown(
            f'<div class="gem-card-sm" style="border-left:3px solid {color}">'
            f'<span style="font-size:0.68rem;color:{color};text-transform:uppercase;'
            f'font-weight:700">[{section}]</span>'
            f' <span style="font-size:0.88rem">{html_module.escape(rp.get("point", ""))}</span>'
            f'<br><span style="font-size:0.7rem;color:#9AA0A6">'
            f'{rp.get("category", "")} · weight {rp.get("weight", 1)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_data_tab(ans: dict) -> None:
    data_pts = _jl(ans.get("data_points"))
    schemes = _jl(ans.get("schemes_referenced"))
    terms = _jl(ans.get("key_terms_used"))

    if data_pts:
        st.markdown('<div class="section-header">Data Points</div>', unsafe_allow_html=True)
        for dp in data_pts:
            flag = dp.get("flag_verify", False)
            source = (
                f' — <em style="color:#9AA0A6">{dp["source"]}</em>'
                if dp.get("source") else ""
            )
            warn = ' <span style="color:#FDD663;font-size:0.75rem">⚠ verify</span>' if flag else ""
            bg = "rgba(253,214,99,0.04)" if flag else "transparent"
            st.markdown(
                f'<div style="padding:6px 10px;border-radius:6px;margin:3px 0;background:{bg}">'
                f'• {html_module.escape(dp.get("value", ""))}{source}{warn}</div>',
                unsafe_allow_html=True,
            )

    if schemes:
        st.markdown(
            '<div class="section-header" style="margin-top:12px">Schemes & Committees</div>',
            unsafe_allow_html=True,
        )
        for s in schemes:
            st.markdown(
                f'<div style="padding:4px 10px;font-size:0.88rem">• {html_module.escape(s)}</div>',
                unsafe_allow_html=True,
            )

    if terms:
        st.markdown(
            '<div class="section-header" style="margin-top:12px">Key Terms Used</div>',
            unsafe_allow_html=True,
        )
        st.markdown(" ".join(chip(t) for t in terms), unsafe_allow_html=True)

    if not any([data_pts, schemes, terms]):
        st.info("No data points or schemes recorded for this answer.")


# ── Page layout ────────────────────────────────────────────────────────────────

if not _DB_PATH.exists():
    st.error(
        "**UPSC database not found.**  \n"
        "`data/upsc.db` is missing — the app should have copied it from `upsc_seed.db` on startup.  \n"
        "Please reload the home page first or contact support."
    )
    st.stop()

conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")

with st.sidebar:
    st.markdown("## 🎓 UPSC Eco Optional")
    st.divider()

    paper_choice = st.selectbox(
        "Paper",
        list(_PAPER_LABELS.keys()),
        format_func=lambda x: _PAPER_LABELS.get(x, x),
    )

    topics = _get_topics(conn, paper_choice)
    topic_opts = {t["topic_id"]: t["topic_name"] for t in topics}
    topic_choice = st.selectbox(
        "Topic",
        list(topic_opts.keys()),
        format_func=lambda x: topic_opts.get(x, x),
    )

    questions_all = _get_questions(conn, topic_id=topic_choice, paper_id=paper_choice)
    has_ans = [q for q in questions_all if q["answer_id"]]
    no_ans  = [q for q in questions_all if not q["answer_id"]]
    color = "#81C995" if not no_ans else "#FDD663"
    st.markdown(
        f'<div style="font-size:0.8rem;color:{color};margin:4px 0 8px">'
        f'✦ {len(has_ans)} answers · {len(no_ans)} pending</div>',
        unsafe_allow_html=True,
    )
    show_all = st.checkbox("Include unanswered questions", value=False)

display_qs = questions_all if show_all else has_ans
available_years = sorted(set(q["year"] for q in display_qs if q["year"]), reverse=True)

# ── Topic header ───────────────────────────────────────────────────────────────
topic_name = topic_opts.get(topic_choice, topic_choice)
paper_label = _PAPER_LABELS.get(paper_choice, paper_choice)
st.markdown(
    f'<h2 style="color:#E8EAED;font-size:1.4rem;margin-bottom:2px">{topic_name}</h2>'
    f'<div style="font-size:0.8rem;color:#9AA0A6;margin-bottom:16px">'
    f'{paper_label} · {len(has_ans)} answers ready</div>',
    unsafe_allow_html=True,
)

# ── Year navigation ────────────────────────────────────────────────────────────
year_options = [None] + available_years
sel_year = st.radio(
    "Year",
    year_options,
    format_func=lambda y: "All" if y is None else str(y),
    horizontal=True,
    label_visibility="collapsed",
    key=f"yr_{topic_choice}",
)

st.markdown(
    '<div style="margin:8px 0;border-top:1px solid rgba(255,255,255,0.08)"></div>',
    unsafe_allow_html=True,
)

# ── Filter by selected year ────────────────────────────────────────────────────
if sel_year:
    filtered_qs = [q for q in display_qs if q["year"] == sel_year]
    year_label = str(sel_year)
else:
    filtered_qs = display_qs
    year_label = "All Years"

n_q = len(filtered_qs)
st.markdown(
    f'<div style="font-size:0.82rem;color:#9AA0A6;margin-bottom:14px">'
    f'📅 {year_label} · {n_q} question{"s" if n_q != 1 else ""}</div>',
    unsafe_allow_html=True,
)

if not filtered_qs:
    st.info("No questions match the current selection.")
    st.stop()

# ── Question cards ─────────────────────────────────────────────────────────────
for qi, q in enumerate(filtered_qs):
    marks_str = f"{q['marks']}m" if q["marks"] else "?"
    wc_str = f"~{q['answer_length']}w" if q.get("answer_length") else ""
    kt = _jl(q.get("key_terms"))

    wc_span = f'<span class="chip chip-green">{wc_str}</span>' if wc_str else ""
    st.markdown(
        f'<div class="gem-card" style="margin-bottom:4px">'
        f'<div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">'
        f'<span style="color:#9AA0A6;font-size:0.78rem;font-weight:700;min-width:24px">Q{qi+1}</span>'
        f'<span class="chip">{q.get("year", "?")}</span>'
        f'<span class="chip chip-purple">{marks_str}</span>'
        f'{wc_span}'
        f'</div>'
        f'<div style="font-size:0.95rem;line-height:1.6;color:#E8EAED">'
        f'{html_module.escape(q["question_text"])}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if kt:
        chips_html = " ".join(chip(k) for k in kt[:8])
        st.markdown(
            f'<div style="margin:-2px 0 8px"><span style="font-size:0.72rem;'
            f'color:#9AA0A6;margin-right:6px">Key Terms:</span>{chips_html}</div>',
            unsafe_allow_html=True,
        )

    if not q["answer_id"]:
        st.markdown(
            '<div style="color:#FDD663;font-size:0.8rem;padding:4px 0 16px">⏳ Answer not yet generated.</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="margin:8px 0 16px;border-top:1px solid rgba(255,255,255,0.06)"></div>',
            unsafe_allow_html=True,
        )
        continue

    with st.expander("View Answer", expanded=(n_q == 1)):
        ans = _get_answer(conn, q["question_id"])
        if not ans:
            st.warning("Answer not found in database.")
        else:
            _render_answer_sections(ans)

            tab_rub, tab_data = st.tabs(["Rubric Checklist", "Data & Schemes"])
            with tab_rub:
                _render_rubric(q.get("rubric_points"))
            with tab_data:
                _render_data_tab(ans)

    st.markdown(
        '<div style="margin:8px 0 16px;border-top:1px solid rgba(255,255,255,0.06)"></div>',
        unsafe_allow_html=True,
    )

conn.close()
