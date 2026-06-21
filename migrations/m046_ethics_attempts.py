"""Ethics user attempts table."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    CREATE TABLE IF NOT EXISTS ethics_attempts (
        attempt_id      TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL,
        question_id     TEXT NOT NULL REFERENCES ethics_questions(question_id),
        attempt_text    TEXT,
        word_count      INTEGER,
        self_rating     TEXT CHECK(self_rating IN ('strong','partial','weak')),
        self_notes      TEXT,
        model_revealed  INTEGER DEFAULT 0,
        revealed_at     TEXT,
        submitted_at    TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_ethics_att_user ON ethics_attempts(user_id, question_id);

    """)

    conn.commit()
