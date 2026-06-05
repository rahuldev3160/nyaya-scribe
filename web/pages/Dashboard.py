"""IES 2026 Study Dashboard."""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from db import EXAM_DATE, EXAM_ID, get_conn, get_user_id, init_user, get_topics, get_true_readiness, get_paper_coverage, set_topic_state, is_crunch_mode, get_study_path, track_page_time
from auth import require_user
from styles import apply_theme, badge, progress_bar

st.set_page_config(
    page_title="Dashboard · IES 2026",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

conn = get_conn()
user_id = require_user(conn)
init_user(conn, user_id)

# Redirect first-time users to onboarding
_onb = conn.execute(
    "SELECT onboarding_completed FROM users WHERE user_id=?", (user_id,)
).fetchone()
if _onb and not _onb["onboarding_completed"]:
    conn.close()
    st.switch_page("pages/8_My_Setup.py")
    st.stop()

track_page_time(conn, "Dashboard")

# ── Cross-exam banner ─────────────────────────────────────────────────────────
_focus_row = conn.execute("SELECT exam_focus FROM users WHERE user_id=?", (user_id,)).fetchone()
_exam_focus = json.loads(_focus_row["exam_focus"] or '["ies"]') if _focus_row and _focus_row["exam_focus"] else ["ies"]
_other_exams = [e for e in _exam_focus if e != "ies"]
_OTHER_LINKS = {
    "rbi":  ("pages/RBI_Dashboard.py",  "🏦 RBI DEPR Dashboard (14th June)"),
    "upsc": ("pages/UPSC_Dashboard.py", "🎓 UPSC Eco Optional Dashboard (~Aug 2026)"),
}
if _other_exams:
    _banner_cols = st.columns(len(_other_exams))
    for _col, _exam in zip(_banner_cols, _other_exams):
        _path, _label = _OTHER_LINKS[_exam]
        with _col:
            st.page_link(_path, label=f"→ {_label}", use_container_width=True)
    st.markdown("<br>", unsafe_allow_html=True)


def days_left() -> int:
    return (datetime.strptime(EXAM_DATE, "%Y-%m-%d").date() - datetime.today().date()).days


def priority_label(score: float) -> str:
    if score >= 0.85: return "Top priority"
    if score >= 0.60: return "High priority"
    if score >= 0.40: return "Medium priority"
    return "Lower priority"


_STATE_META = {
    "UNVISITED": "not yet started",
    "IN_STUDY":  "in progress",
    "PARTIAL":   "partially done — test yourself to verify",
    "VERIFIED":  "fully verified ✓",
    "DECAYING":  "studied before — needs a quick refresh",
    "FLAGGED":   "scored below 50% in quiz — needs more practice",
}

_STATE_DISPLAY = {
    "UNVISITED": "Not Started", "IN_STUDY": "In Progress", "FLAGGED": "Needs Work",
    "PARTIAL": "Partially Done", "VERIFIED": "Verified", "DECAYING": "Needs Refresh",
}

_FOCUS_START_LABEL = {
    "UNVISITED": "Begin Study",
    "FLAGGED":   "Resume",
    "DECAYING":  "Resume",
    "IN_STUDY":  "Mark Partial",
    "PARTIAL":   "Mark Verified",
}


# ── Header metrics ─────────────────────────────────────────────────────────────
d = days_left()
total_a = conn.execute("SELECT COUNT(*) FROM model_answers WHERE exam_id=?", (EXAM_ID,)).fetchone()[0]
total_q = conn.execute("SELECT COUNT(*) FROM pyq_questions WHERE exam_id=?", (EXAM_ID,)).fetchone()[0]
verified = conn.execute(
    "SELECT COUNT(*) FROM gap_states WHERE exam_id=? AND user_id=? AND state='VERIFIED'",
    (EXAM_ID, get_user_id())
).fetchone()[0]
total_t = conn.execute(
    "SELECT COUNT(*) FROM gap_states WHERE exam_id=? AND user_id=?",
    (EXAM_ID, get_user_id())
).fetchone()[0]
readiness = get_true_readiness(conn)

h1, h2, h3, h4, h5, h6 = st.columns([3, 1, 1, 1, 1, 1])
with h1:
    st.markdown("## 📚 IES 2026 Study Dashboard")
    st.markdown(f'<span style="color:#9AA0A6;font-size:0.85rem;">Exam 19-21 June 2026 · GE-01 to GE-04</span>', unsafe_allow_html=True)
with h2:
    day_color = "#F28B82" if d <= 14 else "#8AB4F8"
    st.markdown(f"""<div class="gem-card" style="text-align:center;border-color:{day_color}33">
        <div style="font-size:2rem;font-weight:700;color:{day_color}">{d}</div>
        <div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Days Left</div>
    </div>""", unsafe_allow_html=True)
with h3:
    pct = int(100 * total_a / total_q) if total_q else 0
    st.markdown(f"""<div class="gem-card" style="text-align:center">
        <div style="font-size:2rem;font-weight:700;color:#8AB4F8">{total_a}</div>
        <div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Answers Ready</div>
        <div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">{pct}% of {total_q} PYQs</div>
    </div>""", unsafe_allow_html=True)
with h4:
    st.markdown(f"""<div class="gem-card" style="text-align:center">
        <div style="font-size:2rem;font-weight:700;color:#81C995">{verified}</div>
        <div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Topics Verified</div>
        <div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">of {total_t} topics</div>
    </div>""", unsafe_allow_html=True)
with h5:
    formula_pct = readiness["formula_pct"]
    r_color = "#F28B82" if formula_pct < 20 else "#FDD663" if formula_pct < 50 else "#81C995"
    st.markdown(f"""<div class="gem-card" style="text-align:center;border-color:{r_color}33">
        <div style="font-size:2rem;font-weight:700;color:{r_color}">{formula_pct:.0f}%</div>
        <div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Readiness Now</div>
        <div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">{readiness["covered_count"]}/{readiness["topic_count"]} topics ≥50%</div>
    </div>""", unsafe_allow_html=True)
with h6:
    proj_pct = readiness["projected_pct"]
    st.markdown(f"""<div class="gem-card" style="text-align:center;border-color:#8AB4F833">
        <div style="font-size:2rem;font-weight:700;color:#8AB4F8">{proj_pct:.0f}%</div>
        <div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">If Top 10 Done</div>
        <div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">projected if top gaps filled</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if is_crunch_mode():
    st.markdown("""<div style="background:#F28B8222;border:1px solid #F28B82;border-radius:8px;padding:10px 16px;margin-bottom:12px;">
    <span style="color:#F28B82;font-weight:700;font-size:1rem;">⚡ CRUNCH MODE</span>
    <span style="color:#9AA0A6;font-size:0.85rem;margin-left:8px;">≤7 days left — MCQ pass threshold lowered to 70%. Focus on top gaps only.</span>
    </div>""", unsafe_allow_html=True)

# ── Your Study Path banner ─────────────────────────────────────────────────────
_path = get_study_path(conn, user_id)
if _path:
    _phase = _path.get("current_phase", "")
    _today = _path.get("today_action", "")
    if _phase or _today:
        _pc, _lc = st.columns([5, 1])
        with _pc:
            st.markdown(
                f'<div style="background:#1C2B3A;border:1px solid #8AB4F833;border-radius:8px;'
                f'padding:11px 16px">'
                f'<span style="color:#8AB4F8;font-weight:700;font-size:0.8rem;'
                f'text-transform:uppercase;letter-spacing:.07em">🎯 {_phase}</span>'
                f'<span style="color:#9AA0A6;font-size:0.82rem;margin-left:10px">Today: </span>'
                f'<span style="color:#E8EAED;font-size:0.88rem">{_today}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        with _lc:
            st.page_link("pages/8_My_Setup.py", label="Update plan", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

# ── Today's Focus ──────────────────────────────────────────────────────────────
all_topics = get_topics(conn)

focus_topics = [t for t in all_topics if (t["state"] or "UNVISITED") in ("IN_STUDY", "DECAYING", "FLAGGED")]
if len(focus_topics) < 3:
    unvisited = sorted(
        [t for t in all_topics if (t["state"] or "UNVISITED") == "UNVISITED"],
        key=lambda x: -(x["base_priority_score"] or 0)
    )
    focus_topics = focus_topics + unvisited
focus_topics = focus_topics[:3]

st.markdown('<div class="section-header">Today\'s Focus</div>', unsafe_allow_html=True)
fc1, fc2, fc3 = st.columns(3)
for col, t in zip([fc1, fc2, fc3], focus_topics):
    state = t["state"] or "UNVISITED"
    score = t["base_priority_score"] or 0.0
    ans = t["answers_ready"] or 0
    total = t["total_q"] or 0
    name = t["topic_id"].replace("_", " ").title()
    paper = t["paper_id"].upper().replace("_", "-")
    mastery_pct = round((t.get("mastery_level") or 0) * 100)

    with col:
        st.markdown(f"""<div class="focus-card">
            {badge(state)}
            <h4>{name}</h4>
            <div class="meta">{paper} · {t['pyq_count'] or 0} past questions · {priority_label(score)}</div>
            <div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">{_STATE_META.get(state, '')}</div>
            {progress_bar(mastery_pct, 100)}
            <div style="font-size:0.7rem;color:#9AA0A6;margin-top:4px">{mastery_pct}% mastered · {ans}/{total} answers ready</div>
        </div>""", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        with b1:
            _btn = _FOCUS_START_LABEL.get(state, "Begin Study")
            if st.button(_btn, key=f"focus_start_{t['topic_id']}", use_container_width=True,
                         disabled=(state == "VERIFIED")):
                next_s = {"UNVISITED": "IN_STUDY", "FLAGGED": "IN_STUDY", "DECAYING": "IN_STUDY",
                          "IN_STUDY": "PARTIAL", "PARTIAL": "VERIFIED"}.get(state, state)
                set_topic_state(conn, t["topic_id"], next_s, "ui_focus_start")
                st.rerun()
        with b2:
            if st.button("Mark Verified", key=f"focus_done_{t['topic_id']}", use_container_width=True,
                         disabled=(state == "VERIFIED")):
                set_topic_state(conn, t["topic_id"], "VERIFIED", "ui_focus_done")
                st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# ── Paper tabs ─────────────────────────────────────────────────────────────────
PAPERS = [
    ("ge_01", "GE-01 · Micro & Macro"),
    ("ge_02", "GE-02 · Statistics & Math"),
    ("ge_03", "GE-03 · Indian Economy"),
    ("ge_04", "GE-04 · Economic Policy"),
]
tabs = st.tabs([p[1] for p in PAPERS])
paper_cov = {p["paper_id"]: p for p in get_paper_coverage(conn)}

for tab, (paper_id, _) in zip(tabs, PAPERS):
    with tab:
        topics = get_topics(conn, paper_id)
        pc = paper_cov.get(paper_id, {})
        cov_pct = pc.get("coverage_pct", 0.0)
        cov_done = pc.get("covered_count", 0)
        cov_total = pc.get("topic_count", len(topics))
        cov_color = "#F28B82" if cov_pct < 20 else "#FDD663" if cov_pct < 50 else "#81C995"
        st.markdown(
            progress_bar(cov_pct, 100) +
            f'<div style="font-size:0.72rem;color:#9AA0A6;margin-bottom:10px">'
            f'<span style="color:{cov_color};font-weight:600">{cov_pct:.0f}%</span>'
            f' mastered · {cov_done}/{cov_total} topics at ≥50%</div>',
            unsafe_allow_html=True
        )
        for t in topics:
            state = t["state"] or "UNVISITED"
            score = t["base_priority_score"] or 0.0
            ans = t["answers_ready"] or 0
            total = t["total_q"] or 0
            name = t["topic_id"].replace("_", " ").title()

            col_a, col_b, col_c, col_d, col_e = st.columns([4, 2, 1.2, 1.2, 1.2])
            with col_a:
                st.markdown(
                    f'{badge(state)} <span style="font-size:0.92rem;font-weight:500;margin-left:6px">{name}</span>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    progress_bar(ans, total or 1) +
                    f'<div style="font-size:0.68rem;color:#9AA0A6;margin-top:2px">{ans}/{total} answers ready</div>',
                    unsafe_allow_html=True
                )
            with col_b:
                st.markdown(
                    f'<div style="font-size:0.78rem;color:#9AA0A6;padding-top:4px">'
                    f'{t["pyq_count"] or 0} past questions · '
                    f'<strong style="color:#8AB4F8">{priority_label(score)}</strong>'
                    f'<span style="font-size:0.65rem;color:#555;display:block;margin-top:2px">'
                    f'Priority: exam frequency + recency + gap</span></div>',
                    unsafe_allow_html=True
                )
            with col_c:
                next_states = {
                    "UNVISITED": ("Begin Study",   "IN_STUDY"),
                    "FLAGGED":   ("Resume",         "IN_STUDY"),
                    "DECAYING":  ("Resume",         "IN_STUDY"),
                    "IN_STUDY":  ("Mark Partial",   "PARTIAL"),
                    "PARTIAL":   ("Mark Verified",  "VERIFIED"),
                    "VERIFIED":  ("Verified ✓",     "VERIFIED"),
                }
                btn_label, next_state = next_states.get(state, ("Begin Study", "IN_STUDY"))
                if st.button(btn_label, key=f"adv_{paper_id}_{t['topic_id']}", use_container_width=True,
                             disabled=(state == "VERIFIED")):
                    set_topic_state(conn, t["topic_id"], next_state, "ui_advance")
                    st.rerun()
            with col_d:
                if st.button("Quick Verify", key=f"ver_{paper_id}_{t['topic_id']}", use_container_width=True,
                             disabled=(state == "VERIFIED"),
                             help="Skip ahead — mark this topic as fully verified from any state"):
                    set_topic_state(conn, t["topic_id"], "VERIFIED", "ui_verify")
                    st.rerun()
            with col_e:
                if st.button("Reset", key=f"rst_{paper_id}_{t['topic_id']}", use_container_width=True,
                             help="Reset to Not Started — clears all progress for this topic"):
                    set_topic_state(conn, t["topic_id"], "UNVISITED", "ui_reset")
                    st.rerun()

# ── Summary ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.divider()
st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

STATE_ORDER = ["UNVISITED", "IN_STUDY", "FLAGGED", "PARTIAL", "VERIFIED", "DECAYING"]
state_counts = {}
for t in all_topics:
    s = t["state"] or "UNVISITED"
    state_counts[s] = state_counts.get(s, 0) + 1

scols = st.columns(6)
STATE_COLORS = {
    "UNVISITED": "#9AA0A6", "IN_STUDY": "#FDD663", "FLAGGED": "#8AB4F8",
    "PARTIAL": "#81C995", "VERIFIED": "#81C995", "DECAYING": "#F28B82",
}
STATE_EMOJI = {"UNVISITED": "○", "IN_STUDY": "◑", "FLAGGED": "⚑",
               "PARTIAL": "◕", "VERIFIED": "✓", "DECAYING": "↓"}
for col, s in zip(scols, STATE_ORDER):
    cnt = state_counts.get(s, 0)
    color = STATE_COLORS[s]
    with col:
        st.markdown(f"""<div class="gem-card" style="text-align:center;border-color:{color}33">
            <div style="font-size:1.8rem;font-weight:700;color:{color}">{cnt}</div>
            <div style="font-size:0.68rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">{STATE_EMOJI[s]} {_STATE_DISPLAY.get(s, s)}</div>
        </div>""", unsafe_allow_html=True)

conn.close()
