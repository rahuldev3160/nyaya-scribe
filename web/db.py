"""Shared DB helpers for the web app."""
import json
import os
import re
import sqlite3
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
EXAM_DATE = "2026-06-19"


def is_crunch_mode() -> bool:
    exam = datetime.strptime(EXAM_DATE, "%Y-%m-%d").date()
    return (exam - datetime.today().date()).days <= 7


def get_user_id() -> str:
    """Return the current session's user ID. Auto-assigns UUID on first call from any page."""
    try:
        import streamlit as st
        import uuid as _uuid
        uid = st.session_state.get("user_id")
        if not uid:
            uid = str(_uuid.uuid4())
            st.session_state.user_id = uid
        return uid
    except Exception:
        pass
    return USER_ID


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_user(conn, user_id: str) -> None:
    """Seed default rows for a new session user. Safe to call on every load (OR IGNORE)."""
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


def log_event(conn, event_type: str, entity_type: str | None = None,
              entity_id: str | None = None, exam_id: str | None = None,
              payload: dict | None = None) -> None:
    """Append one row to user_events. Silent no-op if table doesn't exist yet."""
    try:
        import streamlit as st
        session_id = st.session_state.get("session_id") or st.session_state.get("user_id", "unknown")
    except Exception:
        session_id = "script"
    try:
        import json
        conn.execute(
            """INSERT INTO user_events
               (user_id, session_id, event_type, entity_type, entity_id, exam_id, payload)
               VALUES (?,?,?,?,?,?,?)""",
            (get_user_id(), session_id, event_type, entity_type, entity_id, exam_id,
             json.dumps(payload) if payload else None)
        )
        conn.commit()
    except Exception:
        pass  # Never crash the app over logging


def track_page_time(conn, page_name: str) -> None:
    """Call after auth on each page. Logs exit time of previous page. Safe without auth."""
    try:
        import streamlit as st
        from datetime import datetime, timezone
        if not st.session_state.get("user_id"):
            return
        now = datetime.now(timezone.utc)
        prev = st.session_state.get("_active_page")
        if prev and prev != page_name:
            entry = st.session_state.get("_page_entry_time")
            if entry:
                duration_s = int((now - entry).total_seconds())
                if 5 < duration_s < 14400:
                    log_event(conn, "page_time", "page", prev,
                             payload={"duration_s": duration_s})
        if st.session_state.get("_active_page") != page_name:
            st.session_state._active_page = page_name
            st.session_state._page_entry_time = now
    except Exception:
        pass


def get_study_path(conn, user_id: str) -> dict | None:
    """Return the user's AI-generated study path, or None if onboarding not done."""
    try:
        row = conn.execute(
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
    """Persist onboarding answers and AI-generated study path; mark onboarding complete."""
    conn.execute(
        """UPDATE users SET
           exam_focus=?, exam_date=?, prep_level=?, study_mode=?,
           study_path=?, onboarding_completed=1
           WHERE user_id=?""",
        (json.dumps(exam_focus), exam_date, prep_level, study_mode,
         json.dumps(study_path), user_id)
    )
    conn.commit()


def get_time_breakdown(conn, user_id: str, days: int = 1) -> list[dict]:
    """Time-per-page for the last N days, ordered by total seconds descending."""
    try:
        rows = conn.execute(
            """SELECT entity_id AS page_name,
                      SUM(CAST(json_extract(payload, '$.duration_s') AS INTEGER)) AS total_seconds
               FROM user_events
               WHERE user_id=? AND event_type='page_time'
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


def set_topic_state(conn, topic_id: str, new_state: str, trigger: str):
    uid = get_user_id()
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


def get_attempts(conn, topic_id=None, date_from=None, date_to=None) -> list:
    clauses = ["da.exam_id=?", "da.user_id=?"]
    params = [EXAM_ID, get_user_id()]
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
        if isinstance(d["scores"], dict):
            pass
        result.append(d)
    return result


def get_attempt_summary(conn) -> dict:
    uid = get_user_id()
    row = conn.execute("""
        SELECT COUNT(*) as total,
               AVG(weighted_score) as avg_score,
               MAX(weighted_score) as max_score
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
        "avg_score": round(row["avg_score"] * 10, 1) if row["avg_score"] else None,
        "max_score": round(row["max_score"] * 10, 1) if row["max_score"] else None,
        "top_topic": top_topic["topic_id"] if top_topic else None,
    }


def get_true_readiness(conn, user_id: str = None) -> dict:
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

    # Top-10 gap topics: mastery < 0.5, sorted by priority × (1 - mastery) DESC
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


def submit_return_quiz(conn, topic_id: str, answers: dict, session_id: str) -> dict:
    """
    Grade MCQ answers, update gap state, mastery, and attempt summary.
    answers: {question_id: user_answer_string}
    Returns: {score, correct, total, new_state, from_state, new_mastery}
    """
    uid = get_user_id()
    questions = get_mcq_questions(conn, topic_id)
    if not questions:
        return {"score": 0.0, "correct": 0, "total": 0, "new_state": "UNVISITED", "from_state": "UNVISITED", "new_mastery": 0.0}

    # Grade answers
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

    # Read all config before entering transaction
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
    attempt_count = (gap["attempt_count"] or 0) + 1  # used locally for stuck logic only

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

    # Compute new gap state
    if score >= verified_thresh:
        new_state = "VERIFIED"
    elif score >= partial_thresh:
        new_state = "PARTIAL"
    else:
        new_state = "FLAGGED"
    new_urgency = min(urgency + 0.3, 2.0) if new_state == "FLAGGED" else urgency
    stuck = 1 if new_state == "FLAGGED" and attempt_count >= 3 else 0

    # Write all changes atomically
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

        # INSERT OR IGNORE ensures first attempt creates the row; UPDATE fills it in
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


def get_paper_coverage(conn, user_id: str = None) -> list[dict]:
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
