"""Initialise nyaya.db — canonical identity + event store for all NYAYA products.

Creates users, sessions, user_events, product_enrollments tables and migrates
existing OAuth users, sessions, and events from ies.db.
"""

DB = "nyaya"


def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            google_sub TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            display_name TEXT,
            avatar_url TEXT,
            daily_api_calls INTEGER DEFAULT 0,
            quota_resets_at TEXT,
            exam_focus TEXT,
            exam_date TEXT,
            prep_level TEXT,
            study_mode TEXT,
            study_path TEXT,
            onboarding_completed INTEGER DEFAULT 0,
            subscription_tier TEXT DEFAULT 'free',
            created_at TEXT DEFAULT (datetime('now')),
            last_seen_at TEXT DEFAULT (datetime('now'))
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

        CREATE TABLE IF NOT EXISTS sessions (
            session_token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(user_id),
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            remember_me INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

        CREATE TABLE IF NOT EXISTS user_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            session_id TEXT,
            event_type TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            exam_id TEXT,
            payload TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ue_user ON user_events(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_ue_type ON user_events(event_type, created_at DESC);

        CREATE TABLE IF NOT EXISTS product_enrollments (
            user_id TEXT NOT NULL REFERENCES users(user_id),
            product TEXT NOT NULL CHECK(product IN ('scribe_ies','scribe_rbi','scribe_upsc','recall','atlas')),
            enrolled_at TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'active' CHECK(status IN ('active','paused','cancelled')),
            PRIMARY KEY (user_id, product)
        );
    """)

    from pathlib import Path
    import sqlite3 as _sqlite3
    ies_path = Path(__file__).parent.parent / "data" / "ies.db"
    if not ies_path.exists():
        conn.commit()
        return

    ies = _sqlite3.connect(str(ies_path))
    ies.row_factory = _sqlite3.Row

    users = ies.execute(
        "SELECT user_id, google_sub, email, display_name, avatar_url, "
        "daily_api_calls, quota_resets_at, exam_focus, exam_date, prep_level, "
        "study_mode, study_path, onboarding_completed, subscription_tier, "
        "created_at, last_seen_at FROM users WHERE google_sub IS NOT NULL"
    ).fetchall()
    for u in users:
        conn.execute("""
            INSERT OR IGNORE INTO users
            (user_id, google_sub, email, display_name, avatar_url,
             daily_api_calls, quota_resets_at, exam_focus, exam_date, prep_level,
             study_mode, study_path, onboarding_completed, subscription_tier,
             created_at, last_seen_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, tuple(u))

    sessions = ies.execute(
        "SELECT session_token, user_id, created_at, expires_at, remember_me FROM sessions"
    ).fetchall()
    for s in sessions:
        conn.execute("""
            INSERT OR IGNORE INTO sessions (session_token, user_id, created_at, expires_at, remember_me)
            SELECT ?,?,?,?,? WHERE EXISTS (SELECT 1 FROM users WHERE user_id=?)
        """, (s["session_token"], s["user_id"], s["created_at"], s["expires_at"],
              s["remember_me"], s["user_id"]))

    events = ies.execute(
        "SELECT user_id, session_id, event_type, entity_type, entity_id, exam_id, payload, created_at FROM user_events"
    ).fetchall()
    for e in events:
        conn.execute("""
            INSERT INTO user_events
            (user_id, session_id, event_type, entity_type, entity_id, exam_id, payload, created_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (e["user_id"], e["session_id"], e["event_type"], e["entity_type"],
              e["entity_id"], e["exam_id"], e["payload"], e["created_at"]))

    ies.close()
    conn.commit()
