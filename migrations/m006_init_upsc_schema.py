"""Create upsc_eco_opt.db schema (16 IES + 5 UPSC-specific tables) and seed exam config."""
import sys
import importlib.util
from pathlib import Path

DB = "upsc_eco_opt"

_spec = importlib.util.spec_from_file_location(
    "init_upsc_db",
    Path(__file__).parent.parent / "scripts" / "upsc" / "01_init_upsc_db.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def run(conn):
    _mod.create_tables(conn)
    _mod.seed_exam_config(conn)
