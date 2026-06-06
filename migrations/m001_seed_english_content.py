"""Initial English question types + 4 questions (essays, précis, RC)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import seed_english_content as _src


def run(conn):
    _src.seed_into(conn)
