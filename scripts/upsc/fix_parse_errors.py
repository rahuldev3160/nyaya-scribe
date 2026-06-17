"""
Fix the 10 model answers that failed JSON parsing due to invalid LaTeX backslash
escapes (e.g. \alpha, \cdot, \frac) inside JSON strings.

Strategy:
  1. Read raw text from cache JSONL
  2. Strip markdown fences
  3. Fix invalid backslash escapes with regex before json.loads
  4. Fallback: extract fields individually with regex if json.loads still fails
  5. Insert into model_answers
"""
import json
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_eco_opt.db"
CACHE_FILE = Path(__file__).parent.parent.parent / "cache" / "upsc_answer_batch_results" / "msgbatch_01UKywnC3extuStyUiQX4eXs.jsonl"
EXAM_ID = "upsc_eco_opt"

FAILING = {
    "upsc_p1_0027", "upsc_p1_0084", "upsc_p1_0100", "upsc_p1_0328",
    "upsc_p1_0339", "upsc_p1_0395", "upsc_p1_0409", "upsc_p1_0414",
    "upsc_p2_0031", "upsc_p2_0130",
}


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence line (```json or ```)
        text = re.sub(r"^```[a-z]*\n?", "", text)
        # Remove closing fence
        text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def fix_backslashes(text: str) -> str:
    """Double-escape backslashes that are not valid JSON escape sequences."""
    # Valid JSON escapes after \: " \ / b f n r t u
    # We replace \X where X is NOT one of those with \\X
    return re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)


def parse_answer(raw_text: str):
    raw_text = strip_fences(raw_text)
    # First try: fix backslash escapes
    fixed = fix_backslashes(raw_text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    # Second try: replace any remaining \u followed by non-hex
    fixed2 = re.sub(r'\\u(?![0-9a-fA-F]{4})', r'\\\\u', fixed)
    try:
        return json.loads(fixed2)
    except json.JSONDecodeError:
        pass
    return None


def extract_field_fallback(raw_text: str, field: str) -> str:
    """Regex-based field extractor as last resort."""
    pattern = rf'"{field}"\s*:\s*"((?:[^"\\]|\\.)*)\"'
    m = re.search(pattern, raw_text, re.DOTALL)
    return m.group(1) if m else ""


def wc(text: str) -> int:
    return len(text.split()) if text else 0


def build_answer_from_fallback(raw_text: str) -> dict:
    """Extract individual fields when full JSON parse fails."""
    raw_text = strip_fences(raw_text)
    fields = ["intro_text", "body_text", "conclusion_text",
              "diagram_mode", "diagram_type", "diagram_description"]
    result = {}
    for f in fields:
        result[f] = extract_field_fallback(raw_text, f)

    # diagram_mode default
    if not result.get("diagram_mode"):
        result["diagram_mode"] = "omitted"

    # Try extracting JSON arrays loosely
    for arr_field in ["diagram_labels", "data_points", "schemes_referenced", "key_terms_used"]:
        result[arr_field] = []

    return result


def insert_answer(conn: sqlite3.Connection, qid: str, ans: dict):
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
        ans.get("diagram_type") or None,
        ans.get("diagram_description") or None,
        json.dumps(ans.get("diagram_labels") or []),
        json.dumps(ans.get("data_points") or []),
        json.dumps(ans.get("schemes_referenced") or []),
        json.dumps(ans.get("key_terms_used") or []),
        wc(ans.get("intro_text", "")),
        wc(ans.get("body_text", "")),
        wc(ans.get("conclusion_text", "")),
    ))


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")

    inserted = 0
    fallback_used = 0

    with open(CACHE_FILE) as f:
        for line in f:
            rec = json.loads(line)
            qid = rec["custom_id"]
            if qid not in FAILING:
                continue

            text = rec.get("text", "")
            ans = parse_answer(text)

            if ans is None:
                print(f"  JSON parse failed for {qid}, using regex fallback...")
                ans = build_answer_from_fallback(text)
                fallback_used += 1

            insert_answer(conn, qid, ans)
            print(f"  Inserted {qid} (intro={wc(ans.get('intro_text',''))}w, body={wc(ans.get('body_text',''))}w)")
            inserted += 1

    conn.commit()

    total = conn.execute(
        "SELECT COUNT(*) FROM model_answers WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]
    total_q = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]

    print(f"\nDone: inserted={inserted}, fallback_used={fallback_used}")
    print(f"Total model_answers: {total}/{total_q}")
    conn.close()


if __name__ == "__main__":
    main()
