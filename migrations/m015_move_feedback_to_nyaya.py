"""Move user_feedback from ies.db to nyaya.db — product feedback belongs with identity data."""
from pathlib import Path

DB = "nyaya"


def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            feedback_id TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            category    TEXT NOT NULL DEFAULT 'bug'
                CHECK(category IN ('bug','feature','issue','other')),
            title       TEXT NOT NULL,
            description TEXT DEFAULT '',
            status      TEXT DEFAULT 'open'
                CHECK(status IN ('open','acknowledged','resolved')),
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_feedback_created ON user_feedback(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_feedback_user    ON user_feedback(user_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_status  ON user_feedback(status);
    """)

    ies_path = Path(__file__).parent.parent / "data" / "ies.db"
    if ies_path.exists():
        try:
            conn.execute(f"ATTACH DATABASE '{ies_path}' AS ies_db")
            conn.execute("""
                INSERT OR IGNORE INTO user_feedback
                    (feedback_id, user_id, category, title, description, status, created_at)
                SELECT feedback_id, user_id, category, title, description, status, created_at
                FROM ies_db.user_feedback
            """)
            conn.execute("DETACH ies_db")
        except Exception:
            try:
                conn.execute("DETACH ies_db")
            except Exception:
                pass

    conn.commit()
