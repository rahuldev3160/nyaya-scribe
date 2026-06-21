"""Essay module: questions, CA links, thinker links, B-tree indexes, FTS5 (upsc_gs.db)."""
DB = "upsc_gs"


def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS essay_questions (
            essay_id            TEXT PRIMARY KEY,
            prompt              TEXT NOT NULL,
            section             TEXT CHECK(section IN ('A','B','unknown')),
            theme_tag           TEXT REFERENCES essay_theme_analysis(theme_tag),
            hook_type_id        TEXT REFERENCES essay_hook_types(hook_type_id),
            framework_id        TEXT REFERENCES essay_frameworks(framework_id),
            word_limit          INTEGER DEFAULT 1200,
            marks               INTEGER DEFAULT 125,
            year_appeared       INTEGER,
            content_type        TEXT NOT NULL DEFAULT 'practice'
                CHECK(content_type IN ('practice','pyq','ca_generated')),
            generation_year     INTEGER NOT NULL,
            difficulty          TEXT CHECK(difficulty IN ('easy','medium','hard')),
            is_high_probability INTEGER DEFAULT 0,
            backing_note        TEXT,
            source_proposal_id  TEXT REFERENCES essay_topic_proposals(proposal_id),
            created_at          TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS essay_ca_links (
            link_id         TEXT PRIMARY KEY,
            essay_id        TEXT NOT NULL REFERENCES essay_questions(essay_id) ON DELETE CASCADE,
            event_id        TEXT NOT NULL REFERENCES ca_events(event_id) ON DELETE CASCADE,
            relevance_score REAL DEFAULT 1.0,
            hook_usage      TEXT CHECK(hook_usage IN ('hook','evidence','both','context')),
            UNIQUE(essay_id, event_id)
        );

        CREATE TABLE IF NOT EXISTS essay_thinker_links (
            link_id     TEXT PRIMARY KEY,
            essay_id    TEXT NOT NULL REFERENCES essay_questions(essay_id) ON DELETE CASCADE,
            thinker_id  TEXT NOT NULL REFERENCES gs4_thinkers(thinker_id),
            usage_type  TEXT CHECK(usage_type IN ('hook','body','conclusion','quote')),
            UNIQUE(essay_id, thinker_id)
        );

        CREATE INDEX IF NOT EXISTS idx_essay_year    ON essay_questions(year_appeared);
        CREATE INDEX IF NOT EXISTS idx_essay_section ON essay_questions(section);
        CREATE INDEX IF NOT EXISTS idx_essay_theme   ON essay_questions(theme_tag);
        CREATE INDEX IF NOT EXISTS idx_essay_type    ON essay_questions(content_type, generation_year);
        CREATE INDEX IF NOT EXISTS idx_essay_hot     ON essay_questions(is_high_probability, section);
        CREATE INDEX IF NOT EXISTS idx_essay_diff    ON essay_questions(difficulty);

        CREATE VIRTUAL TABLE IF NOT EXISTS essay_fts USING fts5(
            essay_id UNINDEXED,
            prompt,
            backing_note,
            content='essay_questions',
            content_rowid='rowid'
        );
    """)
    conn.commit()
