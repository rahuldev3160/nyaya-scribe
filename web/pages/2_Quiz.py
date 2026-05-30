"""Descriptive Quiz — write an answer, get AI evaluation."""
import json
import random
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic
import streamlit as st

from db import EXAM_ID, USER_ID, get_answer, get_conn, get_questions, get_topics, jl, load_api_key, set_topic_state
from styles import apply_theme, badge, chip, score_card_html

st.set_page_config(page_title="Quiz · IES 2026", layout="wide", page_icon="✍️")
apply_theme()

conn = get_conn()

EVAL_SYSTEM = """You are an IES (Indian Economic Service) exam evaluator.
Grade the student's answer against the rubric. Be concise but specific.
Return ONLY valid JSON, no markdown:
{
  "score_intro": <0-10>,
  "score_body": <0-10>,
  "score_conclusion": <0-10>,
  "score_overall": <0-10>,
  "feedback_intro": "...",
  "feedback_body": "...",
  "feedback_conclusion": "...",
  "missing_points": ["..."],
  "strong_points": ["..."],
  "suggested_improvements": "..."
}"""

WC_GUIDE = {
    (0, 7): (25, 55, 20), (7, 12): (35, 90, 25),
    (12, 18): (50, 140, 30), (18, 25): (60, 190, 40), (25, 999): (80, 340, 80),
}

def get_wc(marks):
    if not marks:
        return WC_GUIDE[(7, 12)]
    for (lo, hi), g in WC_GUIDE.items():
        if lo <= marks < hi:
            return g
    return WC_GUIDE[(7, 12)]


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ✍️ Quiz")
    st.divider()
    mode = st.radio("Pick question by", ["Topic", "Random"], horizontal=True)

    if mode == "Topic":
        paper_choice = st.selectbox("Paper", ["ge_01", "ge_02", "ge_03", "ge_04"],
            format_func=lambda x: {"ge_01": "GE-01", "ge_02": "GE-02",
                                   "ge_03": "GE-03", "ge_04": "GE-04"}.get(x, x))
        topics = get_topics(conn, paper_choice)
        topic_opts = {t["topic_id"]: t["topic_name"] for t in topics}
        topic_choice = st.selectbox("Topic", list(topic_opts.keys()),
                                    format_func=lambda x: topic_opts.get(x, x))
        questions = get_questions(conn, topic_id=topic_choice)
    else:
        questions = [q for q in get_questions(conn) if q["answer_id"]]

    if not questions:
        st.warning("No questions found.")
        st.stop()

    if mode == "Random":
        if st.button("🎲 Random question", use_container_width=True):
            st.session_state["quiz_qid"] = random.choice(questions)["question_id"]
        selected_qid = st.session_state.get("quiz_qid", questions[0]["question_id"])
    else:
        q_labels = {
            q["question_id"]: f"[{q['year']}] {q['marks']}m — {q['question_text'][:50]}…"
            for q in questions
        }
        selected_qid = st.selectbox("Question", list(q_labels.keys()),
                                    format_func=lambda x: q_labels.get(x, x))

    show_model = st.checkbox("Show model answer after evaluation", value=True)
    st.divider()
    st.markdown('<div style="font-size:0.75rem;color:#9AA0A6">Your answer is evaluated by Claude Sonnet against the rubric. Scores are out of 10.</div>', unsafe_allow_html=True)

# ── Question ───────────────────────────────────────────────────────────────────
selected_q = next((q for q in questions if q["question_id"] == selected_qid), questions[0])
marks = selected_q["marks"]
wc = get_wc(marks)
marks_str = f"{marks} marks" if marks else "marks unknown"
wc_hint = f"intro ~{wc[0]}w · body ~{wc[1]}w · conclusion ~{wc[2]}w"
if selected_q["answer_length"]:
    wc_hint += f" · total ~{selected_q['answer_length']}w"

st.markdown(f"""<div class="gem-card-accent">
    <div style="margin-bottom:10px">
        <span class="chip">{selected_q['year']}</span>
        <span class="chip chip-purple" style="margin-left:6px">{marks_str}</span>
    </div>
    <div style="font-size:1.05rem;line-height:1.65;color:#E8EAED">{selected_q['question_text']}</div>
    <div style="margin-top:12px">
        <span style="font-size:0.72rem;color:#9AA0A6;margin-right:8px">Word guide:</span>
        <span class="chip">Intro ~{wc[0]}w</span>
        <span class="chip chip-purple" style="margin-left:4px">Body ~{wc[1]}w</span>
        <span class="chip chip-green" style="margin-left:4px">Conclusion ~{wc[2]}w</span>
    </div>
</div>""", unsafe_allow_html=True)

rubric_pts = jl(selected_q["rubric_points"])
if rubric_pts:
    with st.expander("📋 Scoring hints (rubric)", expanded=False):
        for rp in rubric_pts:
            s = rp.get("section_hint", "body").upper()
            st.markdown(f'<div style="padding:3px 0;font-size:0.85rem"><span class="chip">{s}</span> {rp.get("point","")}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Answer form ────────────────────────────────────────────────────────────────
with st.form("quiz_form", clear_on_submit=False):
    st.markdown('<div class="section-header" style="color:#8AB4F8">Introduction</div>', unsafe_allow_html=True)
    intro_text = st.text_area("", height=100, key="intro",
        placeholder=f"~{wc[0]} words · Define the key concept, state the scope of your answer",
        label_visibility="collapsed")

    st.markdown('<div class="section-header" style="color:#C084FC;margin-top:8px">Body</div>', unsafe_allow_html=True)
    body_text = st.text_area("", height=260, key="body",
        placeholder=f"~{wc[1]} words · Analysis, theories, diagrams (described), data points, government schemes",
        label_visibility="collapsed")

    st.markdown('<div class="section-header" style="color:#81C995;margin-top:8px">Conclusion</div>', unsafe_allow_html=True)
    conc_text = st.text_area("", height=90, key="conc",
        placeholder=f"~{wc[2]} words · Policy implications, way forward, evaluative statement",
        label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    submitted = st.form_submit_button("Submit for Evaluation →", type="primary", use_container_width=True)

# ── Evaluation ─────────────────────────────────────────────────────────────────
if submitted:
    if not any([intro_text.strip(), body_text.strip(), conc_text.strip()]):
        st.warning("Please write something before submitting.")
        st.stop()

    rubric_str = "\n".join(
        f"[{rp.get('section_hint','body')}|wt={rp.get('weight',1)}] {rp.get('point','')}"
        for rp in rubric_pts
    )
    user_prompt = f"""Question ({marks_str}):
{selected_q['question_text']}

Rubric:
{rubric_str}

Student answer:
INTRO: {intro_text}

BODY: {body_text}

CONCLUSION: {conc_text}"""

    with st.spinner("Evaluating with Claude Sonnet..."):
        try:
            api_key = load_api_key()
            client = anthropic.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=1024,
                system=EVAL_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```"); raw = parts[1]
                if raw.startswith("json"): raw = raw[4:]
            result = json.loads(raw)
        except Exception as e:
            st.error(f"Evaluation failed: {e}")
            st.stop()

    # Save attempt (correct schema)
    try:
        conn.execute("""
            INSERT INTO descriptive_attempts
                (user_id, question_id, exam_id, quiz_mode,
                 user_answer_intro, user_answer_body, user_answer_conclusion,
                 word_count_intro, word_count_body, word_count_conclusion,
                 scores_json, weighted_score, session_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            USER_ID, selected_qid, EXAM_ID, "descriptive",
            intro_text, body_text, conc_text,
            len(intro_text.split()), len(body_text.split()), len(conc_text.split()),
            json.dumps(result),
            (result.get("score_overall", 0) or 0) / 10.0,
            uuid.uuid4().hex[:8],
        ))
        conn.commit()
    except Exception:
        pass  # don't break UI if save fails

    # Auto-advance topic state if score ≥ 6
    score_overall = result.get("score_overall", 0) or 0
    if score_overall >= 6 and mode == "Topic":
        topic_row = conn.execute(
            "SELECT state FROM gap_states WHERE user_id=? AND topic_id=? AND exam_id=?",
            (USER_ID, topic_choice, EXAM_ID)
        ).fetchone()
        if topic_row and topic_row[0] in ("IN_STUDY", "FLAGGED", "UNVISITED"):
            set_topic_state(conn, topic_choice, "PARTIAL", "quiz_score")

    # ── Score display ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Your Scores</div>', unsafe_allow_html=True)

    sc1, sc2, sc3, sc4 = st.columns(4)
    cards = [
        ("Introduction", result.get("score_intro")),
        ("Body",         result.get("score_body")),
        ("Conclusion",   result.get("score_conclusion")),
        ("Overall",      result.get("score_overall")),
    ]
    for col, (label, score) in zip([sc1, sc2, sc3, sc4], cards):
        with col:
            st.markdown(score_card_html(label, score), unsafe_allow_html=True)

    # ── Feedback ───────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    ftab_intro, ftab_body, ftab_conc, ftab_tips = st.tabs(
        ["Introduction", "Body", "Conclusion", "Tips & Missing"]
    )
    with ftab_intro:
        st.markdown(result.get("feedback_intro", "—"))
    with ftab_body:
        st.markdown(result.get("feedback_body", "—"))
    with ftab_conc:
        st.markdown(result.get("feedback_conclusion", "—"))
    with ftab_tips:
        strong = result.get("strong_points", [])
        missing = result.get("missing_points", [])
        if strong:
            st.markdown("**Strengths**")
            for s in strong:
                st.markdown(f'<div style="color:#81C995;padding:2px 0">✅ {s}</div>', unsafe_allow_html=True)
        if missing:
            st.markdown("**Missing points**")
            for m in missing:
                st.markdown(f'<div style="color:#F28B82;padding:2px 0">❌ {m}</div>', unsafe_allow_html=True)
        if result.get("suggested_improvements"):
            st.markdown("**Suggested improvements**")
            st.markdown(result["suggested_improvements"])

    # ── Model answer reveal ────────────────────────────────────────────────────
    if show_model and selected_q["answer_id"]:
        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()
        st.markdown('<div class="section-header">Model Answer</div>', unsafe_allow_html=True)
        ans = get_answer(conn, selected_qid)
        if ans:
            with st.expander("Introduction", expanded=True):
                st.markdown(f"""<div class="answer-section">{ans['intro_text']}</div>""", unsafe_allow_html=True)
            with st.expander("Body", expanded=True):
                st.markdown(f"""<div class="answer-section answer-section-body">{ans['body_text']}</div>""", unsafe_allow_html=True)
            with st.expander("Conclusion", expanded=True):
                st.markdown(f"""<div class="answer-section answer-section-conc">{ans['conclusion_text']}</div>""", unsafe_allow_html=True)
            if ans["diagram_mode"] == "described" and ans["diagram_description"]:
                with st.expander("📊 Diagram"):
                    st.markdown(ans["diagram_description"])

conn.close()
