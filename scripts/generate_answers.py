"""
Stage 5: Generate model answers for all PYQs via Sonnet Batch API.
Run: python3 scripts/generate_answers.py [--paper ge_04]

Reads pyq_questions + question_rubrics, generates structured model answers.
For GE-03/GE-04: augments prompts with relevant Economic Survey / Budget
chunks from Devthorium ChromaDB.
Saves batch_id to data/answers_batch.txt for restart safety.
"""
import argparse
import json
import os
import sqlite3
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import anthropic
import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
BATCH_ID_FILE = Path(__file__).parent.parent / "data" / "answers_batch.txt"
EXAM_ID = "ies_2026"
CHROMA_PATH = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / "vector_store"

SYSTEM_PROMPT = """You are an expert IES (Indian Economic Service) exam answer writer.
Your task: produce a structured model answer that would score full marks.

Writing standards for IES:
- Intro: define core concepts, state the scope of the answer
- Body: analytical depth, use diagrams/graphs/bullet points where they add clarity, include data + schemes
- Conclusion: policy implications, way forward, evaluative statement
- Use the rubric points as a checklist — ensure each is addressed
- Include relevant government schemes, committees, economic data
- Diagrams must be textually described with axes, curves, key points labeled
- Keep to the word limit; IES values precision over padding

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

WC_GUIDE = {
    (0, 7): (25, 55, 20),     # ≤6 marks: 100 words
    (7, 12): (35, 90, 25),    # 7-11 marks: 150 words
    (12, 18): (50, 140, 30),  # 12-17 marks: 220 words
    (18, 25): (60, 190, 40),  # 18-24 marks: 290 words
    (25, 999): (80, 340, 80), # ≥25 marks: 500 words
}


def get_wc_guide(marks):
    if not marks:
        return WC_GUIDE[(7, 12)]
    for (lo, hi), guide in WC_GUIDE.items():
        if lo <= marks < hi:
            return guide
    return WC_GUIDE[(7, 12)]


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


def load_pending(conn: sqlite3.Connection, paper_filter=None) -> list[dict]:
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


def build_chroma_retriever():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection("upsc_content")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def retrieve(query_text: str, n=4) -> list[str]:
        emb = embedder.encode([query_text]).tolist()
        results = collection.query(
            query_embeddings=emb,
            n_results=n,
            where={"subject_id": "economy"},
        )
        return results["documents"][0]

    return retrieve


def build_user_prompt(q: dict, context_chunks: list[str]) -> str:
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
        diagram_str = f'\nDiagram expected: YES — type hint: {dt}\nSet diagram_mode to "described" and fill diagram_description with axes, curves, labels, and what each shift/point represents.'

    context_str = ""
    if context_chunks:
        context_str = "\n\nReference context (Economic Survey / Budget data — use relevant facts):\n"
        context_str += "\n---\n".join(f"[{i+1}] {c[:400]}" for i, c in enumerate(context_chunks))

    return f"""Question ({marks_str}):
{q['question_text']}

Word count guide: {wc_str}

Marking rubric:
{rubric_str}

Key terms to include: {key_terms_str}{diagram_str}{context_str}"""


def build_batch_requests(questions: list[dict], retrieve_fn) -> list[dict]:
    requests = []
    rag_papers = {"ge_03", "ge_04"}

    for q in questions:
        if q["paper_id"] in rag_papers and retrieve_fn:
            chunks = retrieve_fn(q["question_text"], n=4)
        else:
            chunks = []

        user_content = build_user_prompt(q, chunks)
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


def insert_answers(conn: sqlite3.Connection, client: anthropic.Anthropic, batch_id: str) -> tuple[int, int]:
    inserted = 0
    errors = 0

    for result in client.messages.batches.results(batch_id):
        qid = result.custom_id

        if result.result.type == "error":
            print(f"  API ERROR {qid}: {result.result.error}")
            errors += 1
            continue

        if result.result.message.stop_reason == "max_tokens":
            print(f"  TRUNCATED {qid}")
            errors += 1
            continue

        raw = result.result.message.content[0].text
        ans = parse_answer(raw)

        if ans is None:
            print(f"  PARSE ERROR {qid}: {repr(raw[:80])}")
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

    print("\n── Stage 5 Sense Check ──────────────────────────")
    print("Answers by paper:")
    for pid, cnt in by_paper:
        print(f"  {pid}: {cnt}")
    print(f"Total answers       : {total_a}/{total_q}")
    print(f"With full diagram   : {with_diag}")
    print(f"Missing             : {total_q - total_a}")
    print("─────────────────────────────────────────────────\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", help="Restrict to a single paper e.g. ge_04")
    args = parser.parse_args()

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

        print(f"Loading ChromaDB retriever...")
        try:
            retrieve = build_chroma_retriever()
        except Exception as e:
            print(f"  ChromaDB unavailable ({e}), GE-03/04 will have no RAG context")
            retrieve = None

        print(f"Building {len(questions)} batch requests...")
        requests = build_batch_requests(questions, retrieve)

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
