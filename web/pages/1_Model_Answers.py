"""Model Answers browser."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from db import EXAM_ID, get_answer, get_conn, get_questions, get_topics, jl
from styles import apply_theme, badge, chip

st.set_page_config(page_title="Model Answers · IES 2026", layout="wide", page_icon="📖")
apply_theme()

conn = get_conn()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📖 Model Answers")
    st.divider()

    paper_choice = st.selectbox("Paper", ["ge_01", "ge_02", "ge_03", "ge_04"],
        format_func=lambda x: {"ge_01": "GE-01 Micro/Macro", "ge_02": "GE-02 Stats/Math",
                               "ge_03": "GE-03 Indian Economy", "ge_04": "GE-04 Economic Policy"}.get(x, x))

    topics = get_topics(conn, paper_choice)
    topic_opts = {t["topic_id"]: t["topic_name"] for t in topics}
    topic_choice = st.selectbox("Topic", list(topic_opts.keys()),
                                format_func=lambda x: topic_opts.get(x, x))

    questions = get_questions(conn, topic_id=topic_choice, paper_id=paper_choice)
    has_ans = [q for q in questions if q["answer_id"]]
    no_ans  = [q for q in questions if not q["answer_id"]]

    ans_color = "#81C995" if len(no_ans) == 0 else "#FDD663"
    st.markdown(
        f'<div style="font-size:0.8rem;color:{ans_color};margin:4px 0 8px">'
        f'✦ {len(has_ans)} answers ready · {len(no_ans)} pending</div>',
        unsafe_allow_html=True
    )

    show_all = st.checkbox("Include questions without answers", value=False)
    display_qs = has_ans if not show_all else questions

    years = sorted(set(q["year"] for q in display_qs if q["year"]), reverse=True)
    year_filter = st.multiselect("Filter by year", years, default=[])
    if year_filter:
        display_qs = [q for q in display_qs if q["year"] in year_filter]

    if not display_qs:
        st.warning("No questions match the selected filters.")
        st.stop()

    q_labels = {
        q["question_id"]: f"[{q['year']}] {q['marks']}m — {q['question_text'][:52]}…"
        for q in display_qs
    }
    q_choice = st.selectbox("Question", list(q_labels.keys()),
                             format_func=lambda x: q_labels.get(x, x))

# ── Main area ─────────────────────────────────────────────────────────────────
selected_q = next((q for q in display_qs if q["question_id"] == q_choice), None)
if not selected_q:
    st.info("Select a question from the sidebar.")
    conn.close()
    st.stop()

# Question card
marks_str = f"{selected_q['marks']} marks" if selected_q["marks"] else "marks unknown"
wc_str    = f"~{selected_q['answer_length']} words" if selected_q["answer_length"] else ""
year_tag_color = "#8AB4F8"

st.markdown(f"""<div class="gem-card">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
        <div style="flex:1">
            <div style="margin-bottom:10px">
                <span class="chip" style="margin-right:6px">{selected_q['year']}</span>
                <span class="chip chip-purple">{marks_str}</span>
                {'<span class="chip chip-green">' + wc_str + '</span>' if wc_str else ''}
            </div>
            <div style="font-size:1rem;line-height:1.6;color:#E8EAED">{selected_q['question_text']}</div>
        </div>
    </div>
</div>""", unsafe_allow_html=True)

# Key terms
key_terms = jl(selected_q["key_terms"])
if key_terms:
    chips_html = " ".join(chip(k) for k in key_terms)
    st.markdown(
        f'<div style="margin:6px 0 12px"><span style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em;margin-right:8px">Key Terms</span>{chips_html}</div>',
        unsafe_allow_html=True
    )

# No answer yet
if not selected_q["answer_id"]:
    st.markdown("""<div class="gem-card" style="border-color:rgba(253,214,99,0.3);background:rgba(253,214,99,0.04)">
        <span style="color:#FDD663">⏳ Answer not yet generated for this question.</span>
    </div>""", unsafe_allow_html=True)
    conn.close()
    st.stop()

ans = get_answer(conn, q_choice)
if not ans:
    st.warning("Answer not found.")
    conn.close()
    st.stop()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_ans, tab_rubric, tab_data = st.tabs(["Answer", "Rubric Checklist", "Data & Schemes"])

with tab_ans:
    wc_i = ans["wc_intro"] or 0
    wc_b = ans["wc_body"]  or 0
    wc_c = ans["wc_conclusion"] or 0
    total_wc = wc_i + wc_b + wc_c

    st.markdown(
        f'<div style="font-size:0.78rem;color:#9AA0A6;margin-bottom:12px">Total: <strong style="color:#E8EAED">{total_wc} words</strong></div>',
        unsafe_allow_html=True
    )

    # Intro
    st.markdown(f"""<div class="answer-section">
        <div class="section-header" style="color:#8AB4F8">Introduction · {wc_i}w</div>
        {ans['intro_text'] or '<em style="color:#9AA0A6">Not generated</em>'}
    </div>""", unsafe_allow_html=True)

    # Body
    st.markdown(f"""<div class="answer-section answer-section-body">
        <div class="section-header" style="color:#C084FC">Body · {wc_b}w</div>
        {ans['body_text'] or '<em style="color:#9AA0A6">Not generated</em>'}
    </div>""", unsafe_allow_html=True)

    # Conclusion
    st.markdown(f"""<div class="answer-section answer-section-conc">
        <div class="section-header" style="color:#81C995">Conclusion · {wc_c}w</div>
        {ans['conclusion_text'] or '<em style="color:#9AA0A6">Not generated</em>'}
    </div>""", unsafe_allow_html=True)

    # Diagram
    if ans["diagram_mode"] == "described" and ans["diagram_description"]:
        with st.expander("📊 Diagram Details"):
            if ans["diagram_type"]:
                st.markdown(f"**Type:** `{ans['diagram_type']}`")
            st.markdown(ans["diagram_description"])
            labels = jl(ans["diagram_labels"])
            if labels:
                st.markdown("**Labels:** " + "  ".join(chip(l) for l in labels), unsafe_allow_html=True)
    elif ans["diagram_mode"] == "mentioned":
        st.markdown(
            f'<div style="font-size:0.8rem;color:#9AA0A6;margin-top:8px">📊 Diagram mentioned: {ans["diagram_type"] or ""}</div>',
            unsafe_allow_html=True
        )

with tab_rubric:
    rubric_pts = jl(selected_q["rubric_points"])
    if rubric_pts:
        section_colors = {"intro": "#8AB4F8", "body": "#C084FC", "conclusion": "#81C995"}
        for rp in rubric_pts:
            section = rp.get("section_hint", "body").lower()
            color = section_colors.get(section, "#9AA0A6")
            weight = rp.get("weight", 1)
            category = rp.get("category", "")
            point = rp.get("point", "")
            st.markdown(
                f'<div class="gem-card-sm" style="border-left:3px solid {color}">'
                f'<span style="font-size:0.68rem;color:{color};text-transform:uppercase;font-weight:700">[{section}]</span>'
                f' <span style="font-size:0.88rem">{point}</span>'
                f'<br><span style="font-size:0.7rem;color:#9AA0A6">{category} · weight {weight}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.info("No rubric available for this question.")

with tab_data:
    data_pts = jl(ans["data_points"])
    schemes  = jl(ans["schemes_referenced"])
    terms    = jl(ans["key_terms_used"])

    if data_pts:
        st.markdown('<div class="section-header">Data Points</div>', unsafe_allow_html=True)
        for dp in data_pts:
            flag = dp.get("flag_verify", False)
            source = f' — <em style="color:#9AA0A6">{dp["source"]}</em>' if dp.get("source") else ""
            warn = ' <span style="color:#FDD663;font-size:0.75rem">⚠ verify</span>' if flag else ""
            bg = "rgba(253,214,99,0.04)" if flag else "transparent"
            st.markdown(
                f'<div style="padding:6px 10px;border-radius:6px;margin:3px 0;background:{bg}">'
                f'• {dp.get("value","")}{source}{warn}</div>',
                unsafe_allow_html=True
            )

    if schemes:
        st.markdown('<div class="section-header" style="margin-top:12px">Schemes & Committees</div>', unsafe_allow_html=True)
        for s in schemes:
            st.markdown(f'<div style="padding:4px 10px;font-size:0.88rem">• {s}</div>', unsafe_allow_html=True)

    if terms:
        st.markdown('<div class="section-header" style="margin-top:12px">Key Terms Used</div>', unsafe_allow_html=True)
        chips_html = " ".join(chip(t) for t in terms)
        st.markdown(f'<div>{chips_html}</div>', unsafe_allow_html=True)

    if not any([data_pts, schemes, terms]):
        st.info("No data points or schemes recorded for this answer.")

conn.close()
