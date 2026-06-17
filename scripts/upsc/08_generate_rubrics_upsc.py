"""
Stage 8 (UPSC): Extract marking rubrics for all UPSC PYQs via Haiku Batch API.
Run: python3 scripts/upsc/08_generate_rubrics_upsc.py

Reads pyq_questions, sends each to Haiku (batch), stores rubric_points JSON
in question_rubrics table. Skips questions already in question_rubrics.
Saves batch_id to data/upsc_rubrics_batch.txt so the script is safe to restart.
"""
import json
import sqlite3
import time
from pathlib import Path

import anthropic

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_eco_opt.db"
BATCH_ID_FILE = Path(__file__).parent.parent.parent / "data" / "upsc_rubrics_batch.txt"
EXAM_ID = "upsc_eco_opt"

SYSTEM_PROMPT = """You are a UPSC Economics Optional (Mains) exam rubric extractor.
Given a UPSC economics question with its marks, extract a concise marking rubric.

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "rubric_points": [
    {"point": "...", "category": "concept|application|analysis|policy", "weight": 0.25, "section_hint": "intro|body|conclusion"}
  ],
  "key_terms": ["term1", "term2"],
  "diagram_expected": 0,
  "diagram_type": null
}

Rules:
- rubric_points: 3-6 points, weights summing to 1.0
- category: concept (define/state), application (use the concept), analysis (evaluate/compare), policy (government measures/schemes)
- section_hint: which part of a 3-section answer (intro/body/conclusion) this point belongs to
- diagram_expected: 1 if a diagram/graph/curve would substantially strengthen the answer
- diagram_type: if diagram_expected=1, one of: demand_supply_curve | production_function | is_lm_curve | lorenz_curve | aggregate_demand | bop_curve | solow_model | phillips_curve | indifference_curve | flow_chart | bar_chart | table | growth_model | other
- key_terms: 4-8 economics terms that a good answer must include"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def load_api_key() -> str:
    env_path = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("ANTHROPIC_API_KEY not found in Devthorium .env")


def load_pending_questions(conn: sqlite3.Connection) -> list:
    rows = conn.execute("""
        SELECT q.question_id, q.exam_id, q.question_text, q.marks, q.paper_id, q.topic_id
        FROM pyq_questions q
        LEFT JOIN question_rubrics r ON q.question_id = r.question_id AND q.exam_id = r.exam_id
        WHERE q.exam_id = ? AND r.question_id IS NULL
        ORDER BY q.paper_id, q.question_id
    """, (EXAM_ID,)).fetchall()

    return [
        {
            "question_id": r[0],
            "exam_id": r[1],
            "question_text": r[2],
            "marks": r[3],
            "paper_id": r[4],
            "topic_id": r[5],
        }
        for r in rows
    ]


def build_batch_requests(questions: list) -> list:
    requests = []
    for q in questions:
        marks_note = f" [{q['marks']} marks]" if q["marks"] else ""
        user_content = f"Question{marks_note}:\n{q['question_text']}"
        requests.append({
            "custom_id": q["question_id"],
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_content}],
            },
        })
    return requests


def submit_batch(client: anthropic.Anthropic, requests: list) -> str:
    batch = client.messages.batches.create(requests=requests)
    print(f"  Batch submitted: {batch.id} ({len(requests)} requests)")
    BATCH_ID_FILE.write_text(batch.id)
    return batch.id


def wait_for_batch(client: anthropic.Anthropic, batch_id: str) -> None:
    print("  Waiting for batch to complete (polls every 30s)...")
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(
            f"    Status: {batch.processing_status} | "
            f"succeeded={counts.succeeded} errored={counts.errored} processing={counts.processing}"
        )
        if batch.processing_status == "ended":
            break
        time.sleep(30)


def parse_rubric(raw_text: str):
    raw_text = raw_text.strip()
    # Strip markdown fences if present (L-14)
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def insert_rubrics(conn: sqlite3.Connection, client: anthropic.Anthropic, batch_id: str):
    inserted = 0
    errors = 0

    for result in client.messages.batches.results(batch_id):
        qid = result.custom_id

        if result.result.type == "error":
            print(f"  ERROR for {qid}: {result.result.error}")
            errors += 1
            continue

        raw = result.result.message.content[0].text
        rubric = parse_rubric(raw)

        if rubric is None:
            print(f"  PARSE ERROR for {qid}: {repr(raw[:100])}")
            errors += 1
            continue

        rubric_points = json.dumps(rubric.get("rubric_points", []))
        key_terms = json.dumps(rubric.get("key_terms", []))
        diagram_expected = int(bool(rubric.get("diagram_expected", 0)))
        diagram_type = rubric.get("diagram_type") or None

        conn.execute("""
            INSERT OR IGNORE INTO question_rubrics
                (question_id, exam_id, rubric_points, key_terms,
                 diagram_expected, diagram_type, extractor_model, extracted_at)
            VALUES (?, ?, ?, ?, ?, ?, 'claude-haiku-4-5-20251001', datetime('now'))
        """, (qid, EXAM_ID, rubric_points, key_terms, diagram_expected, diagram_type))
        inserted += 1

    conn.commit()
    return inserted, errors


def verify(conn: sqlite3.Connection) -> None:
    total_q = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]
    total_r = conn.execute(
        "SELECT COUNT(*) FROM question_rubrics WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]
    with_diagram = conn.execute(
        "SELECT COUNT(*) FROM question_rubrics WHERE exam_id=? AND diagram_expected=1", (EXAM_ID,)
    ).fetchone()[0]

    print("\n── UPSC Stage 8 Sense Check ─────────────────────────")
    print(f"Total PYQs          : {total_q}")
    print(f"Rubrics extracted   : {total_r}")
    print(f"Diagram expected    : {with_diagram} ({100*with_diagram//total_r if total_r else 0}%)")
    print(f"Missing rubrics     : {total_q - total_r}")

    assert total_r >= total_q * 0.95, f"Only {total_r}/{total_q} rubrics extracted"
    print("\n✓ UPSC Stage 8 passed")
    print("─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print("DB not found. Run init_db.py first.")
        raise SystemExit(1)

    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()

    # Check if resuming an existing batch
    if BATCH_ID_FILE.exists():
        batch_id = BATCH_ID_FILE.read_text().strip()
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Resuming batch {batch_id} (status: {batch.processing_status})")
    else:
        questions = load_pending_questions(conn)
        if not questions:
            print("All questions already have rubrics. Running verify...")
            verify(conn)
            conn.close()
            raise SystemExit(0)

        print(f"Submitting {len(questions)} questions to Haiku batch API...")
        requests = build_batch_requests(questions)
        batch_id = submit_batch(client, requests)

    wait_for_batch(client, batch_id)

    print("Processing results...")
    inserted, errors = insert_rubrics(conn, client, batch_id)
    print(f"  Inserted: {inserted} | Errors: {errors}")

    # Clean up batch id file on success
    if errors == 0 and BATCH_ID_FILE.exists():
        BATCH_ID_FILE.unlink()

    verify(conn)
    conn.close()
