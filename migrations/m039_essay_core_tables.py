"""Essay module: core lookup tables — theme analysis, frameworks, hook types, quotes (upsc_gs.db)."""
DB = "upsc_gs"


def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS essay_theme_analysis (
            theme_tag           TEXT PRIMARY KEY,
            theme_label         TEXT NOT NULL,
            frequency_count     INTEGER NOT NULL,
            typical_section     TEXT,
            year_appearances    TEXT,
            example_questions   TEXT,
            fy26_ca_hook        TEXT,
            trend               TEXT CHECK(trend IN ('rising','stable','declining')),
            probability_2026    TEXT CHECK(probability_2026 IN ('high','medium','low')),
            last_updated        TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS essay_frameworks (
            framework_id        TEXT PRIMARY KEY,
            framework_name      TEXT NOT NULL,
            slots_json          TEXT NOT NULL,
            best_for_themes     TEXT,
            typical_sections    TEXT,
            is_active           INTEGER DEFAULT 1,
            created_at          TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS essay_hook_types (
            hook_type_id        TEXT PRIMARY KEY,
            label               TEXT NOT NULL,
            description         TEXT,
            example_template    TEXT,
            best_for_themes     TEXT,
            is_active           INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS essay_quotes (
            quote_id                TEXT PRIMARY KEY,
            thinker                 TEXT NOT NULL,
            quote_text              TEXT NOT NULL,
            context                 TEXT,
            theme_tags              TEXT,
            language                TEXT DEFAULT 'en',
            upsc_suitability_score  REAL DEFAULT 1.0,
            source                  TEXT
        );
    """)
    conn.commit()
