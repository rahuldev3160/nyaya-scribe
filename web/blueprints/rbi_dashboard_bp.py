"""RBI Dashboard blueprint — GET /rbi"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, redirect, render_template, request, url_for
from auth import login_required
from db import get_conn, track_page_time

rbi_dashboard_bp = Blueprint("rbi_dashboard", __name__)

RBI_DATE = "2026-06-14"
_RBI_DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"

SUBJECT_LABELS = {
    "macro": "Macroeconomics",
    "intl_econ": "International Economics",
    "growth": "Growth & Development",
    "micro": "Microeconomics",
    "pub_finance": "Public Finance",
    "quant": "Quantitative Methods",
    "env_econ": "Environmental Economics",
    "rbi_banking": "RBI / Banking",
    "indian_econ": "Indian Economy",
}


@rbi_dashboard_bp.before_request
def open_rbi():
    if not _RBI_DB_PATH.exists():
        g.rbi_conn = None
        return
    c = sqlite3.connect(str(_RBI_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    g.rbi_conn = c


@rbi_dashboard_bp.teardown_request
def close_rbi(exc):
    c = g.pop("rbi_conn", None)
    if c:
        c.close()


@rbi_dashboard_bp.route("/rbi")
@login_required
def rbi_dashboard():
    ies_conn = get_conn()
    track_page_time(ies_conn, "RBI Dashboard")
    user_id = g.user_id

    if not g.rbi_conn:
        return render_template("rbi_dashboard.html", active_page="rbi_dashboard", db_missing=True)

    conn = g.rbi_conn

    d = (datetime.strptime(RBI_DATE, "%Y-%m-%d").date() - datetime.today().date()).days

    total_p1 = conn.execute(
        "SELECT COUNT(*) FROM rbi_questions WHERE tier=1"
    ).fetchone()[0]

    agg = conn.execute(
        "SELECT COUNT(*), SUM(is_correct) FROM rbi_attempts WHERE user_id=?", (user_id,)
    ).fetchone()
    total_attempts = agg[0] or 0
    total_correct = int(agg[1] or 0)

    answered_p1 = conn.execute(
        "SELECT COUNT(DISTINCT question_id) FROM rbi_attempts WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    accuracy = total_correct / total_attempts if total_attempts > 0 else 0.0
    p1_pct = round(100 * answered_p1 / total_p1) if total_p1 > 0 else 0

    tw_rows = conn.execute(
        "SELECT topic, subject, base_weight FROM rbi_topic_weights"
    ).fetchall()
    weights = {r["topic"]: r["base_weight"] for r in tw_rows}
    topic_subjects = {r["topic"]: r["subject"] for r in tw_rows}

    mastery_rows = conn.execute(
        "SELECT topic, subject, mastery_score, coverage_pct, flag_impact, gap_state "
        "FROM rbi_topic_mastery WHERE user_id=?",
        (user_id,),
    ).fetchall()

    total_weight = sum(weights.values()) or 1.0
    mastery_map = {m["topic"]: dict(m) for m in mastery_rows}

    formula_score = sum(
        mastery_map.get(t, {}).get("mastery_score", 0.0) * bw
        for t, bw in weights.items()
    ) / total_weight

    true_penalty = sum(
        bw * max(0.0, 0.5 - mastery_map.get(t, {}).get("coverage_pct", 0.0))
        for t, bw in weights.items()
    )
    true_readiness = max(0.0, formula_score - true_penalty / total_weight)

    well_covered = sum(
        1 for t in weights
        if mastery_map.get(t, {}).get("coverage_pct", 0.0) >= 0.5
    )

    raw_gaps = [
        {
            "topic": t,
            "subject": topic_subjects.get(t, "other"),
            "coverage_pct": mastery_map.get(t, {}).get("coverage_pct", 0.0),
            "impact": bw * (1.0 - mastery_map.get(t, {}).get("coverage_pct", 0.0)),
        }
        for t, bw in weights.items()
        if mastery_map.get(t, {}).get("coverage_pct", 0.0) < 0.5
    ]
    raw_gaps.sort(key=lambda x: x["impact"], reverse=True)

    subject_data: dict = {}
    for t, bw in weights.items():
        subj = topic_subjects.get(t, "other")
        if subj not in subject_data:
            subject_data[subj] = {"weight": 0.0, "weighted_cov": 0.0}
        cov = mastery_map.get(t, {}).get("coverage_pct", 0.0)
        subject_data[subj]["weight"] += bw
        subject_data[subj]["weighted_cov"] += bw * cov

    subject_coverage = {
        s: v["weighted_cov"] / v["weight"] if v["weight"] > 0 else 0.0
        for s, v in subject_data.items()
    }

    def _bar_color(cov: float) -> str:
        if cov >= 0.70:
            return "#81C995"
        if cov >= 0.40:
            return "#FDD663"
        return "#F28B82"

    subject_coverage_items = sorted(subject_coverage.items(), key=lambda x: x[1])
    sc_tuples = [
        (sk, cov, SUBJECT_LABELS.get(sk, sk), _bar_color(cov))
        for sk, cov in subject_coverage_items
    ]
    half = len(sc_tuples) // 2 + len(sc_tuples) % 2
    sc_left = sc_tuples[:half]
    sc_right = sc_tuples[half:]

    gaps = [
        {
            "topic": g_["topic"],
            "subject": g_["subject"],
            "coverage_pct": g_["coverage_pct"],
            "impact": g_["impact"],
            "gcol": "#F28B82" if g_["coverage_pct"] < 0.20 else "#FDD663",
            "topic_label": g_["topic"].replace("_", " ").title(),
            "subj_label": SUBJECT_LABELS.get(g_["subject"], g_["subject"]),
        }
        for g_ in raw_gaps[:8]
    ]

    day_color = "#F28B82" if d <= 7 else "#FDD663" if d <= 14 else "#8AB4F8"
    acc_color = "#81C995" if accuracy >= 0.75 else "#FDD663" if accuracy >= 0.50 else "#F28B82"

    def _score_color(v: float) -> str:
        if v < 0.20:
            return "#F28B82"
        if v < 0.50:
            return "#FDD663"
        return "#81C995"

    r_color = _score_color(formula_score)
    tr_color = _score_color(true_readiness)

    return render_template(
        "rbi_dashboard.html",
        active_page="rbi_dashboard",
        days_left=d,
        day_color=day_color,
        total_p1=total_p1,
        answered_p1=answered_p1,
        p1_pct=p1_pct,
        accuracy=accuracy,
        acc_color=acc_color,
        total_attempts=total_attempts,
        total_correct=total_correct,
        formula_score=formula_score,
        r_color=r_color,
        true_readiness=true_readiness,
        tr_color=tr_color,
        well_covered=well_covered,
        total_topics=len(weights),
        final_stretch=(d <= 7),
        sc_left=sc_left,
        sc_right=sc_right,
        subject_labels=SUBJECT_LABELS,
        gaps=gaps,
    )


@rbi_dashboard_bp.route("/rbi/topics/<topic_name>/drill", methods=["POST"])
@login_required
def rbi_topic_drill(topic_name):
    """Redirect to the Phase 1 drill pre-filtered to the given topic."""
    return redirect(
        url_for("rbi_prep.prep", tab="phase1_drill", mode="filter", topic=topic_name)
    )
