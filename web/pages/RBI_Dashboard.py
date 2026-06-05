"""RBI DEPR 2026 — Prep Dashboard."""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from auth import require_user
from db import get_conn as _get_ies_conn, get_user_id, track_page_time
from styles import apply_theme, progress_bar

st.set_page_config(page_title="RBI Dashboard · DEPR 2026", layout="wide", page_icon="🏦")
apply_theme()

_ies_conn = _get_ies_conn()
user_id = require_user(_ies_conn)
track_page_time(_ies_conn, "RBI Dashboard")
_ies_conn.close()

RBI_DATE = "2026-06-14"
_DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"


def _days_left() -> int:
    return (datetime.strptime(RBI_DATE, "%Y-%m-%d").date() - datetime.today().date()).days


def _get_conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c


if not _DB_PATH.exists():
    st.error("rbi.db not found. Run `python3 scripts/rbi/00_init_rbi_db.py` first.")
    st.stop()

conn = _get_conn()

# ── Load metrics ──────────────────────────────────────────────────────────────

d = _days_left()

total_p1 = conn.execute("SELECT COUNT(*) FROM rbi_questions WHERE tier=1").fetchone()[0]
agg = conn.execute(
    "SELECT COUNT(*), SUM(is_correct) FROM rbi_attempts WHERE user_id=?", (user_id,)
).fetchone()
total_attempts = agg[0] or 0
total_correct = agg[1] or 0
answered_p1 = conn.execute(
    "SELECT COUNT(DISTINCT question_id) FROM rbi_attempts WHERE user_id=?", (user_id,)
).fetchone()[0]
accuracy = total_correct / total_attempts if total_attempts > 0 else 0.0

weights = {r["topic"]: r["base_weight"]
           for r in conn.execute("SELECT topic, base_weight FROM rbi_topic_weights").fetchall()}
mastery_rows = conn.execute(
    "SELECT topic, subject, mastery_score, coverage_pct, flag_impact, gap_state "
    "FROM rbi_topic_mastery WHERE user_id=?", (user_id,)
).fetchall()
total_weight = sum(weights.values()) or 1.0
mastery_map = {m["topic"]: dict(m) for m in mastery_rows}
formula_score = sum(
    mastery_map.get(t, {}).get("mastery_score", 0.0) * bw for t, bw in weights.items()
) / total_weight

# Gap-adjusted readiness
true_penalty = sum(
    bw * max(0.0, 0.5 - mastery_map.get(t, {}).get("coverage_pct", 0.0))
    for t, bw in weights.items()
)
true_readiness = max(0.0, formula_score - true_penalty / total_weight)

well_covered = sum(
    1 for t in weights if mastery_map.get(t, {}).get("coverage_pct", 0.0) >= 0.5
)

gaps = [
    {
        "topic": t,
        "subject": mastery_map.get(t, {}).get("subject", ""),
        "coverage_pct": mastery_map.get(t, {}).get("coverage_pct", 0.0),
        "impact": bw * (1.0 - mastery_map.get(t, {}).get("coverage_pct", 0.0)),
    }
    for t, bw in weights.items()
    if mastery_map.get(t, {}).get("coverage_pct", 0.0) < 0.5
]
gaps.sort(key=lambda g: g["impact"], reverse=True)

# Subject coverage (weighted)
subject_data: dict = {}
for t, bw in weights.items():
    subj_row = conn.execute("SELECT subject FROM rbi_topic_weights WHERE topic=?", (t,)).fetchone()
    subj = subj_row[0] if subj_row else "other"
    if subj not in subject_data:
        subject_data[subj] = {"weight": 0.0, "weighted_cov": 0.0}
    cov = mastery_map.get(t, {}).get("coverage_pct", 0.0)
    subject_data[subj]["weight"] += bw
    subject_data[subj]["weighted_cov"] += bw * cov
subject_coverage = {
    s: d["weighted_cov"] / d["weight"] if d["weight"] > 0 else 0.0
    for s, d in subject_data.items()
}

# ── Header ────────────────────────────────────────────────────────────────────

day_color = "#F28B82" if d <= 7 else "#FDD663" if d <= 14 else "#8AB4F8"
st.markdown("## 🏦 RBI DEPR 2026 Dashboard")
st.markdown(
    '<span style="color:#9AA0A6;font-size:0.85rem;">'
    "Exam 14th June 2026 · Phase 1: Economics MCQ (100m) + English (100m)"
    "</span>",
    unsafe_allow_html=True,
)

# ── Metrics row ───────────────────────────────────────────────────────────────

m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1:
    st.markdown(
        f'<div class="gem-card" style="text-align:center;border-color:{day_color}33">'
        f'<div style="font-size:2rem;font-weight:700;color:{day_color}">{d}</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Days Left</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with m2:
    p1_pct = int(100 * answered_p1 / total_p1) if total_p1 else 0
    st.markdown(
        f'<div class="gem-card" style="text-align:center">'
        f'<div style="font-size:2rem;font-weight:700;color:#8AB4F8">{answered_p1}</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">P1 Qs Answered</div>'
        f'<div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">{p1_pct}% of {total_p1}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with m3:
    acc_color = "#81C995" if accuracy >= 0.75 else "#FDD663" if accuracy >= 0.5 else "#F28B82"
    st.markdown(
        f'<div class="gem-card" style="text-align:center;border-color:{acc_color}33">'
        f'<div style="font-size:2rem;font-weight:700;color:{acc_color}">{int(accuracy * 100)}%</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">P1 Accuracy</div>'
        f'<div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">{total_correct}/{total_attempts} attempts</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with m4:
    r_color = "#F28B82" if formula_score < 0.2 else "#FDD663" if formula_score < 0.5 else "#81C995"
    st.markdown(
        f'<div class="gem-card" style="text-align:center;border-color:{r_color}33">'
        f'<div style="font-size:2rem;font-weight:700;color:{r_color}">{int(formula_score * 100)}%</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Mastery Score</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with m5:
    tr_color = "#F28B82" if true_readiness < 0.2 else "#FDD663" if true_readiness < 0.5 else "#81C995"
    st.markdown(
        f'<div class="gem-card" style="text-align:center;border-color:{tr_color}33">'
        f'<div style="font-size:2rem;font-weight:700;color:{tr_color}">{int(true_readiness * 100)}%</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Exam Readiness</div>'
        f'<div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">gap-adjusted</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
with m6:
    st.markdown(
        f'<div class="gem-card" style="text-align:center">'
        f'<div style="font-size:2rem;font-weight:700;color:#81C995">{well_covered}</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Topics ≥50% Done</div>'
        f'<div style="font-size:0.7rem;color:#9AA0A6;margin-top:2px">of {len(weights)} topics</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

if d <= 7:
    st.markdown(
        '<div style="background:#F28B8222;border:1px solid #F28B82;border-radius:8px;padding:10px 16px;margin-bottom:12px;">'
        '<span style="color:#F28B82;font-weight:700;font-size:1rem;">⚡ FINAL STRETCH</span>'
        '<span style="color:#9AA0A6;font-size:0.85rem;margin-left:8px;">≤7 days to RBI DEPR — focus on top gaps only.</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Quick action ──────────────────────────────────────────────────────────────

_qc, _ = st.columns([1, 3])
with _qc:
    st.page_link("pages/6_RBI_Prep.py", label="▶ Go to Phase 1 Drill & Tier 2 Quiz", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)
st.divider()

# ── Subject Coverage ──────────────────────────────────────────────────────────

SUBJECT_LABELS = {
    "macro": "Macroeconomics", "intl_econ": "International Economics",
    "growth": "Growth & Development", "micro": "Microeconomics",
    "pub_finance": "Public Finance", "quant": "Quantitative Methods",
    "env_econ": "Environmental Economics", "rbi_banking": "RBI / Banking",
    "indian_econ": "Indian Economy",
}

st.markdown('<div class="section-header">Subject Coverage</div>', unsafe_allow_html=True)
sc_left, sc_right = st.columns(2)
items = sorted(subject_coverage.items(), key=lambda x: x[1])
half = len(items) // 2 + len(items) % 2
for col, chunk in [(sc_left, items[:half]), (sc_right, items[half:])]:
    with col:
        for subj, cov in chunk:
            label = SUBJECT_LABELS.get(subj, subj.replace("_", " ").title())
            bar_color = "#81C995" if cov >= 0.7 else "#FDD663" if cov >= 0.4 else "#F28B82"
            st.markdown(
                progress_bar(int(cov * 100), 100) +
                f'<div style="display:flex;justify-content:space-between;font-size:0.75rem;margin-top:2px;margin-bottom:8px">'
                f'<span style="color:#9AA0A6">{label}</span>'
                f'<span style="color:{bar_color};font-weight:600">{int(cov * 100)}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.divider()

# ── Gap Alerts ────────────────────────────────────────────────────────────────

st.markdown('<div class="section-header">Top Gaps — Drill These First</div>', unsafe_allow_html=True)

if not gaps:
    st.success("All topics ≥50% covered — great shape!", icon="✅")
else:
    for g in gaps[:8]:
        cov = g["coverage_pct"]
        gcol = "#F28B82" if cov < 0.2 else "#FDD663"
        subj_label = SUBJECT_LABELS.get(g["subject"], g["subject"].replace("_", " ").title())
        topic_label = g["topic"].replace("_", " ").title()
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 12px;background:rgba(255,255,255,0.03);border-left:3px solid {gcol};'
            f'border-radius:4px;margin-bottom:6px">'
            f'<div>'
            f'<span style="font-size:0.84rem;font-weight:600;color:#E8EAED">{topic_label}</span>'
            f'<span style="font-size:0.72rem;color:#9AA0A6;margin-left:8px">{subj_label}</span>'
            f'</div>'
            f'<div style="text-align:right">'
            f'<span style="font-size:0.82rem;color:{gcol};font-weight:600">{int(cov * 100)}% covered</span>'
            f'<span style="font-size:0.70rem;color:#9AA0A6;display:block">impact {g["impact"]:.3f}</span>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.caption("Impact = topic weight × uncovered fraction. Higher = more exam marks at risk.")

conn.close()
