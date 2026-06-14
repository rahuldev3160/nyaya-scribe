"""UPSC DB helpers — upsc.db connection and shared query helpers."""
import sqlite3
from pathlib import Path

_UPSC_DB_PATH = Path(__file__).parent.parent / "data" / "upsc.db"


def _open_upsc_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_UPSC_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn
