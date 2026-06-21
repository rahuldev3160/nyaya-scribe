"""Seed ethics_questions from a JSONL file into data/upsc_gs.db."""

import argparse
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_gs.db"


def seed(conn, jsonl_path: Path, dry_run: bool) -> None:
    rows = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]

    inserted = 0
    skipped = 0

    for row in rows:
        concept_tags = json.dumps(row.get("concept_tags") or [])
        thinker_tags = json.dumps(row.get("thinker_tags") or [])

        if dry_run:
            inserted += 1
            continue

        cur = conn.execute(
            """
            INSERT OR IGNORE INTO ethics_questions
                (question_id, paper_year, paper_id, section, question_type,
                 question_text, case_preamble, sub_part, marks, content_type,
                 concept_tags, thinker_tags, framework_hint, sequence_order)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                row["question_id"],
                row.get("paper_year"),
                row.get("paper_id"),
                row["section"],
                row["question_type"],
                row["question_text"],
                row.get("case_preamble"),
                row.get("sub_part"),
                row["marks"],
                row.get("content_type", "pyq"),
                concept_tags,
                thinker_tags,
                row.get("framework_hint"),
                row.get("sequence_order"),
            ),
        )
        if cur.rowcount:
            inserted += 1
        else:
            skipped += 1

    if not dry_run:
        conn.commit()

    total = len(rows)
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}Inserted {inserted} / {total} rows ({skipped} already existed)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ethics_questions from JSONL")
    parser.add_argument("--input", required=True, help="Path to JSONL file")
    parser.add_argument("--dry-run", action="store_true", help="Print counts without writing")
    args = parser.parse_args()

    jsonl_path = Path(args.input)
    if not jsonl_path.exists():
        raise SystemExit(f"File not found: {jsonl_path}")

    conn = sqlite3.connect(DB_PATH)
    try:
        seed(conn, jsonl_path, dry_run=args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
