"""
Stage 4: Extract marking rubrics for all PYQs via Haiku Batch API.
Run: python3 scripts/generate_rubrics.py [--exam ies_2026|upsc_eco_opt|rbi_depr]

Reads pyq_questions, sends each to Haiku (batch), stores rubric_points JSON
in question_rubrics table. Skips questions already in question_rubrics.
Saves batch_id to data/{exam_id}_rubrics_batch.txt so the script is safe to restart.
"""
import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

import anthropic

EXAM_DB_MAP = {
    "ies_2026": "ies.db",
    "upsc_eco_opt": "upsc_eco_opt.db",
    "rbi_depr": "rbi.db",
}

SYSTEM_PROMPT = """You are an economics exam rubric extractor.
Given an economics question with its marks, extract a concise marking rubric.

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
- diagram_type: if diagram_expected=1, one of: demand_supply_curve | production_function | is_lm_curve | lorenz_curve | phillips_curve | indifference_curve | flow_chart | bar_chart | table | growth_model | other
- key_terms: 4-8 economics terms that a good answer must include"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def load_pending_questions(conn: sqlite3.Connection, exam_id: str) -> list[dict]:
    rows = conn.execute("""
        SELECT q.question_id, q.exam_id, q.question_text, q.marks, q.paper_id, q.topic_id
        FROM pyq_questions q
        LEFT JOIN question_rubrics r ON q.question_id = r.question_id AND q.exam_id = r.exam_id
        WHERE q.exam_id = ? AND r.question_id IS NULL
        ORDER BY q.paper_id, q.question_id
    """, (exam_id,)).fetchall()

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


def build_batch_requests(questions: list[dict]) -> list[dict]:
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


def submit_batch(client: anthropic.Anthropic, requests: list[dict], batch_id_file: Path) -> str:
    batch = client.messages.batches.create(requests=requests)
    print(f"  Batch submitted: {batch.id} ({len(requests)} requests)")
    batch_id_file.write_text(batch.id)
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
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def insert_rubrics(conn: sqlite3.Connection, client: anthropic.Anthropic, batch_id: str, exam_id: str) -> tuple[int, int]:
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
        """, (qid, exam_id, rubric_points, key_terms, diagram_expected, diagram_type))
        inserted += 1

    conn.commit()
    return inserted, errors


def verify(conn: sqlite3.Connection, exam_id: str) -> None:
    total_q = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=?", (exam_id,)
    ).fetchone()[0]
    total_r = conn.execute(
        "SELECT COUNT(*) FROM question_rubrics WHERE exam_id=?", (exam_id,)
    ).fetchone()[0]
    with_diagram = conn.execute(
        "SELECT COUNT(*) FROM question_rubrics WHERE exam_id=? AND diagram_expected=1", (exam_id,)
    ).fetchone()[0]

    print("\n── Stage 4 Sense Check ──────────────────────────")
    print(f"Total PYQs          : {total_q}")
    print(f"Rubrics extracted   : {total_r}")
    print(f"Diagram expected    : {with_diagram} ({100*with_diagram//total_r if total_r else 0}%)")
    print(f"Missing rubrics     : {total_q - total_r}")

    assert total_r >= total_q * 0.95, f"Only {total_r}/{total_q} rubrics extracted"
    print("\n✓ Stage 4 passed")
    print("─────────────────────────────────────────────────\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate rubrics via Haiku Batch API")
    parser.add_argument(
        "--exam",
        default="ies_2026",
        choices=list(EXAM_DB_MAP.keys()),
        help="Exam ID (default: ies_2026)",
    )
    args = parser.parse_args()

    exam_id = args.exam
    db_path = Path(__file__).parent.parent / "data" / EXAM_DB_MAP[exam_id]
    batch_id_file = Path(__file__).parent.parent / "data" / f"{exam_id}_rubrics_batch.txt"

    if not db_path.exists():
        print(f"DB not found: {db_path}. Run init_db.py first.")
        raise SystemExit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        env_path = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / ".env"
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break

    if not api_key:
        print("ANTHROPIC_API_KEY not found")
        raise SystemExit(1)

    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection(db_path)

    if batch_id_file.exists():
        batch_id = batch_id_file.read_text().strip()
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Resuming batch {batch_id} (status: {batch.processing_status})")
    else:
        questions = load_pending_questions(conn, exam_id)
        if not questions:
            print("All questions already have rubrics. Running verify...")
            verify(conn, exam_id)
            conn.close()
            raise SystemExit(0)

        print(f"Submitting {len(questions)} questions to Haiku batch API...")
        requests = build_batch_requests(questions)
        batch_id = submit_batch(client, requests, batch_id_file)

    wait_for_batch(client, batch_id)

    print("Processing results...")
    inserted, errors = insert_rubrics(conn, client, batch_id, exam_id)
    print(f"  Inserted: {inserted} | Errors: {errors}")

    if errors == 0 and batch_id_file.exists():
        batch_id_file.unlink()

    verify(conn, exam_id)
    conn.close()
