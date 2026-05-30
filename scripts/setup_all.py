"""
Full setup runner — runs all one-time setup stages in sequence.
Run: python3 scripts/setup_all.py

Stages:
  1. init_db.py        — create DB schema
  2. seed_topics.py    — seed topic taxonomy
  3. ingest_pyq.py     — parse PYQ PDFs (1219 questions)
  4. generate_rubrics.py — Haiku batch: extract rubrics
  5. compute_base_scores.py — compute priority scores
  6. generate_answers.py — Sonnet batch: generate model answers

Use --from-stage N to resume from a specific stage.
"""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
DB_PATH = SCRIPTS_DIR.parent / "data" / "ies.db"

STAGES = [
    (1, "init_db.py", "Initialize DB schema"),
    (2, "seed_topics.py", "Seed topic taxonomy"),
    (3, "ingest_pyq.py", "Ingest PYQ questions"),
    (4, "generate_rubrics.py", "Generate rubrics (Haiku batch)"),
    (5, "compute_base_scores.py", "Compute priority scores"),
    (6, "generate_answers.py", "Generate model answers (Sonnet batch)"),
]


def run_stage(script_name: str, label: str) -> bool:
    print(f"\n{'─'*60}")
    print(f"  Running: {label}")
    print(f"  Script : {script_name}")
    print(f"{'─'*60}")

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script_name)],
        cwd=str(SCRIPTS_DIR.parent)
    )
    if result.returncode != 0:
        print(f"\n  FAILED: {script_name} (exit code {result.returncode})")
        return False
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-stage", type=int, default=1, help="Start from this stage number (1-6)")
    parser.add_argument("--only-stage", type=int, help="Run only this stage number")
    args = parser.parse_args()

    if args.only_stage:
        stages_to_run = [s for s in STAGES if s[0] == args.only_stage]
    else:
        stages_to_run = [s for s in STAGES if s[0] >= args.from_stage]

    if not stages_to_run:
        print("No stages to run")
        raise SystemExit(1)

    print(f"\nIES 2026 Setup — running stages {stages_to_run[0][0]}-{stages_to_run[-1][0]}")

    for stage_num, script, label in stages_to_run:
        # Stage 1 (init_db) only runs if DB doesn't exist
        if stage_num == 1 and DB_PATH.exists():
            print(f"\n  Stage 1: DB already exists at {DB_PATH} — skipping")
            continue

        ok = run_stage(script, f"Stage {stage_num}: {label}")
        if not ok:
            print(f"\nSetup halted at stage {stage_num}. Fix the issue and resume with:")
            print(f"  python3 scripts/setup_all.py --from-stage {stage_num}")
            raise SystemExit(1)

    print("\n" + "═" * 60)
    print("  Setup complete!")
    print("  Start studying:")
    print("    python3 scripts/session_planner.py")
    print("    python3 scripts/view_answers.py")
    print("    python3 scripts/quiz_descriptive.py --topic <topic_id>")
    print("═" * 60)
