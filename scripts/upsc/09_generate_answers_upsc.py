"""
Stage 9 (UPSC): Generate model answers for all UPSC PYQs via Sonnet Batch API.
Run: python3 scripts/upsc/09_generate_answers_upsc.py [--paper upsc_paper1]

Reads pyq_questions + question_rubrics + reference_answers + economic_data_points,
generates structured model answers. Saves batch_id to data/upsc_answers_batch.txt
for restart safety.
"""
import argparse
import json
import sqlite3
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import anthropic

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc.db"
BATCH_ID_FILE = Path(__file__).parent.parent.parent / "data" / "upsc_answers_batch.txt"
CACHE_DIR = Path(__file__).parent.parent.parent / "cache" / "upsc_answer_batch_results"
EXAM_ID = "upsc_eco_opt"

SYSTEM_PROMPT = """You are an expert UPSC Economics Optional Mains exam answer writer.
Your task: produce a structured model answer that would score full marks.

Writing standards for UPSC Economics Optional Mains:
- Intro: define core concepts, state the scope of the answer
- Body: analytical depth, use diagrams/graphs/bullet points where they add clarity, include data + schemes
- Conclusion: policy implications, way forward, evaluative statement
- Use the rubric points as a checklist — ensure each is addressed
- Include relevant government schemes, committees, economic data
- Diagrams must be textually described with axes, curves, key points labeled
- Keep to the word limit; UPSC values precision over padding
- Express all equations and mathematical relationships using LaTeX syntax: $...$ for inline, $$...$$ for display equations.

Return ONLY valid JSON (no markdown, no explanation):
{
  "intro_text": "...",
  "body_text": "...",
  "conclusion_text": "...",
  "diagram_mode": "described|mentioned|omitted",
  "diagram_type": null,
  "diagram_description": null,
  "diagram_labels": [],
  "data_points": [{"value": "...", "source": "...", "flag_verify": false}],
  "schemes_referenced": [],
  "key_terms_used": []
}

diagram_mode rules:
- "described": Write full diagram description in diagram_description (axes, curves, labels, shifts)
- "mentioned": Only briefly note the diagram type in body_text
- "omitted": No diagram"""

# UPSC word count guide: 10m=150w, 15m=200w, 20m=300w; default 15m if NULL
WC_GUIDE = {
    (0, 12):   (30, 90, 30),    # <12 marks: ~150 words
    (12, 18):  (40, 120, 40),   # 12-17 marks: ~200 words
    (18, 25):  (60, 190, 50),   # 18-24 marks: ~300 words
    (25, 999): (80, 340, 80),   # >=25 marks: ~500 words
}
DEFAULT_WC = WC_GUIDE[(12, 18)]  # 15m default


def get_wc_guide(marks):
    if not marks:
        return DEFAULT_WC
    for (lo, hi), guide in WC_GUIDE.items():
        if lo <= marks < hi:
            return guide
    return DEFAULT_WC


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


def load_pending(conn: sqlite3.Connection, paper_filter=None) -> list:
    paper_clause = f"AND q.paper_id = '{paper_filter}'" if paper_filter else ""
    rows = conn.execute(f"""
        SELECT q.question_id, q.exam_id, q.question_text, q.marks,
               q.paper_id, q.topic_id, q.answer_length,
               r.rubric_points, r.key_terms, r.diagram_expected, r.diagram_type
        FROM pyq_questions q
        JOIN question_rubrics r ON q.question_id = r.question_id AND q.exam_id = r.exam_id
        LEFT JOIN model_answers ma ON q.question_id = ma.question_id AND q.exam_id = ma.exam_id
        WHERE q.exam_id = ? AND ma.question_id IS NULL {paper_clause}
        ORDER BY q.paper_id, q.marks DESC
    """, (EXAM_ID,)).fetchall()

    return [
        {
            "question_id": r[0], "exam_id": r[1], "question_text": r[2],
            "marks": r[3], "paper_id": r[4], "topic_id": r[5],
            "answer_length": r[6],
            "rubric_points": json.loads(r[7]) if r[7] else [],
            "key_terms": json.loads(r[8]) if r[8] else [],
            "diagram_expected": r[9], "diagram_type": r[10],
        }
        for r in rows
    ]


def get_reference_answer(conn: sqlite3.Connection, question_id: str):
    """Return reference answer text if available in reference_answers table."""
    try:
        row = conn.execute(
            "SELECT answer_text FROM reference_answers WHERE question_id = ? LIMIT 1",
            (question_id,)
        ).fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        # Table may not exist
        return None


def get_economic_data_points(conn: sqlite3.Connection, topic_id, n: int = 5) -> list:
    """Return top n economic data points for a topic_id."""
    if not topic_id:
        return []
    try:
        rows = conn.execute("""
            SELECT indicator, value, context_text, source
            FROM economic_data_points
            WHERE exam_id = ? AND topic_id = ?
            LIMIT ?
        """, (EXAM_ID, topic_id, n)).fetchall()
        return [
            {"indicator": r[0], "value": r[1], "context": r[2], "source": r[3]}
            for r in rows
        ]
    except sqlite3.OperationalError:
        return []


def build_user_prompt(q: dict, ref_answer, data_points: list) -> str:
    marks_str = f"{q['marks']} marks" if q['marks'] else "marks unknown"
    wc = get_wc_guide(q['marks'])
    wc_str = f"intro ~{wc[0]}w | body ~{wc[1]}w | conclusion ~{wc[2]}w"
    if q.get("answer_length"):
        wc_str += f" (total target: {q['answer_length']} words)"

    rubric_str = "\n".join(
        f"  [{p['category']}|{p['section_hint']}|wt={p['weight']}] {p['point']}"
        for p in q["rubric_points"]
    )
    key_terms_str = ", ".join(q["key_terms"])

    diagram_str = ""
    if q["diagram_expected"]:
        dt = q["diagram_type"] or "relevant diagram"
        diagram_str = (
            f'\nDiagram expected: YES — type hint: {dt}\n'
            f'Set diagram_mode to "described" and fill diagram_description with '
            f'axes, curves, labels, and what each shift/point represents.'
        )

    ref_str = ""
    if ref_answer:
        ref_str = (
            "\n\nReference answer available — use as context but write a fresh, "
            "improved version:\n"
            f"{ref_answer[:800]}"
        )

    data_str = ""
    if data_points:
        data_str = "\n\nEconomic data points to consider (cite relevant ones):\n"
        for dp in data_points:
            data_str += f"  - {dp['indicator']}: {dp['value']} (Source: {dp['source']})\n"
            if dp.get("context"):
                data_str += f"    Context: {dp['context'][:120]}\n"

    return f"""Question ({marks_str}):
{q['question_text']}

Word count guide: {wc_str}

Marking rubric:
{rubric_str}

Key terms to include: {key_terms_str}{diagram_str}{ref_str}{data_str}"""


def build_batch_requests(questions: list, conn: sqlite3.Connection) -> list:
    requests = []

    for q in questions:
        ref_answer = get_reference_answer(conn, q["question_id"])
        data_points = get_economic_data_points(conn, q["topic_id"], n=5)
        user_content = build_user_prompt(q, ref_answer, data_points)

        requests.append({
            "custom_id": q["question_id"],
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 6000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_content}],
            },
        })

    return requests


def parse_answer(raw_text: str):
    raw_text = raw_text.strip()
    # Strip markdown fences (L-14)
    if raw_text.startswith("```"):
        parts = raw_text.split("```")
        raw_text = parts[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _fetch_and_cache_results(client: anthropic.Anthropic, batch_id: str) -> list:
    """Stream batch results from the API and save to a local JSONL file.
    On subsequent calls for the same batch_id, reads from local file instead."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{batch_id}.jsonl"

    if cache_file.exists():
        print(f"  Reading from local cache: {cache_file.name}")
        return [json.loads(line) for line in cache_file.read_text().splitlines() if line.strip()]

    print(f"  Fetching results from API and caching to {cache_file.name}...")
    records = []
    try:
        with cache_file.open("w") as f:
            for result in client.messages.batches.results(batch_id):
                if result.result.type in ("succeeded", "errored"):
                    rec = {
                        "custom_id": result.custom_id,
                        "type": result.result.type,
                    }
                    if result.result.type == "succeeded":
                        msg = result.result.message
                        rec["stop_reason"] = msg.stop_reason
                        rec["text"] = msg.content[0].text if msg.content else ""
                    else:
                        rec["error"] = str(result.result.error)
                else:
                    rec = {
                        "custom_id": result.custom_id,
                        "type": result.result.type,
                        "error": "non-succeeded",
                    }
                f.write(json.dumps(rec) + "\n")
                records.append(rec)
    except Exception:
        cache_file.unlink(missing_ok=True)
        raise
    print(f"  Cached {len(records)} results locally.")
    return records


def insert_answers(conn: sqlite3.Connection, client: anthropic.Anthropic, batch_id: str):
    inserted = 0
    errors = 0

    for rec in _fetch_and_cache_results(client, batch_id):
        qid = rec["custom_id"]

        if rec["type"] != "succeeded":
            print(f"  API ERROR {qid}: {rec.get('error', rec['type'])}")
            errors += 1
            continue

        if rec.get("stop_reason") == "max_tokens":
            print(f"  TRUNCATED {qid}")
            errors += 1
            continue

        ans = parse_answer(rec.get("text", ""))

        if ans is None:
            print(f"  PARSE ERROR {qid}: {repr(rec.get('text', '')[:80])}")
            errors += 1
            continue

        answer_id = f"ans_{qid}"
        conn.execute("""
            INSERT OR IGNORE INTO model_answers
                (answer_id, question_id, exam_id,
                 intro_text, body_text, conclusion_text,
                 diagram_mode, diagram_type, diagram_description,
                 diagram_labels, data_points, schemes_referenced, key_terms_used,
                 wc_intro, wc_body, wc_conclusion,
                 generator_model, generated_at, version)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'claude-sonnet-4-6',datetime('now'),1)
        """, (
            answer_id, qid, EXAM_ID,
            ans.get("intro_text", ""),
            ans.get("body_text", ""),
            ans.get("conclusion_text", ""),
            ans.get("diagram_mode", "omitted"),
            ans.get("diagram_type"),
            ans.get("diagram_description"),
            json.dumps(ans.get("diagram_labels") or []),
            json.dumps(ans.get("data_points") or []),
            json.dumps(ans.get("schemes_referenced") or []),
            json.dumps(ans.get("key_terms_used") or []),
            word_count(ans.get("intro_text", "")),
            word_count(ans.get("body_text", "")),
            word_count(ans.get("conclusion_text", "")),
        ))
        inserted += 1

    conn.commit()
    return inserted, errors


def verify(conn: sqlite3.Connection) -> None:
    total_q = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]
    total_a = conn.execute(
        "SELECT COUNT(*) FROM model_answers WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]

    by_paper = conn.execute("""
        SELECT q.paper_id, COUNT(a.answer_id)
        FROM pyq_questions q
        LEFT JOIN model_answers a ON q.question_id=a.question_id AND q.exam_id=a.exam_id
        WHERE q.exam_id=?
        GROUP BY q.paper_id ORDER BY q.paper_id
    """, (EXAM_ID,)).fetchall()

    with_diag = conn.execute(
        "SELECT COUNT(*) FROM model_answers WHERE exam_id=? AND diagram_mode='described'",
        (EXAM_ID,)
    ).fetchone()[0]

    print("\n── UPSC Stage 9 Sense Check ─────────────────────────")
    print("Answers by paper:")
    for pid, cnt in by_paper:
        print(f"  {pid}: {cnt}")
    print(f"Total answers       : {total_a}/{total_q}")
    print(f"With full diagram   : {with_diag}")
    print(f"Missing             : {total_q - total_a}")
    print("─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", help="Restrict to a single paper e.g. upsc_paper1")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("DB not found. Run init_db.py first.")
        raise SystemExit(1)

    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()

    if BATCH_ID_FILE.exists():
        batch_id = BATCH_ID_FILE.read_text().strip()
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Resuming batch {batch_id} (status: {batch.processing_status})")
    else:
        questions = load_pending(conn, args.paper)
        if not questions:
            print("All questions already have answers.")
            verify(conn)
            conn.close()
            raise SystemExit(0)

        print(f"Building {len(questions)} batch requests (with reference + data point context)...")
        requests = build_batch_requests(questions, conn)

        batch = client.messages.batches.create(requests=requests)
        batch_id = batch.id
        BATCH_ID_FILE.write_text(batch_id)
        print(f"  Batch submitted: {batch_id} ({len(requests)} requests)")

    print("Waiting for batch (polls every 60s)...")
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        c = batch.request_counts
        print(
            f"  {batch.processing_status} | "
            f"done={c.succeeded+c.errored} processing={c.processing}"
        )
        if batch.processing_status == "ended":
            break
        time.sleep(60)

    print("Processing results...")
    inserted, errors = insert_answers(conn, client, batch_id)
    print(f"  Inserted: {inserted} | Errors: {errors}")

    if errors == 0 and BATCH_ID_FILE.exists():
        BATCH_ID_FILE.unlink()

    verify(conn)
    conn.close()
