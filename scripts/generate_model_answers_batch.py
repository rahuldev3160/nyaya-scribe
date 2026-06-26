#!/usr/bin/env python3
"""
Anthropic Batch API — generate model answers for UPSC essay + ethics questions.

Usage:
  python scripts/generate_model_answers_batch.py              # submit full batch (~315 items, ~$2.44)
  python scripts/generate_model_answers_batch.py --test-mode --count 4
  python scripts/generate_model_answers_batch.py --poll <batch_id>
  python scripts/generate_model_answers_batch.py --retrieve <batch_id>
"""

import argparse
import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH = Path("data/upsc_gs.db")
STATUS_FILE = Path("data/batch_model_answers_status.json")
MODEL = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

ESSAY_SYSTEM = """\
You are an expert UPSC essay coach. Generate a structured model answer for a UPSC Mains Essay paper question.

Your answer must follow the PART A/B/C essay framework:
- PART A (Introduction): Hook → Context → Thesis → Signpost (target 150-200 words)
- PART B (Body): 3-5 dimensions with challenges + solutions + synthesis (target 800-900 words)
- PART C (Conclusion): Synthesis → Way Forward → Philosophical reflection → Closing line (target 150-200 words)

Return ONLY a valid JSON object with these exact keys — no markdown, no prose outside the JSON:
{
  "intro_hook": "<opening hook, 1-2 sentences>",
  "intro_hook_type": "<one of: quote, stat, paradox, anecdote, definition>",
  "intro_context": "<contextual background, 2-3 sentences>",
  "intro_thesis": "<clear thesis statement, 1-2 sentences>",
  "intro_signpost": "<roadmap sentence, 1 sentence>",
  "body_dimensions_json": [
    {"dimension": "<name>", "content": "<2-3 paragraph discussion>", "evidence": "<example or data>"}
  ],
  "body_challenges": "<paragraph on key challenges/tensions>",
  "body_solutions": "<paragraph on solutions/way forward in body>",
  "body_synthesis_para": "<connecting paragraph tying dimensions together>",
  "concl_synthesis": "<synthesis of main arguments, 2-3 sentences>",
  "concl_way_forward": "<actionable way forward, 2-3 sentences>",
  "concl_philosophical": "<philosophical/values reflection, 2-3 sentences>",
  "concl_closing_line": "<memorable closing sentence>",
  "total_word_count": <integer>
}

Write at a level appropriate for UPSC Mains (IAS) — nuanced, evidence-based, balanced.\
"""

ETHICS_A_SYSTEM = """\
You are an expert UPSC GS4 Ethics coach. Generate a model answer for a GS4 Ethics Section A question using the IDEA-U framework:
- I (Interpretation/Definition): Define the concept precisely
- D (Dimensions/Aspects): Break down into key dimensions
- E (Evidence/Examples): Specific examples, thinker citations, case evidence
- A (Application): Apply to governance/administration/personal context
- U (Upshot/Conclusion): Key takeaway and significance

Return ONLY a valid JSON object with these exact keys — no markdown, no prose outside the JSON:
{
  "theory_intro": "<introduction and definition, 2-3 sentences>",
  "theory_dimensions": "<breakdown of key dimensions, 3-5 short paragraphs>",
  "theory_evidence": "<specific examples, thinker quotes, case evidence>",
  "theory_apply": "<application to governance/administration context>",
  "theory_upshot": "<conclusion and significance, 2-3 sentences>",
  "full_answer_text": "<complete prose answer combining all sections>",
  "thinkers_cited": ["<thinker name>"],
  "frameworks_used": ["IDEA-U"],
  "word_count": <integer>
}

Target word count: 150 for 10-mark, 200-250 for 15-mark, 300+ for 20-mark questions.
Cite 1-2 relevant thinkers (Aristotle, Kant, Gandhi, Rawls, Kautilya, etc.) with brief context.\
"""

ETHICS_B_SYSTEM = """\
You are an expert UPSC GS4 Ethics coach. Generate a model answer for a GS4 Ethics Section B case study using the STAKE framework:
- S (Stakeholders): Identify all affected parties and their interests
- T (Tension/Dilemma): Articulate the core ethical conflict clearly
- A (Analysis): Apply ethical frameworks (consequentialism, deontology, virtue ethics)
- K (Key Decision): State and justify the decided course of action
- E (Execution): Practical action plan with safeguards

Return ONLY a valid JSON object with these exact keys — no markdown, no prose outside the JSON:
{
  "stake_stakeholders": "<all stakeholders and their interests>",
  "stake_tension": "<core ethical tension or dilemma>",
  "stake_analysis": "<multi-framework ethical analysis>",
  "stake_decision": "<decided course of action with justification>",
  "stake_execution": "<practical implementation steps and safeguards>",
  "full_answer_text": "<complete prose answer combining all sections>",
  "thinkers_cited": ["<thinker name>"],
  "frameworks_used": ["STAKE"],
  "word_count": <integer>
}

Be specific, pragmatic, and decisive — no fence-sitting. Target 200-250 words per sub-part.\
"""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_essay_questions(conn, test_mode=False):
    rows = conn.execute("""
        SELECT q.essay_id, q.prompt, q.section, q.theme_tag, q.framework_id,
               q.word_limit, q.marks, q.year_appeared, q.content_type
        FROM essay_questions q
        LEFT JOIN essay_model_answers a ON a.essay_id = q.essay_id
        WHERE a.answer_id IS NULL
        ORDER BY q.content_type, q.year_appeared, q.essay_id
    """).fetchall()
    return rows[:1] if test_mode else rows


def load_ethics_questions(conn, test_mode=False):
    rows = conn.execute("""
        SELECT q.question_id, q.section, q.question_type, q.question_text,
               q.case_preamble, q.sub_part, q.marks, q.content_type,
               q.concept_tags, q.thinker_tags, q.framework_hint, q.paper_id,
               q.sequence_order
        FROM ethics_questions q
        LEFT JOIN ethics_model_answers a ON a.question_id = q.question_id
        WHERE a.answer_id IS NULL
          AND NOT (q.marks = 0 AND q.sub_part IS NULL)
        ORDER BY q.section, q.content_type, q.paper_id, q.sequence_order
    """).fetchall()
    if test_mode:
        a_rows = [r for r in rows if r["section"] == "A"][:2]
        b_rows = [r for r in rows if r["section"] == "B"][:1]
        return a_rows + b_rows
    return rows


def get_case_preamble(conn, question_id, paper_id):
    """Get parent case preamble for a Section B sub-part (a/b)."""
    if question_id and question_id[-1] in ("a", "b"):
        parent_id = question_id[:-1]
        row = conn.execute(
            "SELECT case_preamble FROM ethics_questions WHERE question_id = ?",
            (parent_id,)
        ).fetchone()
        if row and row["case_preamble"]:
            return row["case_preamble"]
    # Fallback: first context row of this paper
    row = conn.execute(
        "SELECT case_preamble FROM ethics_questions WHERE paper_id = ? AND section = 'B' AND sub_part IS NULL AND marks = 0 LIMIT 1",
        (paper_id,)
    ).fetchone()
    return row["case_preamble"] if row and row["case_preamble"] else ""


# ---------------------------------------------------------------------------
# Request builders
# ---------------------------------------------------------------------------

def build_essay_request(q, cid):
    prompt = (
        f"Generate a model UPSC essay answer for this topic:\n\n"
        f"**Essay Topic:** {q['prompt']}\n"
        f"**Section:** {q['section'] or 'Unknown'}\n"
        f"**Theme:** {q['theme_tag'] or 'General'}\n"
        f"**Word limit:** {q['word_limit'] or 1200} words\n"
        f"**Marks:** {q['marks'] or 125}\n"
        + (f"**Year appeared:** {q['year_appeared']}\n" if q["year_appeared"] else "")
        + "\nReturn the JSON answer."
    )
    return Request(
        custom_id=cid,
        params=MessageCreateParamsNonStreaming(
            model=MODEL,
            max_tokens=4096,
            system=ESSAY_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        ),
    )


def build_ethics_a_request(q, cid):
    marks = q["marks"]
    word_target = 150 if marks <= 10 else (250 if marks <= 15 else 350)
    prompt = (
        f"Generate a model UPSC GS4 Ethics Section A answer.\n\n"
        f"**Question:** {q['question_text']}\n"
        f"**Marks:** {marks} (target ~{word_target} words)\n"
        + (f"**Key concepts:** {q['concept_tags']}\n" if q["concept_tags"] else "")
        + (f"**Relevant thinkers:** {q['thinker_tags']}\n" if q["thinker_tags"] else "")
        + "\nApply the IDEA-U framework and return the JSON answer."
    )
    return Request(
        custom_id=cid,
        params=MessageCreateParamsNonStreaming(
            model=MODEL,
            max_tokens=2048,
            system=ETHICS_A_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        ),
    )


def build_ethics_b_request(q, preamble, cid):
    prompt = (
        f"Generate a model UPSC GS4 Ethics Section B case study answer.\n\n"
        f"**Case Scenario:**\n{preamble}\n\n"
        f"**Sub-part {(q['sub_part'] or '').upper()}:** {q['question_text']}\n"
        f"**Marks:** {q['marks']}\n"
        "\nApply the STAKE framework and return the JSON answer."
    )
    return Request(
        custom_id=cid,
        params=MessageCreateParamsNonStreaming(
            model=MODEL,
            max_tokens=4096,
            system=ETHICS_B_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        ),
    )


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------

def submit_batch(test_mode=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    essay_qs = load_essay_questions(conn, test_mode)
    ethics_qs = load_ethics_questions(conn, test_mode)

    print(f"Essay questions to generate:  {len(essay_qs)}")
    print(f"Ethics questions to generate: {len(ethics_qs)}")
    total = len(essay_qs) + len(ethics_qs)
    if total == 0:
        print("Nothing to generate — all answers already exist.")
        conn.close()
        return

    requests = []
    id_map = {}  # custom_id → {"type": "essay"|"ethics", "id": "<question_id>"}

    for i, q in enumerate(essay_qs):
        cid = f"essay_{i:04d}"
        id_map[cid] = {"type": "essay", "id": q["essay_id"]}
        requests.append(build_essay_request(q, cid))

    for i, q in enumerate(ethics_qs):
        cid = f"ethics_{i:04d}"
        id_map[cid] = {"type": "ethics", "id": q["question_id"]}
        if q["section"] == "A":
            requests.append(build_ethics_a_request(q, cid))
        else:
            preamble = get_case_preamble(conn, q["question_id"], q["paper_id"])
            requests.append(build_ethics_b_request(q, preamble, cid))

    conn.close()

    print(f"\nSubmitting {total} requests to Anthropic Batch API (model: {MODEL})...")
    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)

    # Record generation batch in DB
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR IGNORE INTO essay_generation_batches
        (batch_id, batch_type, generation_year, essay_count, model_used, status, started_at)
        VALUES (?, ?, ?, ?, ?, 'running', datetime('now'))
    """, (batch.id, "practice" if test_mode else "pyq", datetime.now().year, len(essay_qs), MODEL))
    conn.commit()
    conn.close()

    status = {
        "batch_id": batch.id,
        "submitted_at": datetime.now().isoformat(),
        "essay_count": len(essay_qs),
        "ethics_count": len(ethics_qs),
        "total": total,
        "test_mode": test_mode,
        "processing_status": batch.processing_status,
        "id_map": id_map,
    }
    STATUS_FILE.write_text(json.dumps(status, indent=2))
    print(f"\nBatch submitted: {batch.id}")
    print(f"Status + ID map saved to: {STATUS_FILE}")
    print(f"\nPoll:     python {sys.argv[0]} --poll {batch.id}")
    print(f"Retrieve: python {sys.argv[0]} --retrieve {batch.id}")


# ---------------------------------------------------------------------------
# Poll
# ---------------------------------------------------------------------------

def poll_batch(batch_id):
    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id)
    c = batch.request_counts
    print(f"Status:      {batch.processing_status}")
    print(f"Processing:  {c.processing}")
    print(f"Succeeded:   {c.succeeded}")
    print(f"Errored:     {c.errored}")
    print(f"Canceled:    {c.canceled}")
    print(f"Expired:     {c.expired}")
    if batch.processing_status == "ended":
        print(f"\nComplete — run: python {sys.argv[0]} --retrieve {batch_id}")


# ---------------------------------------------------------------------------
# Retrieve + insert
# ---------------------------------------------------------------------------

def _parse_json(text):
    """Extract JSON from model output — handles raw JSON, ```json blocks, or leading/trailing prose."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown fences (greedy removal handles multi-line JSON inside fences)
    stripped = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # Last resort: extract outermost { ... } (handles leading prose)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError("No valid JSON found in response")


def retrieve_results(batch_id):
    if not STATUS_FILE.exists():
        sys.exit(f"Status file not found: {STATUS_FILE}. Did you run --submit with this batch?")

    status = json.loads(STATUS_FILE.read_text())
    id_map = status.get("id_map", {})

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        print(f"Not complete yet. Status: {batch.processing_status}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    essay_ok = ethics_ok = errors = 0

    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type != "succeeded":
            print(f"SKIP {cid}: {result.result.type}")
            errors += 1
            continue

        try:
            data = _parse_json(result.result.message.content[0].text)
        except (ValueError, IndexError) as e:
            print(f"PARSE ERROR {cid}: {e}")
            errors += 1
            continue

        meta = id_map.get(cid, {})
        rtype = meta.get("type")
        rid = meta.get("id")

        if not rid:
            print(f"UNKNOWN custom_id {cid} — not in id_map")
            errors += 1
            continue

        answer_id = f"ans_{uuid.uuid4().hex[:12]}"

        if rtype == "essay":
            dims = data.get("body_dimensions_json", [])
            conn.execute("""
                INSERT OR IGNORE INTO essay_model_answers
                (answer_id, essay_id, intro_hook, intro_hook_type, intro_context,
                 intro_thesis, intro_signpost, body_dimensions_json,
                 body_challenges, body_solutions, body_synthesis_para,
                 concl_synthesis, concl_way_forward, concl_philosophical,
                 concl_closing_line, total_word_count, generation_model, batch_id)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                answer_id, rid,
                data.get("intro_hook", ""), data.get("intro_hook_type", "quote"),
                data.get("intro_context", ""), data.get("intro_thesis", ""),
                data.get("intro_signpost", ""),
                json.dumps(dims) if isinstance(dims, list) else "[]",
                data.get("body_challenges", ""), data.get("body_solutions", ""),
                data.get("body_synthesis_para"),
                data.get("concl_synthesis", ""), data.get("concl_way_forward", ""),
                data.get("concl_philosophical", ""), data.get("concl_closing_line", ""),
                data.get("total_word_count"), MODEL, batch_id,
            ))
            essay_ok += 1

        elif rtype == "ethics":
            conn.execute("""
                INSERT OR IGNORE INTO ethics_model_answers
                (answer_id, question_id,
                 theory_intro, theory_dimensions, theory_evidence, theory_apply, theory_upshot,
                 stake_stakeholders, stake_tension, stake_analysis, stake_decision, stake_execution,
                 full_answer_text, word_count, thinkers_cited, frameworks_used, model_used)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                answer_id, rid,
                data.get("theory_intro"), data.get("theory_dimensions"),
                data.get("theory_evidence"), data.get("theory_apply"),
                data.get("theory_upshot"),
                data.get("stake_stakeholders"), data.get("stake_tension"),
                data.get("stake_analysis"), data.get("stake_decision"),
                data.get("stake_execution"),
                data.get("full_answer_text", ""),
                data.get("word_count"),
                json.dumps(data.get("thinkers_cited", [])),
                json.dumps(data.get("frameworks_used", [])),
                MODEL,
            ))
            ethics_ok += 1

    # Mark batch complete
    conn.execute(
        "UPDATE essay_generation_batches SET status = 'complete', completed_at = datetime('now') WHERE batch_id = ?",
        (batch_id,)
    )
    conn.commit()
    conn.close()

    print(f"\nInserted:")
    print(f"  Essay model answers:  {essay_ok}")
    print(f"  Ethics model answers: {ethics_ok}")
    if errors:
        print(f"  Errors / skipped:     {errors}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate UPSC essay + ethics model answers via Anthropic Batch API")
    parser.add_argument("--test-mode", action="store_true", help="Submit 4 items only (1 essay + 2 ethics-A + 1 ethics-B)")
    parser.add_argument("--count", type=int, default=4, help="(reserved for future use)")
    parser.add_argument("--poll", metavar="BATCH_ID", help="Poll batch processing status")
    parser.add_argument("--retrieve", metavar="BATCH_ID", help="Retrieve results and insert into DB")
    args = parser.parse_args()

    if args.poll:
        poll_batch(args.poll)
    elif args.retrieve:
        retrieve_results(args.retrieve)
    else:
        submit_batch(test_mode=args.test_mode)


if __name__ == "__main__":
    main()
