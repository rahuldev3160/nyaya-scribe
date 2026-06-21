"""Essay module: topic proposals queue for annual inference cycle (upsc_gs.db)."""
DB = "upsc_gs"


def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS essay_topic_proposals (
            proposal_id         TEXT PRIMARY KEY,
            proposed_prompt     TEXT NOT NULL,
            theme_tag           TEXT,
            section_guess       TEXT CHECK(section_guess IN ('A','B','unknown')),
            framework_suggestion TEXT REFERENCES essay_frameworks(framework_id),
            hook_suggestion     TEXT REFERENCES essay_hook_types(hook_type_id),
            probability_score   REAL,
            ca_event_ids        TEXT,
            generation_year     INTEGER NOT NULL,
            inferred_by         TEXT DEFAULT 'claude-haiku-4-5-20251001',
            status              TEXT DEFAULT 'pending'
                CHECK(status IN ('pending','approved','rejected','needs_edit')),
            reviewer_notes      TEXT,
            reviewed_at         TEXT,
            created_at          TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
