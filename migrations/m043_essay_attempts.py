"""Essay module: user attempt storage (upsc_gs.db)."""
DB = "upsc_gs"


def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS essay_attempts (
            attempt_id      TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            essay_id        TEXT NOT NULL REFERENCES essay_questions(essay_id),
            intro_text      TEXT,
            body_text       TEXT,
            conclusion_text TEXT,
            full_text       TEXT,
            word_count      INTEGER,
            ai_score_json   TEXT,
            ai_score_overall REAL,
            attempt_type    TEXT DEFAULT 'timed'
                CHECK(attempt_type IN ('timed','open','post_exam')),
            submitted_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_essay_att_user ON essay_attempts(user_id, essay_id);
    """)
    conn.commit()
