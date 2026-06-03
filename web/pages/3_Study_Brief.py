"""Study Brief — full topic context package for focused study."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from db import get_conn, get_topics, get_study_brief, log_event, EXAM_ID
from styles import apply_theme, chip

st.set_page_config(page_title="Study Brief · IES 2026", layout="wide", page_icon="🗂️")
apply_theme()

@st.cache_resource
def _get_conn():
    return get_conn()

conn = _get_conn()

st.markdown("## 🗂️ Study Brief")
st.markdown(
    '<div style="color:#9AA0A6;font-size:0.88rem;margin-bottom:1.2rem">'
    'Pick a topic to get key terms, top questions, rubric points, and a copy-paste study prompt.</div>',
    unsafe_allow_html=True,
)

# ── Selectors ──────────────────────────────────────────────────────────────────
col_p, col_t = st.columns([1, 2])
with col_p:
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
with col_t:
    topics = get_topics(conn, paper_choice)
    topic_opts = {t["topic_id"]: t["topic_name"] for t in topics}
    topic_choice = st.selectbox(
        "Topic", list(topic_opts.keys()),
        format_func=lambda x: topic_opts.get(x, x),
    )

brief = get_study_brief(conn, topic_choice)
if not brief["topic"]:
    st.warning("Topic not found.")
    st.stop()

t  = brief["topic"]
bs = brief["base_score"]
score     = bs.get("base_priority_score", 0) or 0
pyq_count = bs.get("pyq_count", 0) or 0
years     = bs.get("distinct_years", 0) or 0

log_event(conn, "topic_opened", entity_type="topic", entity_id=topic_choice, exam_id=EXAM_ID,
          payload={"paper_id": paper_choice, "priority_score": round(score, 4)})

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="gem-card-accent">'
    f'<div style="font-size:1.25rem;font-weight:700;color:#E8EAED">{t.get("topic_name","")}</div>'
    f'<div style="font-size:0.82rem;color:#9AA0A6;margin-top:4px">'
    f'{paper_choice.upper().replace("_","-")} · Syllabus weight: {t.get("syllabus_weight","?")}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Priority metrics ───────────────────────────────────────────────────────────
m1, m2, m3 = st.columns(3)
for col, val, label, color in [
    (m1, f"{score:.3f}", "Priority Score", "#8AB4F8"),
    (m2, str(pyq_count), "PYQs",           "#C084FC"),
    (m3, str(years),     "Years Asked",    "#81C995"),
]:
    with col:
        st.markdown(
            f'<div class="gem-card" style="text-align:center;border-color:{color}33">'
            f'<div style="font-size:1.8rem;font-weight:700;color:{color}">{val}</div>'
            f'<div style="font-size:0.7rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">{label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Metadata columns (subtopics, key terms, diagrams, instructions) ────────────
left, right = st.columns([3, 2])

with left:
    if brief["subtopics"]:
        st.markdown("**Syllabus Coverage**")
        for s in brief["subtopics"]:
            st.markdown(f"- {s}")
        st.markdown("")

    if brief["key_terms"]:
        st.markdown("**Key Terms to Master**")
        chips_html = " ".join(chip(k) for k in brief["key_terms"])
        st.markdown(f'<div style="line-height:2">{chips_html}</div>', unsafe_allow_html=True)
        st.markdown("")

    if brief["diagrams"]:
        st.markdown("**Frequently Asked Diagrams**")
        for dtype, cnt in brief["diagrams"].items():
            st.markdown(
                f'<span class="chip chip-purple">📊 {dtype}</span>'
                f'<span style="color:#9AA0A6;font-size:0.75rem;margin-left:6px">{cnt}× asked</span>',
                unsafe_allow_html=True,
            )
        st.markdown("")

with right:
    st.markdown(
        '<div class="gem-card" style="border-left:3px solid #C084FC">'
        '<div class="section-header" style="color:#C084FC">How to Study This Topic</div>'
        '<ol style="font-size:0.85rem;line-height:2;color:#E8EAED;margin:0;padding-left:18px">'
        '<li>Learn every key term on the left</li>'
        '<li>For each question, check the rubric — those are your marks</li>'
        '<li>Practice diagrams: sketch them, label axes</li>'
        '<li>Focus on 2025 + 2024 patterns — exam repeats themes</li>'
        '<li>Add data points and government schemes in your answers</li>'
        '</ol>'
        '</div>',
        unsafe_allow_html=True,
    )

st.divider()

# ── Questions — one expander per question ──────────────────────────────────────
st.markdown(f'<div class="section-header">Top {len(brief["questions"])} Questions (by marks + recency)</div>', unsafe_allow_html=True)

for i, q in enumerate(brief["questions"], 1):
    marks_str = f"{q['marks']}m" if q["marks"] else "?m"
    wc_str    = f"~{q['answer_length']}w" if q["answer_length"] else ""
    title     = f"Q{i}. [{q['year']}] {marks_str}  —  {q['question_text'][:65]}…"

    with st.expander(title, expanded=(i == 1)):
        st.info(q["question_text"])

        tag_html = ""
        if wc_str:
            tag_html += f'<span class="chip chip-green">{wc_str}</span> '
        if q["diagram_expected"]:
            tag_html += f'<span class="chip chip-purple">📊 {q["diagram_type"] or "diagram"}</span>'
        if tag_html:
            st.markdown(tag_html, unsafe_allow_html=True)

        if q["rubric_points"]:
            st.markdown("**Rubric checklist:**")
            for rp in q["rubric_points"]:
                section = rp.get("section_hint", "body").upper()
                st.markdown(f"- `[{section}]` {rp.get('point', '')}")

st.divider()

# ── Copy-paste plain text ──────────────────────────────────────────────────────
with st.expander("📋 Copy plain text — paste into Claude.ai for deep study"):
    lines = [
        f"IES 2026 STUDY CONTEXT: {t.get('topic_name','')}",
        f"Paper: {paper_choice.upper().replace('_','-')} | Priority: {score:.3f} | PYQs: {pyq_count} across {years} years",
        "",
    ]
    if brief["subtopics"]:
        lines += ["SYLLABUS:"] + [f"  • {s}" for s in brief["subtopics"]] + [""]
    if brief["key_terms"]:
        lines += ["KEY TERMS:"] + [f"  • {k}" for k in brief["key_terms"]] + [""]
    if brief["diagrams"]:
        lines += ["DIAGRAMS:"] + [f"  • {d} ({c}x)" for d, c in brief["diagrams"].items()] + [""]
    lines.append(f"TOP {len(brief['questions'])} QUESTIONS:")
    lines.append("-" * 60)
    for i, q in enumerate(brief["questions"], 1):
        m  = f"{q['marks']}m" if q["marks"] else "?m"
        wc = f"/{q['answer_length']}w" if q["answer_length"] else ""
        lines += ["", f"Q{i}. [{q['year']} | {m}{wc}]", q["question_text"]]
        if q["rubric_points"]:
            lines.append(f"   Rubric ({len(q['rubric_points'])} points):")
            for rp in q["rubric_points"]:
                lines.append(f"   [{rp.get('section_hint','')}] {rp.get('point','')}")
        if q["diagram_expected"]:
            lines.append(f"   Diagram: {q['diagram_type'] or 'relevant diagram'}")
    st.text_area("", value="\n".join(lines), height=300)
