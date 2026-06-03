import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from db import (
    get_conn, get_user_id, init_user, get_topics,
    get_mcq_questions, submit_return_quiz, get_true_readiness, log_event, EXAM_ID,
)
from styles import apply_theme, badge, chip, progress_bar

st.set_page_config(page_title="Return Quiz · IES 2026", layout="wide", page_icon="✅")
apply_theme()

PAPERS = [
    ("ge_01", "GE-01 · Micro & Macro"),
    ("ge_02", "GE-02 · Statistics & Math"),
    ("ge_03", "GE-03 · Indian Economy"),
    ("ge_04", "GE-04 · Economic Policy"),
]
PAPER_IDS = [p[0] for p in PAPERS]
PAPER_LABELS = [p[1] for p in PAPERS]

STATE_ORDER = {"FLAGGED": 0, "PARTIAL": 1, "IN_STUDY": 2, "DECAYING": 3, "UNVISITED": 4, "VERIFIED": 5}

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("rq_paper_id", "ge_01"),
    ("rq_topic_id", None),
    ("rq_last_result", None),
    ("rq_session_id", str(uuid.uuid4())),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── DB ────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _get_conn():
    return get_conn()

conn = _get_conn()
init_user(conn, get_user_id())

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ✅ Return Quiz")
    st.caption("5 MCQ questions · verify topic mastery · no AI cost")

    paper_idx = PAPER_IDS.index(st.session_state.rq_paper_id) if st.session_state.rq_paper_id in PAPER_IDS else 0
    selected_paper = st.radio("Paper", PAPER_LABELS, index=paper_idx, key="rq_paper_radio")
    selected_paper_id = PAPER_IDS[PAPER_LABELS.index(selected_paper)]

    if selected_paper_id != st.session_state.rq_paper_id:
        st.session_state.rq_paper_id = selected_paper_id
        st.session_state.rq_topic_id = None
        st.session_state.rq_last_result = None
        st.rerun()

    topics = get_topics(conn, selected_paper_id)
    topics_sorted = sorted(topics, key=lambda t: (STATE_ORDER.get(t["state"], 9), -(t.get("base_priority_score") or 0)))

    if not topics_sorted:
        st.info("No topics found.")
        st.stop()

    topic_ids_list = [t["topic_id"] for t in topics_sorted]
    topic_labels = []
    for t in topics_sorted:
        mastery_pct = int((t.get("mastery_level") or 0.0) * 100)
        state_icon = {"VERIFIED": "✅", "PARTIAL": "🟡", "FLAGGED": "🔴", "DECAYING": "🔁"}.get(t["state"], "○")
        topic_labels.append(f"{state_icon} {t['topic_name']} ({mastery_pct}%)")

    curr_tid = st.session_state.rq_topic_id
    topic_idx = topic_ids_list.index(curr_tid) if curr_tid in topic_ids_list else 0
    selected_label = st.selectbox("Topic", topic_labels, index=topic_idx, key="rq_topic_sel")
    selected_topic_id = topic_ids_list[topic_labels.index(selected_label)]

    if selected_topic_id != st.session_state.rq_topic_id:
        st.session_state.rq_topic_id = selected_topic_id
        st.session_state.rq_last_result = None
        st.rerun()

    st.divider()
    readiness = get_true_readiness(conn)
    st.metric("Readiness Now", f"{readiness['formula_pct']:.1f}%", help="Weighted mastery across all topics")
    st.metric("If Top 10 Done", f"{readiness['projected_pct']:.1f}%", help="Projected if top gaps are filled")
    st.caption("Scores ≥ 80% → VERIFIED · 50–79% → PARTIAL · < 50% → FLAGGED")

# ── MAIN ──────────────────────────────────────────────────────────────────────
topic_id = st.session_state.rq_topic_id or topic_ids_list[0]
topic_info = next((t for t in topics_sorted if t["topic_id"] == topic_id), None)
questions = get_mcq_questions(conn, topic_id)

if not topic_info or not questions:
    st.warning("No MCQ questions available for this topic yet.")
    st.stop()

state = topic_info["state"]
mastery = topic_info.get("mastery_level") or 0.0
base_score = topic_info.get("base_priority_score") or 0.5

# Header
col_h, col_r = st.columns([3, 1])
with col_h:
    st.markdown(f"## ✅ {topic_info['topic_name']}")
    stuck = topic_info.get("stuck_flag", 0) or 0
    parts = [chip(selected_paper_id.upper(), "purple"), badge(state)]
    if stuck:
        parts.append(chip("Stuck — try a different approach", "red"))
    st.markdown(" ".join(parts), unsafe_allow_html=True)
    st.markdown(f"Priority score: **{base_score:.3f}** · {len(questions)} questions")

with col_r:
    st.metric("Current mastery", f"{int(mastery * 100)}%")
    st.markdown(progress_bar(mastery), unsafe_allow_html=True)

st.divider()

# ── RESULT VIEW ───────────────────────────────────────────────────────────────
last_result = st.session_state.rq_last_result
if last_result and last_result.get("topic_id") == topic_id:
    res = last_result["result"]
    correct, total, score = res["correct"], res["total"], res["score"]
    new_state, from_state = res["new_state"], res["from_state"]
    submitted_answers = last_result["answers"]

    color_icon = "🟢" if score >= 0.8 else ("🟡" if score >= 0.5 else "🔴")
    st.markdown(f"### {color_icon} {correct}/{total} correct — {int(score * 100)}%")

    if new_state != from_state:
        st.success(f"**{from_state}** → **{new_state}** · Gap state updated")
    else:
        st.info(f"Gap state remains **{new_state}**")

    new_mastery = res.get("new_mastery", mastery)
    st.markdown(f"Updated mastery: **{int(new_mastery * 100)}%**")
    st.markdown(progress_bar(new_mastery), unsafe_allow_html=True)
    st.markdown("")

    st.markdown("#### Per-question breakdown")
    for i, q in enumerate(questions):
        qid = q["question_id"]
        user_ans = submitted_answers.get(qid, "")
        is_correct = user_ans.strip() == (q["correct_answer"] or "").strip()
        icon = "✅" if is_correct else "❌"
        with st.expander(f"{icon} Q{i + 1}  ·  {q['question_text'][:90]}{'…' if len(q['question_text']) > 90 else ''}"):
            opts = [q["correct_answer"], q.get("option_b"), q.get("option_c"), q.get("option_d")]
            opts = sorted([o for o in opts if o])
            for opt in opts:
                is_opt_correct = opt.strip() == (q["correct_answer"] or "").strip()
                is_opt_chosen = opt.strip() == user_ans.strip()
                if is_opt_correct and is_opt_chosen:
                    st.markdown(f"**✓ {opt}** ← your answer ✅")
                elif is_opt_correct:
                    st.markdown(f"**✓ {opt}** ← correct answer")
                elif is_opt_chosen:
                    st.markdown(f"~~{opt}~~ ← your answer ❌")
                else:
                    st.markdown(f"  {opt}")
            dim = q.get("dimension_id") or "concept"
            st.caption(f"Difficulty: {q.get('difficulty', 0.5):.2f} · Focus: {dim}")

    st.divider()
    curr_idx = topic_ids_list.index(topic_id) if topic_id in topic_ids_list else 0
    next_idx = (curr_idx + 1) % len(topic_ids_list)
    next_topic = topics_sorted[next_idx]

    col_retry, col_next = st.columns(2)
    with col_retry:
        if st.button("↩ Retry this topic", use_container_width=True):
            st.session_state.rq_last_result = None
            st.session_state.rq_session_id = str(uuid.uuid4())
            st.rerun()
    with col_next:
        next_label = next_topic["topic_name"][:30]
        if st.button(f"Next → {next_label}…", use_container_width=True, type="primary"):
            st.session_state.rq_topic_id = next_topic["topic_id"]
            st.session_state.rq_last_result = None
            st.session_state.rq_session_id = str(uuid.uuid4())
            st.rerun()

    st.stop()

# ── QUIZ FORM ─────────────────────────────────────────────────────────────────
st.markdown(f"### Answer all 5 questions, then submit")
st.caption("All answers are graded instantly — no AI call. Results update your gap state and readiness score.")

answers: dict[str, str] = {}
form_key = f"rq_form_{topic_id}_{st.session_state.rq_session_id}"

with st.form(form_key):
    for i, q in enumerate(questions):
        qid = q["question_id"]
        difficulty = q.get("difficulty") or 0.5
        diff_label = "Easy" if difficulty < 0.5 else ("Medium" if difficulty < 0.7 else "Hard")
        dim = q.get("dimension_id") or "concept"

        st.markdown(f"**Q{i + 1}.**  {q['question_text']}")
        st.caption(f"Difficulty: {diff_label} · Focus: {dim}")

        opts = [q["correct_answer"], q.get("option_b"), q.get("option_c"), q.get("option_d")]
        opts = sorted([o for o in opts if o])

        chosen = st.radio(
            "",
            opts,
            index=None,
            key=f"rq_radio_{topic_id}_{qid}",
            label_visibility="collapsed",
        )
        answers[qid] = chosen or ""

        if i < len(questions) - 1:
            st.markdown("---")

    st.markdown("")
    submitted = st.form_submit_button("Submit Quiz →", use_container_width=True, type="primary")

if submitted:
    unanswered = [i + 1 for i, q in enumerate(questions) if not answers.get(q["question_id"])]
    if unanswered:
        q_nums = ", ".join(f"Q{n}" for n in unanswered)
        st.warning(f"Please answer {q_nums} before submitting.")
    else:
        result = submit_return_quiz(conn, topic_id, answers, st.session_state.rq_session_id)
        if result is not None:
            log_event(conn, "return_quiz_submitted", entity_type="topic", entity_id=topic_id, exam_id=EXAM_ID,
                      payload={"score": round(result["score"], 4), "correct": result["correct"],
                               "total": result["total"], "session_id": st.session_state.rq_session_id})
        st.session_state.rq_last_result = {
            "topic_id": topic_id,
            "result": result,
            "answers": answers,
        }
        st.rerun()
