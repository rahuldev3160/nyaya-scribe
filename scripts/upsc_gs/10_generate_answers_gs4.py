"""
Stage 10 (UPSC GS-Mains): Generate model answers for GS4 (Ethics, Integrity & Aptitude)
PYQs via Sonnet Batch API. Part of the 2027 redesign, PLAN-021 Area 3.

Scope note (2026-08-30): of 93 raw gs4 rows, 12 were excluded after manual review --
5 are pure junk (YouTube playlist links / nav text, same class as BUG-035's gs1-3
contamination but far rarer here), 7 are multiple case-study titles concatenated into
one row (incoherent as a single question). The remaining 81 include a mix of full real
case narratives and short title-only stems (e.g. "Case-Study: Leaking information ()")
-- for the latter, the model is told to write an illustrative framework answer for that
dilemma type rather than inventing fake specific facts. This is a practice/framework
aid, not a precise answer to a fully-specified real exam scenario, for the stem-only
rows. gs1-3 are NOT touched by this script -- BUG-035 blocks them entirely.

Run: python3 scripts/upsc_gs/10_generate_answers_gs4.py
"""
import argparse
import json
import sqlite3
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import anthropic

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_gs.db"
BATCH_ID_FILE = Path(__file__).parent.parent.parent / "data" / "gs4_answers_batch.txt"
CACHE_DIR = Path(__file__).parent.parent.parent / "cache" / "gs4_answer_batch_results"
EXAM_ID = "upsc_gs_mains"
PAPER_ID = "gs4"

# Excluded 2026-08-30 -- see scope note above.
JUNK_IDS = {
    "gs4_2025_q07", "gs4_2024_q01", "gs4_2024_q09", "gs4_2023_q09", "gs4_2022_q07",
}
JUMBLED_IDS = {
    "gs4_2024_q03", "gs4_2020_q05", "gs4_2019_q02", "gs4_2016_q03",
    "gs4_2016_q05", "gs4_2016_q09", "gs4_2013_q04",
}
EXCLUDE_IDS = JUNK_IDS | JUMBLED_IDS

FULL_CASE_MIN_CHARS = 150  # below this, treat as a title-only stem

SYSTEM_PROMPT = """You are an expert UPSC GS4 (Ethics, Integrity & Aptitude) Mains coach.

Two kinds of input you'll see, marked explicitly in the user message:

1. FULL CASE — the complete real case narrative (facts, dilemma, sub-questions) is given.
   Answer it directly and specifically using those exact facts.

2. TITLE-ONLY STEM — only a short case title or theme is given (e.g. "Leaking information",
   "Wife-beater boss"), not the full scenario. In this situation, DO NOT invent fake specific
   facts and present them as if they were the real exam's facts. Instead write an
   ILLUSTRATIVE FRAMEWORK ANSWER: briefly sketch a plausible, realistic scenario consistent
   with the title (clearly as an example, not asserted as the real exam text), then show how
   to reason through that TYPE of dilemma using ethical frameworks. The value is in
   demonstrating the reasoning process and structure, not in fabricated specific facts.

For both types, use this structure:
- Identify all stakeholders and their interests
- Articulate the core ethical tension/dilemma clearly
- Apply relevant ethical frameworks (consequentialism, deontology, virtue ethics, public
  service values) to analyze the options
- State and justify a decided course of action
- Give a practical execution plan with safeguards

Return ONLY valid JSON (no markdown, no explanation):
{
  "intro_text": "<stakeholders + core ethical tension, 2-4 sentences>",
  "body_text": "<multi-framework analysis of options, the bulk of the answer>",
  "conclusion_text": "<decided course of action + execution plan + safeguards>",
  "diagram_mode": "omitted",
  "diagram_type": null,
  "diagram_description": null,
  "diagram_labels": [],
  "data_points": [],
  "schemes_referenced": [],
  "key_terms_used": ["<ethical concept or thinker cited>"]
}

Be specific, pragmatic, and decisive -- no fence-sitting. Cite 1-2 relevant thinkers
(Aristotle, Kant, Gandhi, Rawls, Kautilya, etc.) with brief context where it strengthens
the analysis. Target ~250-350 words total for a 10-mark question, ~400-500 for 20-mark."""


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


def load_pending(conn: sqlite3.Connection, test_mode=False) -> list:
    placeholders = ",".join("?" * len(EXCLUDE_IDS))
    rows = conn.execute(f"""
        SELECT q.question_id, q.question_text, q.marks, q.year, q.topic_id
        FROM pyq_questions q
        LEFT JOIN model_answers ma ON q.question_id = ma.question_id AND q.exam_id = ma.exam_id
        WHERE q.exam_id = ? AND q.paper_id = ? AND ma.question_id IS NULL
          AND q.question_id NOT IN ({placeholders})
        ORDER BY q.year DESC, q.question_id
    """, (EXAM_ID, PAPER_ID, *EXCLUDE_IDS)).fetchall()
    result = [
        {"question_id": r[0], "question_text": r[1], "marks": r[2], "year": r[3], "topic_id": r[4]}
        for r in rows
    ]
    if test_mode:
        # One short (title-only) + one long (full-case) sample, so both prompt
        # branches get exercised before the real batch runs.
        short = next((q for q in result if len(q["question_text"]) < FULL_CASE_MIN_CHARS), None)
        long_ = next((q for q in result if len(q["question_text"]) >= FULL_CASE_MIN_CHARS), None)
        return [q for q in (short, long_) if q]
    return result


def build_user_prompt(q: dict) -> str:
    is_full_case = len(q["question_text"]) >= FULL_CASE_MIN_CHARS
    kind = "FULL CASE" if is_full_case else "TITLE-ONLY STEM"
    marks_str = f"{q['marks']} marks" if q["marks"] else "marks unknown"
    return f"""[{kind}]

Question ({marks_str}, year {q['year']}, topic: {q['topic_id']}):
{q['question_text']}

Return the JSON answer."""


def build_batch_requests(questions: list) -> list:
    return [
        {
            "custom_id": q["question_id"],
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": build_user_prompt(q)}],
            },
        }
        for q in questions
    ]


def parse_answer(raw_text: str):
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        parts = raw_text.split("```")
        raw_text = parts[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            return json.loads(raw_text[raw_text.find("{"):raw_text.rfind("}") + 1])
        except (json.JSONDecodeError, ValueError):
            return None


def word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _fetch_and_cache_results(client: anthropic.Anthropic, batch_id: str) -> list:
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
                    rec = {"custom_id": result.custom_id, "type": result.result.type}
                    if result.result.type == "succeeded":
                        msg = result.result.message
                        rec["stop_reason"] = msg.stop_reason
                        rec["text"] = msg.content[0].text if msg.content else ""
                    else:
                        rec["error"] = str(result.result.error)
                else:
                    rec = {"custom_id": result.custom_id, "type": result.result.type, "error": "non-succeeded"}
                f.write(json.dumps(rec) + "\n")
                records.append(rec)
    except Exception:
        cache_file.unlink(missing_ok=True)
        raise
    print(f"  Cached {len(records)} results locally.")
    return records


def insert_answers(conn: sqlite3.Connection, client: anthropic.Anthropic, batch_id: str):
    inserted, errors = 0, 0
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
            ans.get("intro_text", ""), ans.get("body_text", ""), ans.get("conclusion_text", ""),
            ans.get("diagram_mode", "omitted"), ans.get("diagram_type"), ans.get("diagram_description"),
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
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=? AND paper_id=?", (EXAM_ID, PAPER_ID)
    ).fetchone()[0]
    total_a = conn.execute("""
        SELECT COUNT(*) FROM model_answers a
        JOIN pyq_questions q ON q.question_id=a.question_id AND q.exam_id=a.exam_id
        WHERE a.exam_id=? AND q.paper_id=?
    """, (EXAM_ID, PAPER_ID)).fetchone()[0]
    print("\n── GS4 Stage 10 Sense Check ─────────────────────────")
    print(f"gs4 total rows        : {total_q}")
    print(f"Excluded (junk+jumbled): {len(EXCLUDE_IDS)}")
    print(f"Answers generated      : {total_a}")
    print("──────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-mode", action="store_true", help="Run 2 sample questions only, no batch ID file, no cost commitment beyond ~2 calls.")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("DB not found.")
        raise SystemExit(1)

    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()

    if args.test_mode:
        questions = load_pending(conn, test_mode=True)
        print(f"TEST MODE: {len(questions)} sample questions, no batch file written.")
        requests = build_batch_requests(questions)
        batch = client.messages.batches.create(requests=requests)
        batch_id = batch.id
        print(f"  Test batch submitted: {batch_id} ({len(requests)} requests)")
    elif BATCH_ID_FILE.exists():
        batch_id = BATCH_ID_FILE.read_text().strip()
        batch = client.messages.batches.retrieve(batch_id)
        print(f"Resuming batch {batch_id} (status: {batch.processing_status})")
    else:
        questions = load_pending(conn)
        if not questions:
            print("All gs4 questions already have answers.")
            verify(conn)
            conn.close()
            raise SystemExit(0)

        print(f"Building {len(questions)} batch requests...")
        requests = build_batch_requests(questions)

        batch = client.messages.batches.create(requests=requests)
        batch_id = batch.id
        BATCH_ID_FILE.write_text(batch_id)
        print(f"  Batch submitted: {batch_id} ({len(requests)} requests)")

    print("Waiting for batch (polls every 30s)...")
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        c = batch.request_counts
        print(f"  {batch.processing_status} | done={c.succeeded + c.errored} processing={c.processing}")
        if batch.processing_status == "ended":
            break
        time.sleep(30)

    print("Processing results...")
    inserted, errors = insert_answers(conn, client, batch_id)
    print(f"  Inserted: {inserted} | Errors: {errors}")

    if errors == 0 and BATCH_ID_FILE.exists():
        BATCH_ID_FILE.unlink()

    verify(conn)
    conn.close()
