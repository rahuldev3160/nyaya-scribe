"""
Widen gs4_keywords.keyword_category CHECK constraint.
Original 7 values were too narrow; replace with the full taxonomy used by setup_upsc_gs.py.
SQLite can't ALTER CHECK constraints — must recreate the table.
"""
DB = "upsc_gs"


def run(conn):
    conn.executescript("""
        PRAGMA foreign_keys = OFF;

        CREATE TABLE IF NOT EXISTS gs4_keywords_new (
            keyword_id       TEXT PRIMARY KEY,
            keyword_text     TEXT NOT NULL UNIQUE,
            canonical_form   TEXT NOT NULL,
            synonyms         TEXT,
            keyword_category TEXT CHECK(keyword_category IN (
                'core_value','ethical_theory','governance_ethics','emotional_intelligence',
                'social_justice','case_study','constitutional','civil_service','philosophical',
                'applied_ethics','thinker_concept','competency','nolan_principles',
                'gandhi','ambedkar','institutional',
                'value','virtue','principle','governance','psychological','governance_term'
            )),
            concept_ids  TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        );

        INSERT INTO gs4_keywords_new
            SELECT keyword_id, keyword_text, canonical_form, synonyms,
                   keyword_category, concept_ids, created_at
            FROM gs4_keywords;

        DROP TABLE gs4_keywords;
        ALTER TABLE gs4_keywords_new RENAME TO gs4_keywords;

        PRAGMA foreign_keys = ON;
    """)
