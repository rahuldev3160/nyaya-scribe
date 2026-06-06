"""Seed 29 topic weights into rbi_topic_weights from 2024 paper distribution analysis."""
import sys
import importlib.util
from pathlib import Path

DB = "rbi"

_spec = importlib.util.spec_from_file_location(
    "seed_topic_weights",
    Path(__file__).parent.parent / "scripts" / "rbi" / "01_seed_topic_weights.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def run(conn):
    _mod.seed_into(conn)
