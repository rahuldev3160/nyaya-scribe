"""RBI Prep blueprint — /rbi/prep"""
import json
import logging
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, g, redirect, render_template, request, session, url_for
from auth import login_required
from db import get_user_id, log_event, track_page_time

rbi_prep_bp = Blueprint("rbi_prep", __name__)

RBI_DATE = "2026-06-14"
_DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"


# ── DB lifecycle ───────────────────────────────────────────────────────────────

@rbi_prep_bp.before_request
def open_rbi_db():
    if not _DB_PATH.exists():
        g.rbi_conn = None
        return
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    g.rbi_conn = conn


@rbi_prep_bp.teardown_request
def close_rbi_db(exc):
    conn = g.pop("rbi_conn", None)
    if conn:
        conn.close()


# ── Countdown helper ───────────────────────────────────────────────────────────

def days_to_rbi() -> int:
    return (datetime.strptime(RBI_DATE, "%Y-%m-%d").date() - datetime.today().date()).days


# ── DB query helpers ───────────────────────────────────────────────────────────

def _answered_ids(conn: sqlite3.Connection) -> set:
    uid = get_user_id()
    rows = conn.execute(
        "SELECT DISTINCT question_id FROM rbi_attempts WHERE user_id=?", (uid,)
    ).fetchall()
    return {r[0] for r in rows}


def get_smart_questions(conn: sqlite3.Connection, n: int = 10) -> list:
    """Layer 1: highest flag_impact topics → unanswered questions first."""
    uid = get_user_id()
    answered = _answered_ids(conn)
    rows = conn.execute("""
        SELECT q.id, q.question, q.option_a, q.option_b, q.option_c, q.option_d,
               q.correct_option, q.explanation, q.topic, q.subject, q.difficulty,
               q.is_trap, q.priority_weight,
               COALESCE(m.flag_impact, tw.base_weight, 0.05) AS topic_priority
        FROM rbi_questions q
        LEFT JOIN rbi_topic_mastery m ON q.topic = m.topic AND m.user_id = ?
        LEFT JOIN rbi_topic_weights tw ON q.topic = tw.topic
        WHERE q.tier = 1
        ORDER BY topic_priority DESC, q.priority_weight DESC
    """, (uid,)).fetchall()

    unanswered = [dict(r) for r in rows if r["id"] not in answered]
    seen_answered = [dict(r) for r in rows if r["id"] in answered]
    result = unanswered[:n]
    if len(result) < n:
        result += seen_answered[:n - len(result)]
    return result


def get_filtered_questions(conn: sqlite3.Connection, filters: dict, n: int = 10) -> list:
    """Layer 3: user-directed filter override."""
    clauses = ["tier = 1"]
    params: list = []
    if filters.get("subject") and filters["subject"] != "all":
        clauses.append("subject = ?")
        params.append(filters["subject"])
    if filters.get("topic") and filters["topic"] != "all":
        clauses.append("topic = ?")
        params.append(filters["topic"])
    if filters.get("difficulty") and filters["difficulty"] != "all":
        clauses.append("difficulty = ?")
        params.append(filters["difficulty"])
    if filters.get("is_trap"):
        clauses.append("is_trap = 1")
    if filters.get("is_recent"):
        clauses.append("is_recent_dev = 1")

    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT id, question, option_a, option_b, option_c, option_d, "
        f"correct_option, explanation, topic, subject, difficulty, is_trap "
        f"FROM rbi_questions WHERE {where} "
        f"ORDER BY priority_weight DESC LIMIT ?",
        (*params, n),
    ).fetchall()
    return [dict(r) for r in rows]


def save_attempt(conn: sqlite3.Connection, question_id: str, answer_given: str,
                 is_correct: bool, session_id: str, topic: str, subject: str) -> None:
    """Save attempt + update mastery."""
    uid = get_user_id()
    try:
        with conn:
            conn.execute(
                "INSERT INTO rbi_attempts (user_id, question_id, answer_given, is_correct, session_id) "
                "VALUES (?,?,?,?,?)",
                (uid, question_id, answer_given, int(is_correct), session_id),
            )
            _update_mastery(conn, topic, subject, is_correct)
        try:
            log_event("drill_attempt", entity_type="rbi_topic", entity_id=topic,
                      exam_id="rbi_depr_2026",
                      payload={"is_correct": int(is_correct), "question_id": question_id,
                               "session_id": session_id})
        except Exception:
            pass
    except Exception as exc:
        logging.exception("rbi_attempts insert failed: %s", exc)


def _update_mastery(conn: sqlite3.Connection, topic: str, subject: str, is_correct: bool) -> None:
    """INSERT OR REPLACE mastery row."""
    uid = get_user_id()
    existing = conn.execute(
        "SELECT attempts, correct FROM rbi_topic_mastery WHERE user_id=? AND topic=?",
        (uid, topic),
    ).fetchone()

    new_attempts = (existing["attempts"] if existing else 0) + 1
    new_correct = (existing["correct"] if existing else 0) + (1 if is_correct else 0)
    mastery = new_correct / new_attempts

    total_q = conn.execute(
        "SELECT COUNT(*) FROM rbi_questions WHERE topic=?", (topic,)
    ).fetchone()[0] or 1
    attempted_q = conn.execute(
        "SELECT COUNT(DISTINCT question_id) FROM rbi_attempts "
        "WHERE user_id=? AND question_id IN (SELECT id FROM rbi_questions WHERE topic=?)",
        (uid, topic),
    ).fetchone()[0]

    coverage = attempted_q / total_q
    bw_row = conn.execute("SELECT base_weight FROM rbi_topic_weights WHERE topic=?", (topic,)).fetchone()
    bw = bw_row[0] if bw_row else 0.05
    flag_impact = bw * (1.0 - coverage)
    gap_state = "VERIFIED" if mastery >= 0.75 else "FLAGGED" if mastery < 0.45 else "IN_STUDY"

    conn.execute("""
        INSERT OR REPLACE INTO rbi_topic_mastery
        (user_id, topic, subject, attempts, correct, mastery_score, coverage_pct, flag_impact, gap_state, last_updated)
        VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))
    """, (uid, topic, subject, new_attempts, new_correct, mastery, coverage, flag_impact, gap_state))


def get_progress_data(conn: sqlite3.Connection) -> dict:
    """Compute formula readiness, true readiness, and top gaps."""
    uid = get_user_id()
    tw_rows = conn.execute(
        "SELECT topic, subject, base_weight FROM rbi_topic_weights"
    ).fetchall()
    weights = {r["topic"]: r["base_weight"] for r in tw_rows}
    topic_subjects = {r["topic"]: r["subject"] for r in tw_rows}

    mastery_rows = conn.execute(
        "SELECT topic, subject, attempts, mastery_score, coverage_pct, flag_impact, gap_state "
        "FROM rbi_topic_mastery WHERE user_id=?", (uid,)
    ).fetchall()

    total_weight = sum(weights.values()) or 1.0
    formula_score = 0.0
    true_penalty = 0.0
    gaps = []

    mastery_map = {r["topic"]: dict(r) for r in mastery_rows}

    for topic, bw in weights.items():
        m = mastery_map.get(topic)
        coverage = m["coverage_pct"] if m else 0.0
        mastery = m["mastery_score"] if m else 0.0

        formula_score += mastery * bw
        if coverage < 0.5:
            true_penalty += bw * (0.5 - coverage)
            gaps.append({
                "topic": topic,
                "subject": topic_subjects.get(topic, "other"),
                "coverage_pct": coverage,
                "flag_impact": bw * (1.0 - coverage),
            })

    formula_score = formula_score / total_weight
    true_readiness = max(0.0, formula_score - true_penalty / total_weight)
    gaps.sort(key=lambda g: g["flag_impact"], reverse=True)

    by_subject: dict = {}
    for topic, bw in weights.items():
        m = mastery_map.get(topic)
        subj = topic_subjects.get(topic, "other")
        if subj not in by_subject:
            by_subject[subj] = {"weight": 0.0, "weighted_cov": 0.0, "attempts": 0}
        cov = m["coverage_pct"] if m else 0.0
        att = m["attempts"] if m else 0
        by_subject[subj]["weight"] += bw
        by_subject[subj]["weighted_cov"] += bw * cov
        by_subject[subj]["attempts"] += att

    subject_coverage = {
        s: d["weighted_cov"] / d["weight"] if d["weight"] > 0 else 0.0
        for s, d in by_subject.items()
    }

    return {
        "formula_score": formula_score,
        "true_readiness": true_readiness,
        "gaps": gaps[:10],
        "subject_coverage": subject_coverage,
        "total_attempts": conn.execute(
            "SELECT COUNT(*) FROM rbi_attempts WHERE user_id=?", (uid,)
        ).fetchone()[0],
    }


# ── Tier-2 bucket metadata (label + icon per topic) ───────────────────────────
# Canonical display order matches the old BUCKETS dict order.
_BUCKET_META = {
    "rbi_instruments":    {"label": "RBI Instruments & Liquidity",        "icon": "⚙"},
    "banking_regulation": {"label": "Banking Regulation & NPA",           "icon": "🏛"},
    "payments_inclusion": {"label": "Payment Systems & Infra",             "icon": "💳"},
    "schemes_indices":    {"label": "Financial Inclusion & PSL",           "icon": "🤝"},
    "fiscal_data":        {"label": "Budget & Fiscal Framework",           "icon": "📋"},
    "india_macro_data":   {"label": "Indian Economy Structure",            "icon": "🇮🇳"},
    "external_sector":    {"label": "External Sector & BoP",               "icon": "🌐"},
    "nbfc_regulation":    {"label": "NBFC & Regulatory Framework",         "icon": "🏢"},
    "intl_finance":       {"label": "International Finance & Institutions", "icon": "🏛"},
}
_BUCKET_ORDER = list(_BUCKET_META.keys())


def _load_buckets(conn: sqlite3.Connection) -> dict:
    """Build the buckets dict from rbi_questions (tier=2), keyed by topic."""
    _opt_labels = ["A) ", "B) ", "C) ", "D) "]
    _opt_cols = ["option_a", "option_b", "option_c", "option_d"]
    rows = conn.execute(
        "SELECT id, topic, question, "
        "option_a, option_b, option_c, option_d, correct_option, explanation "
        "FROM rbi_questions WHERE tier=2 ORDER BY created_at"
    ).fetchall()

    buckets: dict = {}
    for row in rows:
        topic = row["topic"]
        if topic not in buckets:
            meta = _BUCKET_META.get(topic, {"label": topic, "icon": "📝"})
            buckets[topic] = {"label": meta["label"], "icon": meta["icon"], "qs": []}
        opts = [_opt_labels[i] + (row[_opt_cols[i]] or "") for i in range(4)]
        letter = (row["correct_option"] or "").strip().upper()
        letter_idx = {"A": 0, "B": 1, "C": 2, "D": 3}.get(letter, 0)
        correct_full = opts[letter_idx] if letter_idx < len(opts) else opts[0]
        buckets[topic]["qs"].append({
            "id": row["id"],
            "q": row["question"],
            "opts": opts,
            "correct": correct_full,
            "correct_option": letter,
            "exp": row["explanation"] or "",
        })

    ordered: dict = {}
    for key in _BUCKET_ORDER:
        if key in buckets:
            ordered[key] = buckets[key]
    for key in buckets:
        if key not in ordered:
            ordered[key] = buckets[key]
    return ordered


def _load_key_sections(conn: sqlite3.Connection) -> list:
    """Build key_sections list from rbi_key_data, grouped by section."""
    raw = conn.execute(
        "SELECT section, section_color, item_name, item_value, item_note, needs_verify "
        "FROM rbi_key_data ORDER BY section_sort, sort_order"
    ).fetchall()
    key_sections = []
    seen: dict = {}
    for row in raw:
        sec = row["section"]
        if sec not in seen:
            seen[sec] = {"label": sec, "color": row["section_color"], "rows": []}
            key_sections.append(seen[sec])
        seen[sec]["rows"].append((
            row["item_name"], row["item_value"], row["item_note"], bool(row["needs_verify"])
        ))
    return key_sections


# ── Routes ─────────────────────────────────────────────────────────────────────

@rbi_prep_bp.route("/rbi/prep")
@login_required
def prep():
    tab = request.args.get("tab", "key_data")
    if tab not in ("key_data", "phase1_drill", "tier2_quiz", "progress"):
        tab = "key_data"

    conn = g.rbi_conn

    buckets = _load_buckets(conn) if conn else {}
    bucket_keys = list(buckets.keys())
    bucket_key = request.args.get("bucket", bucket_keys[0] if bucket_keys else "")
    if bucket_key not in buckets:
        bucket_key = bucket_keys[0] if bucket_keys else ""

    result_mode = request.args.get("result", "0") == "1"
    drill_mode = request.args.get("mode", session.get("rbi_drill_mode", "smart"))
    if drill_mode not in ("smart", "filter"):
        drill_mode = "smart"
    session["rbi_drill_mode"] = drill_mode

    # ── Phase 1 drill setup data ───────────────────────────────────
    t1_count = 0
    subjects = []
    topics_for_subject = []
    sel_subj = "all"
    # topic param from dashboard redirect — look up its subject to pre-populate filter
    preselect_topic = request.args.get("topic", "")
    if conn:
        try:
            t1_count = conn.execute(
                "SELECT COUNT(*) FROM rbi_questions WHERE tier=1"
            ).fetchone()[0]
            if t1_count > 0:
                subjects = ["all"] + sorted({
                    r[0] for r in conn.execute(
                        "SELECT DISTINCT subject FROM rbi_questions WHERE tier=1"
                    ).fetchall()
                })
                sel_subj = request.args.get("subject", "all")
                # If a topic is pre-selected but no subject given, infer the subject
                if preselect_topic and preselect_topic != "all" and sel_subj == "all":
                    subj_row = conn.execute(
                        "SELECT subject FROM rbi_questions WHERE tier=1 AND topic=? LIMIT 1",
                        (preselect_topic,),
                    ).fetchone()
                    if subj_row:
                        sel_subj = subj_row[0]
                if sel_subj != "all" and sel_subj in subjects:
                    topics_for_subject = ["all"] + sorted({
                        r[0] for r in conn.execute(
                            "SELECT DISTINCT topic FROM rbi_questions WHERE tier=1 AND subject=?",
                            (sel_subj,)
                        ).fetchall()
                    })
                else:
                    topics_for_subject = ["all"] + sorted({
                        r[0] for r in conn.execute(
                            "SELECT DISTINCT topic FROM rbi_questions WHERE tier=1"
                        ).fetchall()
                    })
        except Exception:
            pass

    # ── Drill questions for active session ────────────────────────
    drill_questions = []
    drill_session_id = session.get("rbi_drill_session_id", "")
    if tab == "phase1_drill" and not result_mode and conn and t1_count > 0:
        n_qs = int(request.args.get("n", session.get("rbi_drill_n", 10)))
        session["rbi_drill_n"] = n_qs
        if drill_mode == "smart":
            if request.args.get("start") == "1":
                drill_questions = get_smart_questions(conn, n_qs)
                drill_session_id = str(uuid.uuid4())
                session["rbi_drill_session_id"] = drill_session_id
                session["rbi_drill_questions"] = drill_questions
            else:
                drill_questions = session.get("rbi_drill_questions", [])
        else:
            if request.args.get("start") == "1":
                filters = {
                    "subject": request.args.get("subject", "all"),
                    "topic": request.args.get("topic", "all"),
                    "difficulty": request.args.get("difficulty", "all"),
                    "is_trap": request.args.get("is_trap") == "1",
                    "is_recent": request.args.get("is_recent") == "1",
                }
                session["rbi_drill_filter"] = filters
                drill_questions = get_filtered_questions(conn, filters, n_qs)
                drill_session_id = str(uuid.uuid4())
                session["rbi_drill_session_id"] = drill_session_id
                session["rbi_drill_questions"] = drill_questions
            else:
                drill_questions = session.get("rbi_drill_questions", [])

    # ── Drill results ──────────────────────────────────────────────
    drill_results = []
    if tab == "phase1_drill" and result_mode:
        drill_results = session.get("rbi_drill_results", [])

    drill_error = session.pop("rbi_drill_error", None)

    # ── Tier 2 quiz state ──────────────────────────────────────────
    tier2_scores = session.get("rbi_tier2_scores", {})
    tier2_answers = session.get("rbi_tier2_answers", {})
    tier2_bucket = session.get("rbi_tier2_bucket", bucket_keys[0] if bucket_keys else "")
    if bucket_key != tier2_bucket and tab == "tier2_quiz":
        tier2_bucket = bucket_key
        session["rbi_tier2_bucket"] = bucket_key
        if not result_mode:
            session.pop("rbi_tier2_answers", None)

    # ── Progress data — always computed so JS tab-switch shows live data ──
    progress = None
    if conn:
        try:
            progress = get_progress_data(conn)
        except Exception:
            pass

    # ── Key data ──────────────────────────────────────────────────
    key_sections = []
    if conn:
        try:
            key_sections = _load_key_sections(conn)
        except Exception:
            pass

    # Track page visit
    try:
        track_page_time(g.conn, "RBI Prep")
    except Exception:
        pass

    d = days_to_rbi()
    d_color = "#F28B82" if d <= 5 else "#FDD663" if d <= 10 else "#81C995"

    return render_template(
        "rbi_prep.html",
        active_page="rbi_prep",
        # countdown
        days=d,
        days_color=d_color,
        # tabs
        tab=tab,
        result_mode=result_mode,
        # key data
        key_sections=key_sections,
        # phase 1 drill
        t1_count=t1_count,
        drill_mode=drill_mode,
        drill_questions=drill_questions,
        drill_session_id=drill_session_id,
        drill_results=drill_results,
        drill_error=drill_error,
        drill_n=session.get("rbi_drill_n", 10),
        drill_filter=session.get("rbi_drill_filter", {}),
        preselect_topic=preselect_topic,
        sel_subj=sel_subj,
        subjects=subjects,
        topics_for_subject=topics_for_subject,
        # tier 2
        bucket_key=bucket_key,
        buckets=buckets,
        bucket_keys=bucket_keys,
        tier2_scores=tier2_scores,
        tier2_answers=tier2_answers,
        # progress
        progress=progress,
        SUBJECT_LABELS={
            "macro": "Macroeconomics", "intl_econ": "International Economics",
            "growth": "Growth & Development", "micro": "Microeconomics",
            "pub_finance": "Public Finance", "quant": "Quantitative Methods",
            "env_econ": "Environmental Economics", "rbi_banking": "RBI / Banking",
            "indian_econ": "Indian Economy",
        },
    )


@rbi_prep_bp.route("/rbi/prep/tier2/submit", methods=["POST"])
@login_required
def tier2_submit():
    conn = g.rbi_conn
    buckets = _load_buckets(conn) if conn else {}
    bucket_keys = list(buckets.keys())

    bucket_key = request.form.get("bucket_key", bucket_keys[0] if bucket_keys else "")
    if bucket_key not in buckets:
        bucket_key = bucket_keys[0] if bucket_keys else ""

    bucket = buckets.get(bucket_key, {"qs": []})
    questions = bucket["qs"]

    answers = {}
    for q in questions:
        val = request.form.get(f"ans_{q['id']}", "")
        answers[q["id"]] = val

    correct_count = sum(
        1 for q in questions
        if answers.get(q["id"], "").strip() == q["correct"].strip()
    )

    scores = session.get("rbi_tier2_scores", {})
    scores[bucket_key] = {"correct": correct_count, "total": len(questions)}
    session["rbi_tier2_scores"] = scores
    session["rbi_tier2_answers"] = answers
    session["rbi_tier2_bucket"] = bucket_key

    return redirect(url_for("rbi_prep.prep", tab="tier2_quiz", bucket=bucket_key, result=1))


@rbi_prep_bp.route("/rbi/prep/drill/submit", methods=["POST"])
@login_required
def drill_submit():
    sid = request.form.get("session_id", "")
    conn = g.rbi_conn
    if not conn:
        return redirect(url_for("rbi_prep.prep", tab="phase1_drill"))

    questions = session.get("rbi_drill_questions", [])
    if not questions:
        return redirect(url_for("rbi_prep.prep", tab="phase1_drill"))

    # Build answer map first so we can validate before writing anything
    raw_answers = {str(q["id"]): request.form.get(f"q_{str(q['id'])}", "") for q in questions}
    unanswered = [i + 1 for i, q in enumerate(questions) if not raw_answers.get(str(q["id"]))]
    if unanswered:
        session["rbi_drill_error"] = f"Please answer Q{', Q'.join(str(n) for n in unanswered)} before submitting."
        return redirect(url_for("rbi_prep.prep", tab="phase1_drill"))

    results = []
    for q in questions:
        qid = str(q["id"])
        chosen_full = raw_answers[qid]
        _opt_map = {
            q.get("option_a", "").strip(): "A",
            q.get("option_b", "").strip(): "B",
            q.get("option_c", "").strip(): "C",
            q.get("option_d", "").strip(): "D",
        }
        letter = _opt_map.get(chosen_full.strip(), "")
        if not letter:
            continue
        is_correct = letter == q.get("correct_option", "")

        save_attempt(conn, qid, letter, is_correct, sid,
                     q.get("topic", ""), q.get("subject", ""))

        correct_key = f"option_{q['correct_option'].lower()}" if q.get("correct_option") else ""
        results.append({
            "question": q["question"],
            "answer_given": chosen_full,
            "correct_option": q.get("correct_option", ""),
            "correct_option_full": q.get(correct_key, "") if correct_key else "",
            "options": [q.get("option_a", ""), q.get("option_b", ""),
                        q.get("option_c", ""), q.get("option_d", "")],
            "explanation": q.get("explanation", ""),
            "is_correct": is_correct,
        })

    session["rbi_drill_results"] = results
    session["rbi_drill_mode"] = session.get("rbi_drill_mode", "smart")
    session["rbi_drill_questions"] = []

    return redirect(url_for("rbi_prep.prep", tab="phase1_drill", result=1))


@rbi_prep_bp.route("/rbi/prep/drill/questions")
@login_required
def drill_questions_redirect():
    mode = request.args.get("mode", "smart")
    n = request.args.get("n", "10")
    subject = request.args.get("subject", "all")
    topic = request.args.get("topic", "all")
    difficulty = request.args.get("difficulty", "all")
    return redirect(url_for("rbi_prep.prep", tab="phase1_drill",
                             mode=mode, n=n, subject=subject,
                             topic=topic, difficulty=difficulty))
