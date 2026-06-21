"""Essay module: generation batches, structured model answers, FTS5 on answers (upsc_gs.db)."""
DB = "upsc_gs"


def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS essay_generation_batches (
            batch_id        TEXT PRIMARY KEY,
            batch_type      TEXT CHECK(batch_type IN ('practice','pyq','ca_refresh')),
            generation_year INTEGER NOT NULL,
            essay_count     INTEGER,
            model_used      TEXT,
            estimated_cost  REAL,
            status          TEXT DEFAULT 'pending'
                CHECK(status IN ('pending','running','complete','failed')),
            started_at      TEXT,
            completed_at    TEXT,
            notes           TEXT
        );

        CREATE TABLE IF NOT EXISTS essay_model_answers (
            answer_id           TEXT PRIMARY KEY,
            essay_id            TEXT NOT NULL REFERENCES essay_questions(essay_id),
            intro_hook          TEXT NOT NULL,
            intro_hook_type     TEXT NOT NULL,
            intro_context       TEXT NOT NULL,
            intro_thesis        TEXT NOT NULL,
            intro_signpost      TEXT NOT NULL,
            body_dimensions_json TEXT NOT NULL,
            body_challenges     TEXT NOT NULL,
            body_solutions      TEXT NOT NULL,
            body_synthesis_para TEXT,
            concl_synthesis     TEXT NOT NULL,
            concl_way_forward   TEXT NOT NULL,
            concl_philosophical TEXT NOT NULL,
            concl_closing_line  TEXT NOT NULL,
            total_word_count    INTEGER,
            framework_id        TEXT REFERENCES essay_frameworks(framework_id),
            generation_model    TEXT DEFAULT 'claude-sonnet-4-6',
            batch_id            TEXT REFERENCES essay_generation_batches(batch_id),
            human_reviewed      INTEGER DEFAULT 0,
            reviewer_notes      TEXT,
            reviewed_at         TEXT,
            created_at          TEXT DEFAULT (datetime('now'))
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS essay_answer_fts USING fts5(
            answer_id UNINDEXED,
            intro_hook,
            intro_thesis,
            body_challenges,
            body_solutions,
            concl_closing_line,
            content='essay_model_answers',
            content_rowid='rowid'
        );
    """)
    conn.commit()
