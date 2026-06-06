"""Seed 16 UPSC topics + 64 subtopics from config/topics_upsc_eco.json."""
import json
import importlib.util
from pathlib import Path

DB = "upsc"

ROOT = Path(__file__).parent.parent

_spec = importlib.util.spec_from_file_location(
    "seed_topics_upsc",
    ROOT / "scripts" / "upsc" / "02_seed_topics_upsc.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_TOPICS_JSON = ROOT / "config" / "topics_upsc_eco.json"


def run(conn):
    data = json.loads(_TOPICS_JSON.read_text())
    _mod.seed_topics(conn, data)
