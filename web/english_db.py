"""English DB helpers — english.db connection."""
import sqlite3
from pathlib import Path

_ENGLISH_DB_PATH = Path(__file__).parent.parent / "data" / "english.db"


def _open_english_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_ENGLISH_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn
