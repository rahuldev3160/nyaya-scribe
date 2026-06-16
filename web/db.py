# IES-specific helpers — for RBI use rbi_db.py, for UPSC use upsc_db.py
"""Shared DB helpers — works in Flask request context and standalone scripts."""
import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

_PROMO = re.compile(
    r'Download the Ecoholics app.*?TOWARDS YOUR SUCCESS\.',
    re.DOTALL | re.IGNORECASE,
)


def clean_q(text: str) -> str:
    """Strip Ecoholics promotional text injected mid-question by PDF page breaks."""
    if not text:
        return text
    return ' '.join(_PROMO.sub('', text).split())


DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
EXAM_ID = "ies_2026"
USER_ID = os.environ.get("IES_USER_ID", "rahul")
def is_crunch_mode() -> bool:
    try:
        conn = _open_conn()
        row = conn.execute(
            "SELECT exam_date FROM exam_configurations WHERE exam_id='ies_2026'"
        ).fetchone()
        conn.close()
        exam_str = row[0] if row else "2026-06-19"
    except Exception:
        exam_str = "2026-06-19"
    exam = datetime.strptime(exam_str, "%Y-%m-%d").date()
    return (exam - datetime.today().date()).days <= 7


def get_user_id() -> str:
    """Return current user_id: Flask g.user_id in request context, env var for scripts."""
    try:
        from flask import g
        uid = getattr(g, "user_id", None)
        if uid:
            return uid
    except RuntimeError:
        pass  # Outside Flask application context (scripts)
    return USER_ID


def _open_conn() -> sqlite3.Connection:
    """Open a new SQLite connection. Used by app factory and scripts."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_conn() -> sqlite3.Connection:
    """Return the request-scoped connection (Flask) or open a new one (scripts).
    In Flask routes, teardown_appcontext closes the connection — do NOT close manually.
    In scripts, caller must close the returned connection."""
    try:
        from flask import g
        if hasattr(g, "conn") and g.conn:
            return g.conn
    except RuntimeError:
        pass  # Outside Flask application context
    return _open_conn()


_NYAYA_PATH = Path(__file__).parent.parent / "data" / "nyaya.db"


def _open_nyaya_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_NYAYA_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def get_nyaya_conn() -> sqlite3.Connection:
    try:
        from flask import g
        if hasattr(g, "nyaya_conn") and g.nyaya_conn:
            return g.nyaya_conn
    except RuntimeError:
        pass
    return _open_nyaya_conn()


def has_feature(user_id: str, gate_id: str) -> bool:
    """Return True if user can access a gated feature (tier + per-user override)."""
    try:
        nc = get_nyaya_conn()
        user = nc.execute(
            "SELECT subscription_tier FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        if not user:
            return False
        override = nc.execute(
            "SELECT 1 FROM user_feature_overrides"
            " WHERE user_id=? AND gate_id=?"
            " AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (user_id, gate_id),
        ).fetchone()
        if override:
            return True
        tier_col = "is_enabled_for_pro" if user["subscription_tier"] == "pro" else "is_enabled_for_free"
        gate = nc.execute(
            f"SELECT {tier_col} FROM feature_gates WHERE gate_id=?", (gate_id,)
        ).fetchone()
        return bool(gate and gate[0])
    except Exception:
        return True  # tables may not exist during migration; default allow


def get_monthly_usage(user_id: str, gate_id: str) -> int:
    """Return how many times user has used a quota-gated feature this calendar month."""
    try:
        nc = get_nyaya_conn()
        period = __import__("datetime").date.today().strftime("%Y-%m")
        row = nc.execute(
            "SELECT usage_count FROM user_feature_usage WHERE user_id=? AND gate_id=? AND period=?",
            (user_id, gate_id, period),
        ).fetchone()
        return row["usage_count"] if row else 0
    except Exception:
        return 0


def increment_feature_usage(user_id: str, gate_id: str) -> int:
    """Increment monthly usage counter; returns new count."""
    try:
        nc = get_nyaya_conn()
        period = __import__("datetime").date.today().strftime("%Y-%m")
        nc.execute(
            "INSERT INTO user_feature_usage (user_id, gate_id, period, usage_count, last_used_at)"
            " VALUES (?,?,?,1,datetime('now'))"
            " ON CONFLICT(user_id, gate_id, period) DO UPDATE SET"
            " usage_count=usage_count+1, last_used_at=datetime('now')",
            (user_id, gate_id, period),
        )
        nc.commit()
        row = nc.execute(
            "SELECT usage_count FROM user_feature_usage WHERE user_id=? AND gate_id=? AND period=?",
            (user_id, gate_id, period),
        ).fetchone()
        return row["usage_count"] if row else 1
    except Exception:
        return 1


def can_use_feature(user_id: str, gate_id: str) -> tuple[bool, str]:
    """Check feature access AND quota. Returns (allowed, reason).
    reason: 'ok' | 'not_enabled' | 'quota_exhausted'
    """
    if not has_feature(user_id, gate_id):
        return False, "not_enabled"
    try:
        nc = get_nyaya_conn()
        user = nc.execute(
            "SELECT subscription_tier FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
        tier = user["subscription_tier"] if user else "free"
        quota_col = "quota_pro" if tier == "pro" else "quota_free"
        gate = nc.execute(
            f"SELECT {quota_col} FROM feature_gates WHERE gate_id=?", (gate_id,)
        ).fetchone()
        quota = gate[0] if gate else None
        if quota is not None and get_monthly_usage(user_id, gate_id) >= quota:
            return False, "quota_exhausted"
    except Exception:
        pass
    return True, "ok"


def init_user(conn, user_id: str) -> None:
    """Seed default rows for a new user. No-op for existing users."""
    if conn.execute(
        "SELECT 1 FROM gap_states WHERE user_id=? AND exam_id=? LIMIT 1",
        (user_id, EXAM_ID),
    ).fetchone():
        return
    topics = conn.execute(
        "SELECT topic_id, paper_id FROM topics WHERE exam_id=? AND topic_level='topic'",
        (EXAM_ID,)
    ).fetchall()
    for t in topics:
        conn.execute(
            "INSERT OR IGNORE INTO gap_states (user_id, topic_id, exam_id, paper_id, state) VALUES (?,?,?,?,?)",
            (user_id, t["topic_id"], EXAM_ID, t["paper_id"], "UNVISITED")
        )
        conn.execute(
            "INSERT OR IGNORE INTO user_mastery (user_id, topic_id, exam_id) VALUES (?,?,?)",
            (user_id, t["topic_id"], EXAM_ID)
        )
        conn.execute(
            "INSERT OR IGNORE INTO topic_attempt_summary (user_id, topic_id, exam_id) VALUES (?,?,?)",
            (user_id, t["topic_id"], EXAM_ID)
        )
    for paper_id in ["ge_01", "ge_02", "ge_03", "ge_04"]:
        conn.execute(
            "INSERT OR IGNORE INTO user_paper_preferences (user_id, exam_id, paper_id) VALUES (?,?,?)",
            (user_id, EXAM_ID, paper_id)
        )
    conn.commit()


def _get_user_agent() -> str | None:
    try:
        from flask import request as flask_request
        return flask_request.user_agent.string or None
    except RuntimeError:
        return None


def log_event(event_type: str, entity_type: str | None = None,
              entity_id: str | None = None, exam_id: str | None = None,
              payload: dict | None = None) -> None:
    """Append one row to user_events in nyaya.db. Silent no-op on any error."""
    uid = get_user_id()
    _fallback = os.environ.get("IES_USER_ID", "rahul")
    if not uid or uid == _fallback:
        return
    try:
        from flask import session as flask_session
        session_id = flask_session.get("session_id") or uid
    except RuntimeError:
        session_id = "script"
    try:
        nc = get_nyaya_conn()
        nc.execute(
            """INSERT INTO user_events
               (user_id, session_id, event_type, entity_type, entity_id, exam_id, payload, user_agent)
               VALUES (?,?,?,?,?,?,?,?)""",
            (uid, session_id, event_type, entity_type, entity_id, exam_id,
             json.dumps(payload) if payload else None, _get_user_agent())
        )
        nc.commit()
    except Exception:
        pass


def track_page_time(conn, page_name: str, exam_id: str | None = None) -> None:
    uid = get_user_id()
    if not uid:
        return
    try:
        from flask import g as flask_g, session as flask_session, request as flask_request
        elapsed = int(time.time() - getattr(flask_g, "request_start", time.time()))
        session_id = flask_session.get("session_id") or uid
        ua = flask_request.user_agent.string or None
    except RuntimeError:
        elapsed = None
        session_id = uid
        ua = None
    payload = json.dumps({"duration_s": elapsed}) if elapsed is not None else None

    def _write():
        try:
            nc = _open_nyaya_conn()
            nc.execute(
                """INSERT INTO user_events
                   (user_id, session_id, event_type, entity_type, entity_id, exam_id, payload, user_agent)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (uid, session_id, "page_view", "page", page_name, exam_id, payload, ua),
            )
            nc.commit()
            nc.close()
        except Exception:
            pass

    threading.Thread(target=_write, daemon=True).start()


def get_study_path(conn, user_id: str) -> dict | None:
    """Return the user's AI-generated study path, or None if onboarding not done."""
    try:
        nc = get_nyaya_conn()
        row = nc.execute(
            "SELECT study_path, onboarding_completed FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if row and row["study_path"]:
            return json.loads(row["study_path"])
        return None
    except Exception:
        return None


def save_onboarding(conn, user_id: str, exam_focus: list, exam_date: str,
                    prep_level: str, study_mode: str, study_path: dict) -> None:
    """Persist onboarding answers and AI-generated study path in nyaya.db."""
    nc = get_nyaya_conn()
    nc.execute(
        """UPDATE users SET
           exam_focus=?, exam_date=?, prep_level=?, study_mode=?,
           study_path=?, onboarding_completed=1
           WHERE user_id=?""",
        (json.dumps(exam_focus), exam_date, prep_level, study_mode,
         json.dumps(study_path), user_id)
    )
    nc.commit()


def get_time_breakdown(conn, user_id: str, days: int = 1) -> list[dict]:
    """Time-per-page for the last N days, ordered by total seconds descending."""
    try:
        nc = get_nyaya_conn()
        rows = nc.execute(
            """SELECT entity_id AS page_name,
                      SUM(CAST(json_extract(payload, '$.duration_s') AS INTEGER)) AS total_seconds
               FROM user_events
               WHERE user_id=? AND event_type='page_view'
                 AND date(created_at) >= date('now', ?)
               GROUP BY entity_id
               ORDER BY total_seconds DESC""",
            (user_id, f"-{days} days")
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    raise ValueError("Set the ANTHROPIC_API_KEY environment variable to enable quiz evaluation.")


def get_papers(conn) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT paper_id FROM topics WHERE exam_id=? AND topic_level='topic' ORDER BY paper_id",
        (EXAM_ID,)
    ).fetchall()
    return [r["paper_id"] for r in rows]


def get_topics(conn, paper_id=None) -> list[dict]:
    paper_clause = "AND t.paper_id=?" if paper_id else ""
    uid = get_user_id()
    rows = conn.execute(f"""
        SELECT t.topic_id, t.topic_name, t.paper_id,
               gs.state,
               bs.base_priority_score, bs.pyq_count, bs.distinct_years,
               COUNT(DISTINCT ma.answer_id) AS answers_ready,
               COUNT(DISTINCT q.question_id) AS total_q,
               MAX(COALESCE(um.mastery_level, 0.0)) AS mastery_level
        FROM topics t
        LEFT JOIN gap_states gs ON t.topic_id=gs.topic_id AND t.exam_id=gs.exam_id AND gs.user_id=?
        LEFT JOIN user_mastery um ON t.topic_id=um.topic_id AND t.exam_id=um.exam_id AND um.user_id=?
        LEFT JOIN topic_base_scores bs ON t.topic_id=bs.topic_id AND t.exam_id=bs.exam_id
        LEFT JOIN pyq_questions q ON t.topic_id=q.topic_id AND t.exam_id=q.exam_id
        LEFT JOIN model_answers ma ON q.question_id=ma.question_id AND q.exam_id=ma.exam_id
        WHERE t.exam_id=? AND t.topic_level='topic' {paper_clause}
        GROUP BY t.topic_id
        ORDER BY t.paper_id,
                 CASE gs.state WHEN 'IN_STUDY' THEN 0 WHEN 'FLAGGED' THEN 1
                     WHEN 'PARTIAL' THEN 2 WHEN 'DECAYING' THEN 3
                     WHEN 'UNVISITED' THEN 4 WHEN 'VERIFIED' THEN 5 ELSE 6 END,
                 bs.base_priority_score DESC
    """, (uid, uid, EXAM_ID) + ((paper_id,) if paper_id else ())).fetchall()
    return [dict(r) for r in rows]


def set_topic_state(conn, topic_id: str, new_state: str, trigger: str,
                    user_id: str | None = None):
    """Update gap state for a topic. Pass user_id explicitly to avoid BUG-010."""
    uid = user_id or get_user_id()
    current = conn.execute(
        "SELECT state FROM gap_states WHERE user_id=? AND topic_id=? AND exam_id=?",
        (uid, topic_id, EXAM_ID)
    ).fetchone()
    if not current:
        return
    from_state = current["state"]
    conn.execute(
        "UPDATE gap_states SET state=?, last_active_at=datetime('now') WHERE user_id=? AND topic_id=? AND exam_id=?",
        (new_state, uid, topic_id, EXAM_ID)
    )
    conn.execute(
        "INSERT INTO gap_state_events (user_id,topic_id,exam_id,from_state,to_state,trigger,created_at) VALUES (?,?,?,?,?,?,datetime('now'))",
        (uid, topic_id, EXAM_ID, from_state, new_state, trigger)
    )
    conn.commit()


def get_questions(conn, topic_id=None, paper_id=None, year=None) -> list[dict]:
    clauses = ["q.exam_id=?"]
    params = [EXAM_ID]
    if topic_id:
        clauses.append("q.topic_id=?"); params.append(topic_id)
    if paper_id:
        clauses.append("q.paper_id=?"); params.append(paper_id)
    if year:
        clauses.append("q.year=?"); params.append(year)
    where = " AND ".join(clauses)
    rows = conn.execute(f"""
        SELECT q.question_id, q.question_text, q.marks, q.year, q.paper_id,
               q.topic_id, q.answer_length,
               r.rubric_points, r.key_terms, r.diagram_expected, r.diagram_type,
               ma.answer_id
        FROM pyq_questions q
        LEFT JOIN question_rubrics r ON q.question_id=r.question_id AND q.exam_id=r.exam_id
        LEFT JOIN model_answers ma ON q.question_id=ma.question_id AND q.exam_id=ma.exam_id
        WHERE {where}
        ORDER BY q.marks DESC NULLS LAST, q.year DESC
    """, params).fetchall()
    result = [dict(r) for r in rows]
    for r in result:
        r["question_text"] = clean_q(r["question_text"])
    return result


def get_answer(conn, question_id: str):
    row = conn.execute("""
        SELECT ma.*, q.question_text, q.marks, q.year, q.paper_id, q.topic_id, q.answer_length,
               r.rubric_points, r.key_terms, r.diagram_expected, r.diagram_type
        FROM model_answers ma
        JOIN pyq_questions q ON ma.question_id=q.question_id AND ma.exam_id=q.exam_id
        LEFT JOIN question_rubrics r ON q.question_id=r.question_id AND q.exam_id=r.exam_id
        WHERE ma.question_id=? AND ma.exam_id=?
    """, (question_id, EXAM_ID)).fetchone()
    return dict(row) if row else None


def get_mcq_questions(conn, topic_id: str) -> list[dict]:
    rows = conn.execute("""
        SELECT * FROM return_quiz_questions
        WHERE topic_id=? AND exam_id=?
        ORDER BY difficulty
    """, (topic_id, EXAM_ID)).fetchall()
    return [dict(r) for r in rows]


def get_subtopics(conn, topic_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT topic_name FROM topics WHERE subtopic_of=? AND exam_id=? ORDER BY topic_id",
        (topic_id, EXAM_ID)
    ).fetchall()
    return [r["topic_name"] for r in rows]


def get_topic_base_score(conn, topic_id: str):
    row = conn.execute(
        "SELECT * FROM topic_base_scores WHERE topic_id=? AND exam_id=?",
        (topic_id, EXAM_ID)
    ).fetchone()
    return dict(row) if row else None


def jl(s) -> list:
    if not s:
        return []
    try:
        result = json.loads(s)
        return result if result is not None else []
    except Exception:
        return []


def get_study_brief(conn, topic_id: str) -> dict:
    topic = conn.execute(
        "SELECT topic_name, paper_id, syllabus_weight FROM topics WHERE topic_id=? AND exam_id=? AND topic_level='topic'",
        (topic_id, EXAM_ID)
    ).fetchone()

    subtopics = conn.execute(
        "SELECT topic_name FROM topics WHERE subtopic_of=? AND exam_id=? ORDER BY topic_id",
        (topic_id, EXAM_ID)
    ).fetchall()

    bs = conn.execute(
        "SELECT base_priority_score, pyq_count, distinct_years FROM topic_base_scores WHERE topic_id=? AND exam_id=?",
        (topic_id, EXAM_ID)
    ).fetchone()

    questions = conn.execute("""
        SELECT q.question_id, q.year, q.marks, q.question_text, q.answer_length,
               r.rubric_points, r.key_terms, r.diagram_expected, r.diagram_type
        FROM pyq_questions q
        LEFT JOIN question_rubrics r ON q.question_id=r.question_id AND q.exam_id=r.exam_id
        WHERE q.topic_id=? AND q.exam_id=?
        ORDER BY q.marks DESC NULLS LAST, q.year DESC
        LIMIT 10
    """, (topic_id, EXAM_ID)).fetchall()

    all_key_terms = []
    seen_terms = set()
    all_diagrams = []
    for q in questions:
        for kt in jl(q["key_terms"]):
            if kt not in seen_terms:
                seen_terms.add(kt)
                all_key_terms.append(kt)
        if q["diagram_expected"] and q["diagram_type"]:
            all_diagrams.append(q["diagram_type"])

    from collections import Counter
    diagram_counts = dict(Counter(all_diagrams).most_common())

    return {
        "topic": dict(topic) if topic else {},
        "subtopics": [r["topic_name"] for r in subtopics],
        "base_score": dict(bs) if bs else {},
        "key_terms": all_key_terms,
        "diagrams": diagram_counts,
        "questions": [
            {
                "question_id": q["question_id"],
                "year": q["year"],
                "marks": q["marks"],
                "question_text": clean_q(q["question_text"]),
                "answer_length": q["answer_length"],
                "rubric_points": jl(q["rubric_points"]),
                "key_terms": jl(q["key_terms"]),
                "diagram_expected": q["diagram_expected"],
                "diagram_type": q["diagram_type"],
            }
            for q in questions
        ],
    }


def get_attempts(conn, topic_id=None, date_from=None, date_to=None,
                 user_id: str | None = None) -> list:
    uid = user_id or get_user_id()
    clauses = ["da.exam_id=?", "da.user_id=?"]
    params = [EXAM_ID, uid]
    if topic_id:
        clauses.append("q.topic_id=?"); params.append(topic_id)
    if date_from:
        clauses.append("da.created_at >= ?"); params.append(str(date_from))
    if date_to:
        clauses.append("da.created_at <= ?"); params.append(str(date_to) + " 23:59:59")
    where = " AND ".join(clauses)

    rows = conn.execute(f"""
        SELECT da.attempt_id, da.question_id, da.quiz_mode,
               da.weighted_score, da.scores_json,
               da.word_count_intro, da.word_count_body, da.word_count_conclusion,
               da.created_at,
               q.question_text, q.topic_id, q.paper_id, q.marks, q.year
        FROM descriptive_attempts da
        JOIN pyq_questions q ON da.question_id=q.question_id AND da.exam_id=q.exam_id
        WHERE {where}
        ORDER BY da.created_at DESC
    """, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["scores"] = jl(d.pop("scores_json", None) or "[]")
        result.append(d)
    return result


def get_attempt_summary(conn, user_id: str | None = None) -> dict:
    uid = user_id or get_user_id()
    row = conn.execute("""
        SELECT COUNT(*) as total
        FROM descriptive_attempts WHERE exam_id=? AND user_id=?
    """, (EXAM_ID, uid)).fetchone()

    top_topic = conn.execute("""
        SELECT q.topic_id, COUNT(*) as cnt
        FROM descriptive_attempts da
        JOIN pyq_questions q ON da.question_id=q.question_id AND da.exam_id=q.exam_id
        WHERE da.exam_id=? AND da.user_id=?
        GROUP BY q.topic_id ORDER BY cnt DESC LIMIT 1
    """, (EXAM_ID, uid)).fetchone()

    return {
        "total": row["total"] or 0,
        "top_topic": top_topic["topic_id"] if top_topic else None,
    }


def get_true_readiness(conn, user_id: str | None = None) -> dict:
    """Compute weighted readiness % and projected % if top-10 gaps are filled."""
    uid = user_id or get_user_id()
    rows = conn.execute("""
        SELECT um.topic_id,
               um.mastery_level,
               bs.base_priority_score
        FROM user_mastery um
        JOIN topic_base_scores bs ON um.topic_id = bs.topic_id AND um.exam_id = bs.exam_id
        JOIN topics t ON um.topic_id = t.topic_id AND um.exam_id = t.exam_id
        WHERE um.user_id = ? AND um.exam_id = ? AND t.topic_level = 'topic'
    """, (uid, EXAM_ID)).fetchall()

    if not rows:
        return {"formula_pct": 0.0, "projected_pct": 0.0, "covered_count": 0, "topic_count": 0}

    data = [{"topic_id": r["topic_id"], "mastery": r["mastery_level"], "priority": r["base_priority_score"]} for r in rows]

    total_priority = sum(d["priority"] for d in data)
    if total_priority == 0:
        return {"formula_pct": 0.0, "projected_pct": 0.0, "covered_count": 0, "topic_count": len(data)}

    formula_pct = round(sum(d["mastery"] * d["priority"] for d in data) / total_priority * 100, 1)
    covered_count = sum(1 for d in data if d["mastery"] >= 0.5)

    gaps = sorted(
        [d for d in data if d["mastery"] < 0.5],
        key=lambda d: d["priority"] * (1 - d["mastery"]),
        reverse=True,
    )[:10]
    gap_ids = {d["topic_id"] for d in gaps}

    projected_pct = round(
        sum((1.0 if d["topic_id"] in gap_ids else d["mastery"]) * d["priority"] for d in data) / total_priority * 100,
        1,
    )

    return {
        "formula_pct": formula_pct,
        "projected_pct": projected_pct,
        "covered_count": covered_count,
        "topic_count": len(data),
    }


def submit_return_quiz(conn, topic_id: str, answers: dict, session_id: str,
                       user_id: str | None = None) -> dict:
    """Grade MCQ answers, update gap state, mastery, and attempt summary."""
    uid = user_id or get_user_id()
    questions = get_mcq_questions(conn, topic_id)
    if not questions:
        return {"score": 0.0, "correct": 0, "total": 0, "new_state": "UNVISITED", "from_state": "UNVISITED", "new_mastery": 0.0}

    correct = 0
    total = len(questions)
    graded_rows = []
    for q in questions:
        qid = q["question_id"]
        user_ans = (answers.get(qid) or "").strip()
        is_correct = 1 if user_ans == (q["correct_answer"] or "").strip() else 0
        correct += is_correct
        graded_rows.append((uid, topic_id, EXAM_ID, qid, user_ans, is_correct, session_id))

    score = correct / total

    cfg = conn.execute(
        "SELECT verified_quiz_threshold, partial_quiz_threshold FROM exam_configurations WHERE exam_id=?",
        (EXAM_ID,)
    ).fetchone()
    verified_thresh = cfg["verified_quiz_threshold"] if cfg else 0.80
    partial_thresh = cfg["partial_quiz_threshold"] if cfg else 0.50
    if is_crunch_mode():
        verified_thresh = 0.70
        partial_thresh = 0.45

    gap = conn.execute(
        "SELECT state, urgency_multiplier, attempt_count FROM gap_states WHERE user_id=? AND topic_id=? AND exam_id=?",
        (uid, topic_id, EXAM_ID)
    ).fetchone()
    from_state = gap["state"] if gap else "UNVISITED"
    urgency = gap["urgency_multiplier"] if gap else 1.0
    attempt_count = (gap["attempt_count"] or 0) + 1

    existing = conn.execute(
        "SELECT mastery_level, quiz_attempt_count FROM user_mastery WHERE user_id=? AND topic_id=? AND exam_id=?",
        (uid, topic_id, EXAM_ID)
    ).fetchone()
    old_mastery = existing["mastery_level"] if existing else 0.0
    old_count = existing["quiz_attempt_count"] if existing else 0
    new_mastery = (old_mastery * old_count + score) / (old_count + 1)

    base_row = conn.execute(
        "SELECT base_priority_score FROM topic_base_scores WHERE topic_id=? AND exam_id=?",
        (topic_id, EXAM_ID)
    ).fetchone()
    base_priority = base_row["base_priority_score"] if base_row else 0.5

    if score >= verified_thresh:
        new_state = "VERIFIED"
    elif score >= partial_thresh:
        new_state = "PARTIAL"
    else:
        new_state = "FLAGGED"
    new_urgency = min(urgency + 0.3, 2.0) if new_state == "FLAGGED" else urgency
    stuck = 1 if new_state == "FLAGGED" and attempt_count >= 3 else 0

    with conn:
        for row in graded_rows:
            conn.execute("""
                INSERT INTO return_quiz_attempts
                    (user_id, topic_id, exam_id, question_id, user_answer, is_correct, session_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, row)

        if new_state == "VERIFIED":
            conn.execute("""
                UPDATE gap_states SET state=?, last_return_quiz_score=?, urgency_multiplier=?,
                    last_verified_at=datetime('now'), next_review_at=datetime('now','+14 days'),
                    last_active_at=datetime('now'), attempt_count=attempt_count+1, stuck_flag=0
                WHERE user_id=? AND topic_id=? AND exam_id=?
            """, (new_state, score, urgency, uid, topic_id, EXAM_ID))
        elif new_state == "PARTIAL":
            conn.execute("""
                UPDATE gap_states SET state=?, last_return_quiz_score=?,
                    last_active_at=datetime('now'), attempt_count=attempt_count+1
                WHERE user_id=? AND topic_id=? AND exam_id=?
            """, (new_state, score, uid, topic_id, EXAM_ID))
        else:
            conn.execute("""
                UPDATE gap_states SET state=?, last_return_quiz_score=?, urgency_multiplier=?,
                    last_active_at=datetime('now'), attempt_count=attempt_count+1, stuck_flag=?
                WHERE user_id=? AND topic_id=? AND exam_id=?
            """, (new_state, score, new_urgency, stuck, uid, topic_id, EXAM_ID))

        conn.execute("""
            INSERT INTO gap_state_events
                (user_id, topic_id, exam_id, from_state, to_state, trigger, quiz_score, created_at)
            VALUES (?, ?, ?, ?, ?, 'mcq_quiz', ?, datetime('now'))
        """, (uid, topic_id, EXAM_ID, from_state, new_state, score))

        conn.execute("""
            INSERT OR IGNORE INTO user_mastery (user_id, topic_id, exam_id) VALUES (?, ?, ?)
        """, (uid, topic_id, EXAM_ID))
        conn.execute("""
            UPDATE user_mastery SET mastery_level=?, last_quiz_score=?,
                quiz_attempt_count=?, last_tested_at=datetime('now')
            WHERE user_id=? AND topic_id=? AND exam_id=?
        """, (new_mastery, score, old_count + 1, uid, topic_id, EXAM_ID))

        conn.execute("""
            UPDATE topic_attempt_summary SET
                total_attempts = total_attempts + 1,
                correct_attempts = correct_attempts + ?,
                coverage_pct = ?,
                flag_impact_score = ?,
                last_updated = datetime('now')
            WHERE user_id=? AND topic_id=? AND exam_id=?
        """, (correct, score, base_priority * (1 - score), uid, topic_id, EXAM_ID))

    return {
        "score": score,
        "correct": correct,
        "total": total,
        "new_state": new_state,
        "from_state": from_state,
        "new_mastery": new_mastery,
    }


def get_paper_coverage(conn, user_id: str | None = None) -> list[dict]:
    """Return per-paper weighted coverage stats for all top-level topics."""
    from collections import defaultdict

    uid = user_id or get_user_id()
    rows = conn.execute("""
        SELECT t.paper_id,
               um.mastery_level,
               bs.base_priority_score
        FROM user_mastery um
        JOIN topic_base_scores bs ON um.topic_id = bs.topic_id AND um.exam_id = bs.exam_id
        JOIN topics t ON um.topic_id = t.topic_id AND um.exam_id = t.exam_id
        WHERE um.user_id = ? AND um.exam_id = ? AND t.topic_level = 'topic'
    """, (uid, EXAM_ID)).fetchall()

    if not rows:
        return []

    papers = defaultdict(lambda: {"weighted_sum": 0.0, "priority_sum": 0.0, "covered": 0, "total": 0})
    for r in rows:
        p = papers[r["paper_id"]]
        p["weighted_sum"] += r["mastery_level"] * r["base_priority_score"]
        p["priority_sum"] += r["base_priority_score"]
        p["total"] += 1
        if r["mastery_level"] >= 0.5:
            p["covered"] += 1

    result = []
    for paper_id in sorted(papers):
        p = papers[paper_id]
        coverage_pct = round(p["weighted_sum"] / p["priority_sum"] * 100, 1) if p["priority_sum"] else 0.0
        result.append({
            "paper_id": paper_id,
            "coverage_pct": coverage_pct,
            "covered_count": p["covered"],
            "topic_count": p["total"],
        })
    return result


def _days_bucket(days_to_exam: int) -> str:
    if days_to_exam <= 15:
        return "crunch"
    return "standard"


def _template_key(exam_list: list[str], days_to_exam: int, prep_level: str, study_mode: str) -> str:
    exam_part = "_".join(sorted(exam_list))
    bucket = _days_bucket(days_to_exam)
    return f"{exam_part}__{bucket}__{prep_level}__{study_mode}"


def get_study_plan_template(
    conn,
    exam_list: list[str],
    days_to_exam: int,
    prep_level: str,
    study_mode: str,
) -> dict | None:
    key = _template_key(exam_list, days_to_exam, prep_level, study_mode)
    try:
        row = conn.execute(
            "SELECT plan_json FROM study_plan_templates WHERE template_key = ?",
            (key,),
        ).fetchone()
        if row:
            return json.loads(row["plan_json"])
    except Exception:
        pass
    return None
