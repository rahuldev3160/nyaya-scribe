"""
Generate MCQ return-quiz questions for topics (pre-cached, no LLM during session).
Run: python3 scripts/generate_return_quiz.py --topic inflation_india
     python3 scripts/generate_return_quiz.py --all

Creates 5 MCQ questions per topic using Haiku batch. Questions test understanding
at concept/analysis/application level (not factual recall).
"""
import argparse
import json
import sqlite3
import time
import uuid
from pathlib import Path

import anthropic

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
BATCH_ID_FILE = Path(__file__).parent.parent / "data" / "return_quiz_batch.txt"
EXAM_ID = "ies_2026"

MCQ_SYSTEM = """You are an IES (Indian Economic Service) quiz question generator.
Generate exactly 5 MCQ questions for the given economics topic.

Focus on CONCEPTS and ANALYSIS, not factual recall. Questions should test whether
a student truly understands the topic, not just memorizes facts.

Return ONLY valid JSON (no markdown):
[
  {
    "question_text": "...",
    "question_type": "mcq",
    "correct_answer": "A) ...",
    "option_b": "B) ...",
    "option_c": "C) ...",
    "option_d": "D) ...",
    "difficulty": 0.4-0.8,
    "dimension_id": "concept|application|analysis|policy"
  }
]

Rules:
- All 4 options must be plausible (no obviously wrong distractors)
- Correct answer should not always be the same position (mix A/B/C/D)
- difficulty 0.4-0.6 for concept, 0.6-0.8 for analysis/policy
- Include 1-2 questions on diagrams/graphical analysis
- IES level: graduate economics"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def load_api_key() -> str:
    env_path = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("ANTHROPIC_API_KEY not found")


def get_topics_needing_quiz(conn: sqlite3.Connection, topic_filter=None) -> list[dict]:
    clause = "AND t.topic_id = ?" if topic_filter else ""
    params = [EXAM_ID, EXAM_ID]
    if topic_filter:
        params.insert(1, topic_filter)

    rows = conn.execute(f"""
        SELECT t.topic_id, t.topic_name, t.paper_id,
               GROUP_CONCAT(DISTINCT st.topic_name) AS subtopic_names,
               COUNT(DISTINCT rq.question_id) AS existing_quiz_q
        FROM topics t
        LEFT JOIN topics st ON st.subtopic_of=t.topic_id AND st.exam_id=t.exam_id
        LEFT JOIN return_quiz_questions rq ON t.topic_id=rq.topic_id AND rq.exam_id=?
        WHERE t.exam_id=? AND t.topic_level='topic' {clause}
        GROUP BY t.topic_id
        HAVING existing_quiz_q < 5
        ORDER BY t.paper_id, t.topic_id
    """, params).fetchall()

    topics = []
    for r in rows:
        # Get top 3 PYQs for context
        pyqs = conn.execute("""
            SELECT q.question_text, r2.key_terms
            FROM pyq_questions q
            LEFT JOIN question_rubrics r2 ON q.question_id=r2.question_id AND q.exam_id=r2.exam_id
            WHERE q.topic_id=? AND q.exam_id=?
            ORDER BY q.marks DESC, q.year DESC LIMIT 3
        """, (r[0], EXAM_ID)).fetchall()

        topics.append({
            "topic_id": r[0],
            "topic_name": r[1],
            "paper_id": r[2],
            "subtopics": r[3] or "",
            "sample_pyqs": [p[0][:150] for p in pyqs],
            "sample_key_terms": list(set(
                term
                for p in pyqs
                if p[1]
                for term in json.loads(p[1])[:4]
            ))[:8],
        })

    return topics


def build_mcq_requests(topics: list[dict]) -> list[dict]:
    requests = []
    for t in topics:
        subtopic_str = f"\nSubtopics: {t['subtopics']}" if t['subtopics'] else ""
        pyq_str = "\n".join(f"  - {q}" for q in t['sample_pyqs'])
        terms_str = ", ".join(t['sample_key_terms'])

        user_content = f"""Topic: {t['topic_name']} (Paper: {t['paper_id'].upper()})
{subtopic_str}

Sample PYQ questions on this topic:
{pyq_str}

Key terms students should know: {terms_str}

Generate 5 MCQ questions testing deep understanding of this topic."""

        requests.append({
            "custom_id": t["topic_id"],
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 2048,
                "system": MCQ_SYSTEM,
                "messages": [{"role": "user", "content": user_content}],
            },
        })
    return requests


def insert_quiz_questions(conn: sqlite3.Connection, client, batch_id: str) -> tuple[int, int]:
    inserted = 0
    errors = 0

    for result in client.messages.batches.results(batch_id):
        topic_id = result.custom_id

        if result.result.type == "error":
            print(f"  ERROR {topic_id}: {result.result.error}")
            errors += 1
            continue

        raw = result.result.message.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]

        try:
            questions = json.loads(raw)
        except Exception:
            print(f"  PARSE ERROR {topic_id}: {repr(raw[:80])}")
            errors += 1
            continue

        for q in questions:
            qid = f"rq_{topic_id}_{uuid.uuid4().hex[:6]}"
            conn.execute("""
                INSERT OR IGNORE INTO return_quiz_questions
                    (question_id, topic_id, exam_id, question_text, question_type,
                     correct_answer, option_b, option_c, option_d,
                     difficulty, dimension_id, validation_status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,'pending')
            """, (
                qid, topic_id, EXAM_ID,
                q.get("question_text", ""),
                q.get("question_type", "mcq"),
                q.get("correct_answer", ""),
                q.get("option_b"), q.get("option_c"), q.get("option_d"),
                q.get("difficulty", 0.5),
                q.get("dimension_id", "concept"),
            ))
            inserted += 1

    conn.commit()
    return inserted, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", help="Generate for specific topic")
    parser.add_argument("--all", action="store_true", help="Generate for all topics")
    args = parser.parse_args()

    if not args.topic and not args.all:
        print("Specify --topic <topic_id> or --all")
        raise SystemExit(1)

    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()

    if BATCH_ID_FILE.exists():
        batch_id = BATCH_ID_FILE.read_text().strip()
        print(f"Resuming batch {batch_id}...")
    else:
        topics = get_topics_needing_quiz(conn, args.topic)
        if not topics:
            print("All topics already have quiz questions")
            raise SystemExit(0)

        print(f"Generating MCQ questions for {len(topics)} topics...")
        requests = build_mcq_requests(topics)
        batch = client.messages.batches.create(requests=requests)
        batch_id = batch.id
        BATCH_ID_FILE.write_text(batch_id)
        print(f"  Batch submitted: {batch_id}")

    print("Waiting for batch...")
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        c = batch.request_counts
        print(f"  {batch.processing_status} | done={c.succeeded+c.errored} processing={c.processing}")
        if batch.processing_status == "ended":
            break
        time.sleep(20)

    print("Processing results...")
    inserted, errors = insert_quiz_questions(conn, client, batch_id)
    print(f"  Inserted: {inserted} questions | Errors: {errors}")

    if errors == 0 and BATCH_ID_FILE.exists():
        BATCH_ID_FILE.unlink()

    total = conn.execute(
        "SELECT COUNT(*) FROM return_quiz_questions WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]
    print(f"\nTotal return quiz questions in DB: {total}")
    conn.close()
