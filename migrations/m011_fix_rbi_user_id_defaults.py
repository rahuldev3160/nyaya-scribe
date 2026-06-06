"""Remove DEFAULT 'rahul' from rbi.db user_id columns.

With real users in production, a missing user_id must fail loudly — not silently
write to a ghost 'rahul' row. Recreates all three user tables without the default.
"""

DB = "rbi"


def run(conn):
    conn.executescript("""
        PRAGMA foreign_keys=OFF;

        CREATE TABLE rbi_attempts_new (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            question_id     TEXT NOT NULL,
            answer_given    TEXT NOT NULL CHECK(answer_given IN ('A','B','C','D')),
            is_correct      INTEGER NOT NULL CHECK(is_correct IN (0,1)),
            time_taken_s    INTEGER,
            session_id      TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (question_id) REFERENCES rbi_questions(id)
        );
        INSERT INTO rbi_attempts_new
            SELECT id, user_id, question_id, answer_given, is_correct,
                   time_taken_s, session_id, created_at
            FROM rbi_attempts;
        DROP TABLE rbi_attempts;
        ALTER TABLE rbi_attempts_new RENAME TO rbi_attempts;
        CREATE INDEX IF NOT EXISTS idx_attempts_user ON rbi_attempts(user_id, question_id);

        CREATE TABLE rbi_sessions_new (
            session_id      TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL,
            mode            TEXT NOT NULL CHECK(mode IN ('smart_serve','filter')),
            filter_params   TEXT DEFAULT '{}',
            total_questions INTEGER DEFAULT 0,
            correct         INTEGER DEFAULT 0,
            started_at      TEXT DEFAULT (datetime('now')),
            ended_at        TEXT
        );
        INSERT INTO rbi_sessions_new SELECT * FROM rbi_sessions;
        DROP TABLE rbi_sessions;
        ALTER TABLE rbi_sessions_new RENAME TO rbi_sessions;
        CREATE INDEX IF NOT EXISTS idx_rbi_sess_user ON rbi_sessions(user_id);

        CREATE TABLE rbi_topic_mastery_new (
            user_id         TEXT NOT NULL,
            topic           TEXT NOT NULL,
            subject         TEXT NOT NULL,
            attempts        INTEGER DEFAULT 0,
            correct         INTEGER DEFAULT 0,
            mastery_score   REAL DEFAULT 0.0,
            coverage_pct    REAL DEFAULT 0.0,
            flag_impact     REAL DEFAULT 0.0,
            gap_state       TEXT DEFAULT 'UNVISITED'
                            CHECK(gap_state IN ('UNVISITED','IN_STUDY','DECAYING','VERIFIED','FLAGGED')),
            last_updated    TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, topic)
        );
        INSERT INTO rbi_topic_mastery_new SELECT * FROM rbi_topic_mastery;
        DROP TABLE rbi_topic_mastery;
        ALTER TABLE rbi_topic_mastery_new RENAME TO rbi_topic_mastery;
        CREATE INDEX IF NOT EXISTS idx_mastery_user ON rbi_topic_mastery(user_id);

        PRAGMA foreign_keys=ON;
    """)
    conn.commit()
