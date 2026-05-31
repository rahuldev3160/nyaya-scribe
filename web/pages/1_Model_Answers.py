"""Model Answers browser — year-first navigation with diagram rendering."""
import html as html_module
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import streamlit as st

from db import get_answer, get_conn, get_questions, get_topics, jl
from diagrams import COVERED_TYPES, get_standard_diagram
from styles import apply_theme, chip
from table_renderer import render_table

st.set_page_config(page_title="Model Answers · IES 2026", layout="wide", page_icon="📖")
apply_theme()

# ── Diagram type aliases ───────────────────────────────────────────────────────
# Maps variant/long diagram_type names → canonical keys used by get_standard_diagram()

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


def _norm(dtype: str) -> str:
    d = (dtype or "").lower().strip()
    return _DTYPE_ALIASES.get(d, d)


# ── Diagram renderer ───────────────────────────────────────────────────────────

def _render_diagram(ans: dict) -> None:
    dtype_raw = ans.get("diagram_type") or ""
    dtype = _norm(dtype_raw)
    desc = ans.get("diagram_description") or ""
    code = ans.get("diagram_code")
    mode = ans.get("diagram_mode") or ""
    labels = jl(ans.get("diagram_labels") or "[]")

    if mode not in ("described", "mentioned"):
        return
    if not dtype and not desc:
        return

    # For "mentioned" diagrams with an unrecognised type and no description,
    # show a small inline chip instead of opening an empty expander.
    is_renderable = (
        dtype in COVERED_TYPES
        or dtype == "flow_chart"
        or "table" in dtype
        or "table" in dtype_raw.lower()
    )
    if mode == "mentioned" and not is_renderable and not desc:
        if dtype_raw:
            st.markdown(
                f'<div style="font-size:0.8rem;color:#9AA0A6;margin:4px 0 12px">'
                f'📊 Diagram referenced: <code style="background:rgba(255,255,255,0.07);'
                f'padding:1px 5px;border-radius:3px">{dtype_raw}</code></div>',
                unsafe_allow_html=True,
            )
        return

    with st.expander("📊 Diagram", expanded=True):
        rendered = False

        # 1. Standard matplotlib diagrams (offline, no AI)
        if dtype in COVERED_TYPES:
            try:
                fig = get_standard_diagram(dtype)
                if fig:
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)
                    rendered = True
            except Exception as e:
                st.warning(f"Diagram render error: {e}")

        # 2. Mermaid flowchart (rendered from stored code)
        elif dtype == "flow_chart":
            if code:
                mermaid_html = (
                    '<div style="background:#1C1C1E;padding:12px;border-radius:8px">'
                    f'<pre class="mermaid" style="background:transparent">{code}</pre>'
                    "</div>"
                    '<script type="module">'
                    "  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';"
                    "  mermaid.initialize({ startOnLoad: true, theme: 'dark' });"
                    "</script>"
                )
                st.components.v1.html(mermaid_html, height=420, scrolling=True)
                rendered = True
            # No else: if code is None, fall through to text fallback below

        # 3. Comparison / payoff tables (pure Python renderer)
        elif "table" in dtype or "table" in dtype_raw.lower():
            if desc:
                st.markdown(render_table(desc), unsafe_allow_html=True)
                rendered = True

        # 4. Text fallback for everything else
        if not rendered and desc:
            st.markdown(
                f'<div style="font-size:0.88rem;line-height:1.6;color:#C9CACE;padding:12px;'
                f'background:rgba(255,255,255,0.03);border-radius:8px;'
                f'border-left:3px solid rgba(138,180,248,0.3)">{desc}</div>',
                unsafe_allow_html=True,
            )

        # Explanation note shown below rendered matplotlib diagrams
        if rendered and desc and dtype in COVERED_TYPES:
            preview = desc[:600] + ("…" if len(desc) > 600 else "")
            st.markdown(
                f'<div style="font-size:0.8rem;color:#9AA0A6;margin-top:10px;padding:10px;'
                f'background:rgba(255,255,255,0.03);border-radius:6px">'
                f'<strong style="color:#8AB4F8;font-size:0.72rem;text-transform:uppercase;'
                f'letter-spacing:.05em">Diagram note </strong>{preview}</div>',
                unsafe_allow_html=True,
            )

        if labels:
            st.markdown(
                '<div style="margin-top:8px;font-size:0.75rem;color:#9AA0A6">Labels: '
                + " ".join(chip(l) for l in labels)
                + "</div>",
                unsafe_allow_html=True,
            )


# ── Answer section renderers ───────────────────────────────────────────────────

def _render_answer_sections(ans: dict) -> None:
    wc_i = ans["wc_intro"] or 0
    wc_b = ans["wc_body"] or 0
    wc_c = ans["wc_conclusion"] or 0
    total_wc = wc_i + wc_b + wc_c
    st.markdown(
        f'<div style="font-size:0.78rem;color:#9AA0A6;margin-bottom:10px">'
        f'Total: <strong style="color:#E8EAED">{total_wc} words</strong></div>',
        unsafe_allow_html=True,
    )
    _missing_html = '<em style="color:#9AA0A6">Not generated</em>'
    for label, key_tex, key_raw, wc, color, css_cls in [
        ("Introduction", "intro_tex", "intro_text", wc_i, "#8AB4F8", "answer-section"),
        ("Body", "body_tex", "body_text", wc_b, "#C084FC", "answer-section answer-section-body"),
        ("Conclusion", "conclusion_tex", "conclusion_text", wc_c, "#81C995", "answer-section answer-section-conc"),
    ]:
        tex = ans.get(key_tex)
        raw = ans.get(key_raw) or ""
        if tex:
            # LaTeX column: header as HTML, content as native markdown so KaTeX renders $...$
            st.markdown(
                f'<div style="border-left:3px solid {color};padding:4px 0 4px 12px;'
                f'margin:14px 0 6px;background:rgba(255,255,255,0.025);border-radius:0 6px 6px 0">'
                f'<span class="section-header" style="color:{color}">{label} · {wc}w</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(tex or "_Not generated_")
        else:
            st.markdown(
                f'<div class="{css_cls}">'
                f'<div class="section-header" style="color:{color}">{label} · {wc}w</div>'
                f'{raw or _missing_html}'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_rubric(q: dict) -> None:
    rubric_pts = jl(q["rubric_points"])
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
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_data_tab(ans: dict) -> None:
    data_pts = jl(ans["data_points"])
    schemes = jl(ans["schemes_referenced"])
    terms = jl(ans["key_terms_used"])

    if data_pts:
        st.markdown('<div class="section-header">Data Points</div>', unsafe_allow_html=True)
        for dp in data_pts:
            flag = dp.get("flag_verify", False)
            source = (
                f' — <em style="color:#9AA0A6">{dp["source"]}</em>'
                if dp.get("source")
                else ""
            )
            warn = (
                ' <span style="color:#FDD663;font-size:0.75rem">⚠ verify</span>'
                if flag
                else ""
            )
            bg = "rgba(253,214,99,0.04)" if flag else "transparent"
            st.markdown(
                f'<div style="padding:6px 10px;border-radius:6px;margin:3px 0;background:{bg}">'
                f"• {html_module.escape(dp.get('value', ''))}{source}{warn}</div>",
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

conn = get_conn()

with st.sidebar:
    st.markdown("## 📖 Model Answers")
    st.divider()

    paper_choice = st.selectbox(
        "Paper",
        ["ge_01", "ge_02", "ge_03", "ge_04"],
        format_func=lambda x: {
            "ge_01": "GE-01 Micro/Macro",
            "ge_02": "GE-02 Stats/Math",
            "ge_03": "GE-03 Indian Economy",
            "ge_04": "GE-04 Economic Policy",
        }.get(x, x),
    )

    topics = get_topics(conn, paper_choice)
    topic_opts = {t["topic_id"]: t["topic_name"] for t in topics}
    topic_choice = st.selectbox(
        "Topic", list(topic_opts.keys()), format_func=lambda x: topic_opts.get(x, x)
    )

    questions_all = get_questions(conn, topic_id=topic_choice, paper_id=paper_choice)
    has_ans = [q for q in questions_all if q["answer_id"]]
    no_ans = [q for q in questions_all if not q["answer_id"]]
    color = "#81C995" if not no_ans else "#FDD663"
    st.markdown(
        f'<div style="font-size:0.8rem;color:{color};margin:4px 0 8px">'
        f"✦ {len(has_ans)} answers · {len(no_ans)} pending</div>",
        unsafe_allow_html=True,
    )
    show_all = st.checkbox("Include unanswered questions", value=False)

display_qs = questions_all if show_all else has_ans
available_years = sorted(
    set(q["year"] for q in display_qs if q["year"]), reverse=True
)

# ── Topic header ───────────────────────────────────────────────────────────────
topic_name = topic_opts.get(topic_choice, topic_choice)
paper_label = paper_choice.upper().replace("_", "-")
st.markdown(
    f'<h2 style="color:#E8EAED;font-size:1.4rem;margin-bottom:2px">{topic_name}</h2>'
    f'<div style="font-size:0.8rem;color:#9AA0A6;margin-bottom:16px">'
    f"{paper_label} · {len(has_ans)} answers ready</div>",
    unsafe_allow_html=True,
)

# ── Year navigation ────────────────────────────────────────────────────────────
# key includes topic_choice so widget resets automatically when topic changes
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
    conn.close()
    st.stop()

# ── Question cards ─────────────────────────────────────────────────────────────
for qi, q in enumerate(filtered_qs):
    marks_str = f"{q['marks']}m" if q["marks"] else "?"
    wc_str = f"~{q['answer_length']}w" if q.get("answer_length") else ""
    kt = jl(q["key_terms"])

    # Question header card (always visible)
    wc_span = f'<span class="chip chip-green">{wc_str}</span>' if wc_str else ""
    st.markdown(
        f'<div class="gem-card" style="margin-bottom:4px">'
        f'<div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">'
        f'<span style="color:#9AA0A6;font-size:0.78rem;font-weight:700;min-width:24px">Q{qi+1}</span>'
        f'<span class="chip">{q.get("year", "?")}</span>'
        f'<span class="chip chip-purple">{marks_str}</span>'
        f"{wc_span}"
        f"</div>"
        f'<div style="font-size:0.95rem;line-height:1.6;color:#E8EAED">{html_module.escape(q["question_text"])}</div>'
        f"</div>",
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

    # Auto-expand when only one question is in view
    with st.expander("View Answer", expanded=(n_q == 1)):
        ans = get_answer(conn, q["question_id"])
        if not ans:
            st.warning("Answer not found in database.")
        else:
            _render_answer_sections(ans)
            _render_diagram(ans)

            tab_rub, tab_data = st.tabs(["Rubric Checklist", "Data & Schemes"])
            with tab_rub:
                _render_rubric(q)
            with tab_data:
                _render_data_tab(ans)

    st.markdown(
        '<div style="margin:8px 0 16px;border-top:1px solid rgba(255,255,255,0.06)"></div>',
        unsafe_allow_html=True,
    )

conn.close()
