"""English batch 2 — 15 questions: essays, précis, RC, letters, reports."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import seed_english_batch2 as _src


def run(conn):
    _src.seed_into(conn)
