"""
Fix the 5 batch topics that failed JSON parsing due to literal newlines / bad escapes.
Extracts each question object individually using a field-by-field regex fallback.
"""
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "web"))
from db import load_api_key

import anthropic

DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"
BATCH_ID_FILE = Path(__file__).parent.parent.parent / "data" / "rbi_mcq_batch.txt"

FAILED_TOPICS = {
    "macro__money_banking":        ("macro",     "money_banking"),
    "intl_econ__mundell_fleming":  ("intl_econ", "mundell_fleming"),
    "macro__is_lm":                ("macro",     "is_lm"),
    "macro__qtm_monetary":         ("macro",     "qtm_monetary"),
    "micro__market_structures":    ("micro",     "market_structures"),
}

REQUIRED = {"id", "question", "option_a", "option_b", "option_c", "option_d",
            "correct_option", "explanation"}


def sanitize_json(raw: str) -> str:
    """Strip fences, replace literal newlines inside strings with \\n."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    # Replace literal newlines inside JSON string values
    # Strategy: replace \n that appear between quotes with \\n
    def fix_string_newlines(m):
        s = m.group(0)
        s = s.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        return s

    # Match JSON string values (between double quotes, handling escaped quotes)
    raw = re.sub(r'"(?:[^"\\]|\\.)*"', fix_string_newlines, raw, flags=re.DOTALL)
    return raw


def extract_field(text: str, field: str) -> str:
    """Extract a single field value from a JSON object fragment."""
    pattern = rf'"{re.escape(field)}"\s*:\s*"((?:[^"\\]|\\.)*)"|"{re.escape(field)}"\s*:\s*(\d+)'
    m = re.search(pattern, text, re.DOTALL)
    if not m:
        return ""
    val = m.group(1) if m.group(1) is not None else m.group(2)
    try:
        return json.loads(f'"{val}"')
    except Exception:
        return val


def extract_objects_individually(raw: str) -> list:
    """Split into top-level objects and parse each one independently."""
    # First try the sanitized full parse
    try:
        sanitized = sanitize_json(raw)
        return json.loads(sanitized)
    except json.JSONDecodeError:
        pass

    # Fall back: extract each {...} block and parse individually
    objects = []
    depth = 0
    start = None
    in_string = False
    escape_next = False

    for i, ch in enumerate(raw):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                fragment = raw[start:i + 1]
                # Try to parse this object
                try:
                    obj = json.loads(fragment)
                    objects.append(obj)
                except json.JSONDecodeError:
                    # Try sanitizing just this fragment
                    try:
                        san = sanitize_json(fragment)
                        obj = json.loads(san)
                        objects.append(obj)
                    except json.JSONDecodeError:
                        # Last resort: extract fields by regex
                        obj = extract_by_regex(fragment)
                        if obj:
                            objects.append(obj)
                start = None

    return objects


def extract_by_regex(fragment: str) -> dict:
    """Field-by-field regex extraction for a malformed JSON object."""
    fields = ["id", "question", "option_a", "option_b", "option_c", "option_d",
              "correct_option", "explanation", "subtopic", "dimension",
              "difficulty", "is_core_concept", "is_trap", "question_type"]
    obj = {}
    for field in fields:
        val = extract_field(fragment, field)
        if val:
            obj[field] = val
    return obj if REQUIRED.issubset(obj.keys()) else {}


def validate_and_insert(conn, questions, subject, topic):
    bw_row = conn.execute("SELECT base_weight FROM rbi_topic_weights WHERE topic=?", (topic,)).fetchone()
    inserted = 0
    for q in questions:
        if not REQUIRED.issubset(q.keys()):
            continue
        if q.get("correct_option") not in ("A", "B", "C", "D"):
            continue
        try:
            conn.execute("""
                INSERT OR IGNORE INTO rbi_questions
                (id, question, option_a, option_b, option_c, option_d,
                 correct_option, explanation, subject, topic, subtopic,
                 dimension, tier, difficulty, is_core_concept, is_recent_dev,
                 is_trap, question_type, tags)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,0,?,?,?)
            """, (
                q["id"], q["question"],
                q["option_a"], q["option_b"], q["option_c"], q["option_d"],
                q["correct_option"], q["explanation"],
                subject, topic,
                q.get("subtopic", ""),
                q.get("dimension", "definition"),
                q.get("difficulty", "medium"),
                int(bool(q.get("is_core_concept", 0))),
                int(bool(q.get("is_trap", 0))),
                q.get("question_type", "standard"),
                json.dumps(q.get("tags", [])),
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


def main():
    os.environ.setdefault("ANTHROPIC_API_KEY", load_api_key())
    client = anthropic.Anthropic()
    conn = sqlite3.connect(DB_PATH)

    batch_id = BATCH_ID_FILE.read_text().strip()
    total_inserted = 0
    total_errors = 0

    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if cid not in FAILED_TOPICS:
            continue

        subject, topic = FAILED_TOPICS[cid]
        raw = result.result.message.content[0].text

        questions = extract_objects_individually(raw)
        if not questions:
            print(f"STILL FAILED: {cid} — no objects extracted")
            total_errors += 1
            continue

        n = validate_and_insert(conn, questions, subject, topic)
        print(f"  {cid}: {len(questions)} extracted, {n} inserted")
        total_inserted += n

    # Seed mastery rows for newly inserted topics
    topics = conn.execute(
        "SELECT DISTINCT topic, subject FROM rbi_questions"
    ).fetchall()
    for topic, subject in topics:
        conn.execute(
            "INSERT OR IGNORE INTO rbi_topic_mastery (user_id, topic, subject) VALUES ('rahul',?,?)",
            (topic, subject),
        )
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM rbi_questions").fetchone()[0]
    conn.close()

    print(f"\nFixed: {total_inserted} questions inserted. DB total: {total}")
    if total_errors:
        print(f"Still failed: {total_errors} topics")


if __name__ == "__main__":
    main()
