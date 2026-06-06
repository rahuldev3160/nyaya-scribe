"""Create rbi.db 5-table schema (rbi_questions, rbi_attempts, rbi_topic_mastery, rbi_sessions, rbi_topic_weights)."""
import importlib.util
from pathlib import Path

DB = "rbi"

_spec = importlib.util.spec_from_file_location(
    "init_rbi_db",
    Path(__file__).parent.parent / "scripts" / "rbi" / "00_init_rbi_db.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def run(conn):
    _mod.ensure_schema(conn)
