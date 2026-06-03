"""My Progress — quiz attempt history and score trends."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

from db import EXAM_ID, get_user_id, get_attempts, get_attempt_summary, get_conn, get_topics
from styles import apply_theme, chip, score_color

st.set_page_config(page_title="My Progress · IES 2026", layout="wide", page_icon="📈")
apply_theme()

@st.cache_resource
def _get_conn():
    return get_conn()

conn = _get_conn()

st.markdown("## 📈 My Progress")
st.markdown('<div style="color:#9AA0A6;font-size:0.88rem;margin-bottom:1rem">Track your quiz attempts and score improvements over time.</div>', unsafe_allow_html=True)

summary = get_attempt_summary(conn)

# ── Summary metrics ────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
metrics = [
    ("Total Attempts", summary["total"], "#8AB4F8"),
    ("Average Score", f"{summary['avg_score']}/10" if summary["avg_score"] is not None else "—", "#C084FC"),
    ("Best Score",    f"{summary['max_score']}/10" if summary["max_score"] is not None else "—", "#81C995"),
    ("Most Practiced", summary["top_topic"].replace("_"," ").title() if summary["top_topic"] else "—", "#FDD663"),
]
for col, (label, val, color) in zip([m1, m2, m3, m4], metrics):
    with col:
        st.markdown(f"""<div class="gem-card" style="text-align:center;border-color:{color}33">
            <div style="font-size:1.6rem;font-weight:700;color:{color}">{val}</div>
            <div style="font-size:0.7rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if summary["total"] == 0:
    st.markdown("""<div class="gem-card" style="text-align:center;padding:48px 24px">
        <div style="font-size:2.5rem;margin-bottom:12px">✍️</div>
        <div style="font-size:1.1rem;color:#E8EAED;margin-bottom:8px">No quiz attempts yet</div>
        <div style="font-size:0.85rem;color:#9AA0A6">Head to the Quiz page to practice your first question</div>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 My Progress")
    st.divider()
    all_topics = get_topics(conn)
    topic_filter_opts = ["All topics"] + [t["topic_id"] for t in all_topics]
    topic_filter = st.selectbox("Filter by topic", topic_filter_opts,
                                format_func=lambda x: x.replace("_"," ").title() if x != "All topics" else x)
    date_range = st.date_input("Date range", value=[], help="Leave empty for all dates")

topic_id_filter = None if topic_filter == "All topics" else topic_filter
date_from = date_range[0] if isinstance(date_range, (list, tuple)) and len(date_range) >= 1 else None
date_to   = date_range[1] if isinstance(date_range, (list, tuple)) and len(date_range) >= 2 else None

attempts = get_attempts(conn, topic_id=topic_id_filter, date_from=date_from, date_to=date_to)

if not attempts:
    st.info("No attempts match the selected filters.")
    st.stop()

# ── Attempts table ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">Attempt History</div>', unsafe_allow_html=True)

rows = []
for a in attempts:
    scores = a.get("scores") or {}
    if isinstance(scores, str):
        try: scores = json.loads(scores)
        except: scores = {}
    rows.append({
        "Date": a["created_at"][:10] if a["created_at"] else "—",
        "Topic": (a.get("topic_id") or "").replace("_"," ").title(),
        "Paper": (a.get("paper_id") or "").upper().replace("_","-"),
        "Year": a.get("year", "—"),
        "Marks": a.get("marks", "—"),
        "Score": round((a.get("weighted_score") or 0) * 10, 1),
        "Intro": scores.get("score_intro", "—"),
        "Body":  scores.get("score_body", "—"),
        "Conc":  scores.get("score_conclusion", "—"),
        "Words Written": (a.get("word_count_intro") or 0) + (a.get("word_count_body") or 0) + (a.get("word_count_conclusion") or 0),
    })

df = pd.DataFrame(rows)

st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "Score": st.column_config.ProgressColumn(
            "Overall Score",
            min_value=0, max_value=10,
            format="%.1f",
        ),
    },
    hide_index=True,
)

# ── Score trends ───────────────────────────────────────────────────────────────
if len(attempts) >= 3:
    with st.expander("📊 Score Trends by Topic", expanded=False):
        topic_dfs = {}
        for a in attempts:
            tid = (a.get("topic_id") or "unknown").replace("_", " ").title()
            score = round((a.get("weighted_score") or 0) * 10, 1)
            date  = a["created_at"][:10] if a["created_at"] else "unknown"
            if tid not in topic_dfs:
                topic_dfs[tid] = []
            topic_dfs[tid].append({"date": date, "score": score})

        multi_topics = {k: v for k, v in topic_dfs.items() if len(v) >= 3}
        if multi_topics:
            chart_data = {}
            for tid, records in multi_topics.items():
                for r in records:
                    chart_data.setdefault(r["date"], {})[tid] = r["score"]
            chart_df = pd.DataFrame(chart_data).T.sort_index()
            st.line_chart(chart_df)
        else:
            st.caption("Practice at least 3 questions per topic to see score trends.")

# ── Recent attempts detail ─────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">Recent Attempts (last 5)</div>', unsafe_allow_html=True)

for a in attempts[:5]:
    scores = a.get("scores") or {}
    if isinstance(scores, str):
        try: scores = json.loads(scores)
        except: scores = {}

    ws = a.get("weighted_score") or 0
    overall = round(ws * 10, 1)
    color_cls = score_color(overall)
    color_map = {"score-green": "#81C995", "score-amber": "#FDD663", "score-red": "#F28B82"}
    color = color_map.get(color_cls, "#9AA0A6")

    topic_name = (a.get("topic_id") or "").replace("_"," ").title()
    date_str = a["created_at"][:10] if a["created_at"] else "—"
    marks_str = f"{a.get('marks','?')}m" if a.get("marks") else "—"

    st.markdown(f"""<div class="gem-card" style="border-left:3px solid {color}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <span class="chip">{date_str}</span>
                <span class="chip chip-purple" style="margin-left:4px">{topic_name}</span>
                <span class="chip" style="margin-left:4px">{a.get('paper_id','').upper().replace('_','-')}</span>
                <span class="chip" style="margin-left:4px">{marks_str}</span>
            </div>
            <div style="font-size:1.4rem;font-weight:700;color:{color}">{overall}/10</div>
        </div>
        <div style="font-size:0.85rem;color:#9AA0A6;margin-top:6px;line-height:1.4">{a.get('question_text','')[:100]}…</div>
        <div style="margin-top:8px;font-size:0.78rem;color:#9AA0A6">
            Intro: <strong style="color:#8AB4F8">{scores.get('score_intro','—')}</strong> ·
            Body: <strong style="color:#C084FC">{scores.get('score_body','—')}</strong> ·
            Conclusion: <strong style="color:#81C995">{scores.get('score_conclusion','—')}</strong>
        </div>
    </div>""", unsafe_allow_html=True)
