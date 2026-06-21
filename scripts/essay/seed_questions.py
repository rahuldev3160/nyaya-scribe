"""
Read data/essay_questions_seed.jsonl and insert rows into essay_questions (upsc_gs.db).

Usage:
    python3 scripts/essay/seed_questions.py
    python3 scripts/essay/seed_questions.py --dry-run
    python3 scripts/essay/seed_questions.py --input data/custom_seed.jsonl
"""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "data" / "upsc_gs.db"
DEFAULT_SEED = ROOT / "data" / "essay_questions_seed.jsonl"

COLUMNS = (
    "essay_id", "prompt", "section", "theme_tag", "hook_type_id", "framework_id",
    "word_limit", "marks", "year_appeared", "content_type", "generation_year",
    "difficulty", "is_high_probability", "backing_note", "source_proposal_id",
)


def load_rows(path: Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {line_no}: invalid JSON — {exc}") from exc
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input", default=str(DEFAULT_SEED))
    args = parser.parse_args()

    seed_path = Path(args.input)
    if not seed_path.exists():
        print(f"ERROR: seed file not found: {seed_path}")
        raise SystemExit(1)

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} does not exist. Run migrations first.")
        raise SystemExit(1)

    rows = load_rows(seed_path)
    total = len(rows)

    if args.dry_run:
        print(f"[dry-run] {total} rows in seed file. First 3:")
        for r in rows[:3]:
            print(f"  {r.get('essay_id')} | {r.get('content_type')} | {r.get('prompt', '')[:60]}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inserted = 0
    try:
        for row in rows:
            params = tuple(row.get(col) for col in COLUMNS)
            placeholders = ",".join("?" * len(COLUMNS))
            col_list = ",".join(COLUMNS)
            cur = conn.execute(
                f"INSERT OR IGNORE INTO essay_questions ({col_list}) VALUES ({placeholders})",
                params,
            )
            inserted += cur.rowcount
        conn.commit()
    finally:
        conn.close()

    already = total - inserted
    print(f"Inserted {inserted} / {total} rows ({already} already existed)")


if __name__ == "__main__":
    main()
