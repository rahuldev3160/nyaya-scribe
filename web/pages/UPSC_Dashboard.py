"""UPSC Economics Optional — Topic Dashboard."""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from auth import require_user
from db import get_conn as _get_ies_conn, get_user_id, track_page_time
from styles import apply_theme, badge, progress_bar

st.set_page_config(page_title="UPSC Dashboard · Eco Optional", layout="wide", page_icon="🎓")
apply_theme()

_ies_conn = _get_ies_conn()
user_id = require_user(_ies_conn)
track_page_time(_ies_conn, "UPSC Dashboard")
_ies_conn.close()

UPSC_DATE = "2026-08-22"
UPSC_EXAM_ID = "upsc_eco_opt"
_DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc.db"

PAPER_LABELS = {
    "upsc_p1": "Paper I · Theory",
    "upsc_p2": "Paper II · Indian Economy",
}

_STATE_META = {
    "UNVISITED": "not yet started",
    "IN_STUDY":  "in progress",
    "PARTIAL":   "partially done",
    "VERIFIED":  "fully verified ✓",
    "DECAYING":  "needs a quick refresh",
    "FLAGGED":   "needs more practice",
}

_STATE_DISPLAY = {
    "UNVISITED": "Not Started", "IN_STUDY": "In Progress", "FLAGGED": "Needs Work",
    "PARTIAL": "Partially Done", "VERIFIED": "Verified", "DECAYING": "Needs Refresh",
}


def _days_left() -> int:
    return (datetime.strptime(UPSC_DATE, "%Y-%m-%d").date() - datetime.today().date()).days


def _get_conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c


def _init_user(conn: sqlite3.Connection, uid: str) -> None:
    """Insert gap_states rows for any topics this user doesn't have yet."""
    topics = conn.execute(
        "SELECT topic_id, paper_id FROM topics WHERE exam_id=? AND topic_level='topic'",
        (UPSC_EXAM_ID,),
    ).fetchall()
    changed = False
    for t in topics:
        exists = conn.execute(
            "SELECT 1 FROM gap_states WHERE user_id=? AND topic_id=? AND exam_id=?",
            (uid, t["topic_id"], UPSC_EXAM_ID),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO gap_states (user_id, topic_id, exam_id, paper_id, state, attempt_count) "
                "VALUES (?,?,?,?,?,0)",
                (uid, t["topic_id"], UPSC_EXAM_ID, t["paper_id"], "UNVISITED"),
            )
            changed = True
    if changed:
        conn.commit()


def _get_topics(conn: sqlite3.Connection, uid: str, paper_id: str | None = None) -> list[dict]:
    paper_clause = "AND t.paper_id=?" if paper_id else ""
    params: list = [UPSC_EXAM_ID, "topic", uid, UPSC_EXAM_ID]
    if paper_id:
        params.insert(2, paper_id)
    rows = conn.execute(
        f"""SELECT t.topic_id, t.topic_name, t.paper_id,
               gs.state,
               COALESCE(bs.base_priority_score, 0.5) AS base_priority_score,
               COALESCE(bs.pyq_count, 0)             AS pyq_count,
               COUNT(DISTINCT q.question_id)          AS total_q,
               COUNT(DISTINCT ma.answer_id)           AS answers_ready,
               COALESCE(um.mastery_level, 0.0)        AS mastery_level
        FROM topics t
        LEFT JOIN gap_states gs
               ON gs.user_id=? AND gs.topic_id=t.topic_id AND gs.exam_id=?
        LEFT JOIN topic_base_scores bs
               ON bs.topic_id=t.topic_id AND bs.exam_id=t.exam_id
        LEFT JOIN pyq_questions q
               ON q.topic_id=t.topic_id AND q.exam_id=t.exam_id
        LEFT JOIN model_answers ma
               ON ma.question_id=q.question_id AND ma.exam_id=q.exam_id
        LEFT JOIN user_mastery um
               ON um.user_id=? AND um.topic_id=t.topic_id AND um.exam_id=?
        WHERE t.exam_id=? AND t.topic_level='topic' {paper_clause}
        GROUP BY t.topic_id
        ORDER BY base_priority_score DESC""",
        [uid, UPSC_EXAM_ID, uid, UPSC_EXAM_ID, UPSC_EXAM_ID] + ([paper_id] if paper_id else []),
    ).fetchall()
    return [dict(r) for r in rows]


def _set_state(conn: sqlite3.Connection, uid: str, topic_id: str, new_state: str) -> None:
    conn.execute(
        "UPDATE gap_states SET state=?, last_active_at=datetime('now') "
        "WHERE user_id=? AND topic_id=? AND exam_id=?",
        (new_state, uid, topic_id, UPSC_EXAM_ID),
    )
    conn.commit()


if not _DB_PATH.exists():
    st.error("upsc.db not found.")
    st.stop()

conn = _get_conn()
_init_user(conn, user_id)

d = _days_left()

all_topics = _get_topics(conn, user_id)
state_counts: dict = {}
for t in all_topics:
    s = t["state"] or "UNVISITED"
    state_counts[s] = state_counts.get(s, 0) + 1

verified = state_counts.get("VERIFIED", 0)
total_t = len(all_topics)
in_progress = state_counts.get("IN_STUDY", 0) + state_counts.get("PARTIAL", 0)

total_q = sum(t["total_q"] for t in all_topics)
total_ans = sum(t["answers_ready"] for t in all_topics)
ans_pct = int(100 * total_ans / total_q) if total_q else 0

# ── Header ────────────────────────────────────────────────────────────────────

day_color = "#F28B82" if d <= 30 else "#FDD663" if d <= 60 else "#8AB4F8"
st.markdown("## 🎓 UPSC Eco Optional Dashboard")
st.markdown(
    '<span style="color:#9AA0A6;font-size:0.85rem;">'
    "Mains ~22 Aug 2026 (tentative) · Paper I: Theory · Paper II: Indian Economy"
    "</span>",
    unsafe_allow_html=True,
)

# ── Metrics row ───────────────────────────────────────────────────────────────

h1, h2, h3, h4, h5 = st.columns(5)
with h1:
    st.markdown(
        f'<div class="gem-card" style="text-align:center;border-color:{day_color}33">'
        f'<div style="font-size:2rem;font-weight:700;color:{day_color}">{d}</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Days Left</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with h2:
    st.markdown(
        f'<div class="gem-card" style="text-align:center">'
        f'<div style="font-size:2rem;font-weight:700;color:#81C995">{verified}</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Topics Verified</div>'
        f'<div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">of {total_t} topics</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with h3:
    ip_color = "#FDD663" if in_progress > 0 else "#9AA0A6"
    st.markdown(
        f'<div class="gem-card" style="text-align:center">'
        f'<div style="font-size:2rem;font-weight:700;color:{ip_color}">{in_progress}</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">In Progress</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with h4:
    st.markdown(
        f'<div class="gem-card" style="text-align:center">'
        f'<div style="font-size:2rem;font-weight:700;color:#8AB4F8">{total_ans}</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Model Answers</div>'
        f'<div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">{ans_pct}% of {total_q} PYQs</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with h5:
    readiness_pct = int(100 * verified / total_t) if total_t else 0
    r_color = "#F28B82" if readiness_pct < 20 else "#FDD663" if readiness_pct < 50 else "#81C995"
    st.markdown(
        f'<div class="gem-card" style="text-align:center;border-color:{r_color}33">'
        f'<div style="font-size:2rem;font-weight:700;color:{r_color}">{readiness_pct}%</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Topics Complete</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

_qc, _ = st.columns([1, 3])
with _qc:
    st.page_link("pages/7_UPSC_Mains.py", label="→ Browse Model Answers", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# ── Paper tabs ────────────────────────────────────────────────────────────────

_FOCUS_NEXT = {
    "UNVISITED": ("Begin Study",   "IN_STUDY"),
    "FLAGGED":   ("Resume",         "IN_STUDY"),
    "DECAYING":  ("Resume",         "IN_STUDY"),
    "IN_STUDY":  ("Mark Partial",   "PARTIAL"),
    "PARTIAL":   ("Mark Verified",  "VERIFIED"),
    "VERIFIED":  ("Verified ✓",     "VERIFIED"),
}

tabs = st.tabs([PAPER_LABELS["upsc_p1"], PAPER_LABELS["upsc_p2"]])

for tab, paper_id in zip(tabs, ["upsc_p1", "upsc_p2"]):
    with tab:
        topics = _get_topics(conn, user_id, paper_id)
        p_verified = sum(1 for t in topics if (t["state"] or "UNVISITED") == "VERIFIED")
        p_total = len(topics)
        p_pct = int(100 * p_verified / p_total) if p_total else 0
        p_color = "#F28B82" if p_pct < 20 else "#FDD663" if p_pct < 50 else "#81C995"
        st.markdown(
            progress_bar(p_pct, 100) +
            f'<div style="font-size:0.72rem;color:#9AA0A6;margin-bottom:10px">'
            f'<span style="color:{p_color};font-weight:600">{p_pct}%</span>'
            f' verified · {p_verified}/{p_total} topics done</div>',
            unsafe_allow_html=True,
        )

        for t in topics:
            state = t["state"] or "UNVISITED"
            ans = t["answers_ready"] or 0
            total = t["total_q"] or 0
            name = t["topic_name"] or t["topic_id"].replace("_", " ").title()
            score = t["base_priority_score"] or 0.0
            mastery_pct = round((t["mastery_level"] or 0) * 100)

            col_a, col_b, col_c, col_d, col_e = st.columns([4, 2, 1.2, 1.2, 1.2])
            with col_a:
                st.markdown(
                    f'{badge(state)} <span style="font-size:0.92rem;font-weight:500;margin-left:6px">{name}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    progress_bar(ans, total or 1) +
                    f'<div style="font-size:0.68rem;color:#9AA0A6;margin-top:2px">'
                    f'{ans}/{total} answers · {mastery_pct}% mastered</div>',
                    unsafe_allow_html=True,
                )
            with col_b:
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#9AA0A6;padding-top:4px">'
                    f'{t["pyq_count"] or 0} past questions · '
                    f'<strong style="color:#8AB4F8">{_STATE_META.get(state, "")}</strong></div>',
                    unsafe_allow_html=True,
                )
            with col_c:
                btn_label, next_state = _FOCUS_NEXT.get(state, ("Begin Study", "IN_STUDY"))
                if st.button(btn_label, key=f"adv_{paper_id}_{t['topic_id']}", use_container_width=True,
                             disabled=(state == "VERIFIED")):
                    _set_state(conn, user_id, t["topic_id"], next_state)
                    st.rerun()
            with col_d:
                if st.button("Quick Verify", key=f"ver_{paper_id}_{t['topic_id']}", use_container_width=True,
                             disabled=(state == "VERIFIED"),
                             help="Mark as fully verified from any state"):
                    _set_state(conn, user_id, t["topic_id"], "VERIFIED")
                    st.rerun()
            with col_e:
                if st.button("Reset", key=f"rst_{paper_id}_{t['topic_id']}", use_container_width=True,
                             help="Reset to Not Started"):
                    _set_state(conn, user_id, t["topic_id"], "UNVISITED")
                    st.rerun()

# ── Overview ──────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
st.divider()
st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

STATE_ORDER = ["UNVISITED", "IN_STUDY", "FLAGGED", "PARTIAL", "VERIFIED", "DECAYING"]
STATE_COLORS = {
    "UNVISITED": "#9AA0A6", "IN_STUDY": "#FDD663", "FLAGGED": "#8AB4F8",
    "PARTIAL": "#81C995", "VERIFIED": "#81C995", "DECAYING": "#F28B82",
}
STATE_EMOJI = {"UNVISITED": "○", "IN_STUDY": "◑", "FLAGGED": "⚑",
               "PARTIAL": "◕", "VERIFIED": "✓", "DECAYING": "↓"}

scols = st.columns(6)
for col, s in zip(scols, STATE_ORDER):
    cnt = state_counts.get(s, 0)
    color = STATE_COLORS[s]
    with col:
        st.markdown(
            f'<div class="gem-card" style="text-align:center;border-color:{color}33">'
            f'<div style="font-size:1.8rem;font-weight:700;color:{color}">{cnt}</div>'
            f'<div style="font-size:0.68rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">'
            f'{STATE_EMOJI[s]} {_STATE_DISPLAY.get(s, s)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

conn.close()
