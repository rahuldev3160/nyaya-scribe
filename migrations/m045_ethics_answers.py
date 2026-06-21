"""Ethics model answers table + FTS5."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    CREATE TABLE IF NOT EXISTS ethics_model_answers (
        answer_id           TEXT PRIMARY KEY,
        question_id         TEXT NOT NULL REFERENCES ethics_questions(question_id),
        theory_intro        TEXT,
        theory_dimensions   TEXT,
        theory_evidence     TEXT,
        theory_apply        TEXT,
        theory_upshot       TEXT,
        stake_stakeholders  TEXT,
        stake_tension       TEXT,
        stake_analysis      TEXT,
        stake_decision      TEXT,
        stake_execution     TEXT,
        full_answer_text    TEXT NOT NULL,
        word_count          INTEGER,
        thinkers_cited      TEXT,
        frameworks_used     TEXT,
        model_used          TEXT DEFAULT 'claude-sonnet-4-6',
        human_reviewed      INTEGER DEFAULT 0,
        created_at          TEXT DEFAULT (datetime('now'))
    );

    CREATE VIRTUAL TABLE IF NOT EXISTS ethics_answer_fts USING fts5(
        answer_id UNINDEXED,
        full_answer_text,
        thinkers_cited,
        content='ethics_model_answers',
        content_rowid='rowid'
    );

    """)

    conn.commit()
