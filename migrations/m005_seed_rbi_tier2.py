"""Seed 36 Tier 2 MCQs into rbi_questions."""
import sys
import importlib.util
from pathlib import Path

DB = "rbi"

_spec = importlib.util.spec_from_file_location(
    "migrate_tier2",
    Path(__file__).parent.parent / "scripts" / "rbi" / "03_migrate_tier2.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def run(conn):
    _mod.seed_into(conn)
