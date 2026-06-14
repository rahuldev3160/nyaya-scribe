"""Add user_agent column to user_events in nyaya.db for device tracking."""

DB = "nyaya"


def run(conn):
    try:
        conn.execute("ALTER TABLE user_events ADD COLUMN user_agent TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists
