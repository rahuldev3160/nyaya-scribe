"""upsc_gs.db connection helper — GS Mains (all 4 papers)."""
import sqlite3
from pathlib import Path

_UPSC_GS_DB_PATH = Path(__file__).parent.parent / "data" / "upsc_gs.db"


def _open_upsc_gs_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_UPSC_GS_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
