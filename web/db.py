"""Shared DB helpers for the web app."""
import json
import os
import re
import sqlite3
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
EXAM_DATE = "2026-06-17"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def load_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_path = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("Set ANTHROPIC_API_KEY env var or place key in Devthorium/.env")


def get_papers(conn) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT paper_id FROM topics WHERE exam_id=? AND topic_level='topic' ORDER BY paper_id",
        (EXAM_ID,)
    ).fetchall()
    return [r["paper_id"] for r in rows]


def get_topics(conn, paper_id=None) -> list[dict]:
    paper_clause = "AND t.paper_id=?" if paper_id else ""
    params = [EXAM_ID, EXAM_ID, EXAM_ID, USER_ID, EXAM_ID]
    if paper_id:
        params.insert(1, paper_id)

    rows = conn.execute(f"""
        SELECT t.topic_id, t.topic_name, t.paper_id,
               gs.state,
               bs.base_priority_score, bs.pyq_count, bs.distinct_years,
               COUNT(DISTINCT ma.answer_id) AS answers_ready,
               COUNT(DISTINCT q.question_id) AS total_q
        FROM topics t
        LEFT JOIN gap_states gs ON t.topic_id=gs.topic_id AND t.exam_id=gs.exam_id AND gs.user_id=?
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
    """, (USER_ID, EXAM_ID) + ((paper_id,) if paper_id else ())).fetchall()
    return [dict(r) for r in rows]


def set_topic_state(conn, topic_id: str, new_state: str, trigger: str):
    current = conn.execute(
        "SELECT state FROM gap_states WHERE user_id=? AND topic_id=? AND exam_id=?",
        (USER_ID, topic_id, EXAM_ID)
    ).fetchone()
    if not current:
        return
    from_state = current["state"]
    conn.execute(
        "UPDATE gap_states SET state=?, last_active_at=datetime('now') WHERE user_id=? AND topic_id=? AND exam_id=?",
        (new_state, USER_ID, topic_id, EXAM_ID)
    )
    conn.execute(
        "INSERT INTO gap_state_events (user_id,topic_id,exam_id,from_state,to_state,trigger,created_at) VALUES (?,?,?,?,?,?,datetime('now'))",
        (USER_ID, topic_id, EXAM_ID, from_state, new_state, trigger)
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
        return json.loads(s)
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
    params = [EXAM_ID, USER_ID]
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
    row = conn.execute("""
        SELECT COUNT(*) as total,
               AVG(weighted_score) as avg_score,
               MAX(weighted_score) as max_score
        FROM descriptive_attempts WHERE exam_id=? AND user_id=?
    """, (EXAM_ID, USER_ID)).fetchone()

    top_topic = conn.execute("""
        SELECT q.topic_id, COUNT(*) as cnt
        FROM descriptive_attempts da
        JOIN pyq_questions q ON da.question_id=q.question_id AND da.exam_id=q.exam_id
        WHERE da.exam_id=? AND da.user_id=?
        GROUP BY q.topic_id ORDER BY cnt DESC LIMIT 1
    """, (EXAM_ID, USER_ID)).fetchone()

    return {
        "total": row["total"] or 0,
        "avg_score": round(row["avg_score"] * 10, 1) if row["avg_score"] else None,
        "max_score": round(row["max_score"] * 10, 1) if row["max_score"] else None,
        "top_topic": top_topic["topic_id"] if top_topic else None,
    }
