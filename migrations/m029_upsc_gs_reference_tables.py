"""Create GS reference tables: government_schemes, committees, constitution, bilateral_relations."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    CREATE TABLE IF NOT EXISTS government_schemes (
        scheme_id           TEXT PRIMARY KEY,
        scheme_name         TEXT NOT NULL,
        ministry            TEXT NOT NULL,
        launch_year         INTEGER,
        objective           TEXT,
        budget_outlay       TEXT,
        beneficiary_group   TEXT,
        gs_topic_ids        TEXT NOT NULL DEFAULT '[]',
        status              TEXT NOT NULL DEFAULT 'active'
            CHECK(status IN ('active','merged','renamed','discontinued')),
        renamed_to          TEXT,
        merged_into         TEXT,
        upsc_ask_frequency  TEXT DEFAULT 'low'
            CHECK(upsc_ask_frequency IN ('high','medium','low')),
        last_verified_at    TEXT,
        created_at          TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS committees_index (
        committee_id            TEXT PRIMARY KEY,
        committee_name          TEXT NOT NULL,
        year                    INTEGER,
        mandate                 TEXT,
        key_recommendations     TEXT,
        gs2_topic_ids           TEXT,
        pyq_question_ids        TEXT,
        status                  TEXT CHECK(status IN ('implemented','partial','pending','rejected'))
    );

    CREATE TABLE IF NOT EXISTS constitution_index (
        article_id          TEXT PRIMARY KEY,
        article_number      TEXT NOT NULL,
        part_number         TEXT,
        schedule_number     TEXT,
        short_title         TEXT NOT NULL,
        amendment_history   TEXT,
        current_status      TEXT CHECK(current_status IN ('in_force','modified','repealed')),
        gs2_topic_ids       TEXT,
        pyq_question_ids    TEXT,
        landmark_cases      TEXT
    );

    CREATE TABLE IF NOT EXISTS bilateral_relations (
        relation_id             TEXT PRIMARY KEY,
        country_name            TEXT NOT NULL,
        region                  TEXT,
        relationship_tier       TEXT CHECK(relationship_tier IN ('strategic','important','developing','contentious')),
        key_agreements          TEXT,
        key_friction_points     TEXT,
        recent_developments     TEXT,
        ca_sensitivity          TEXT DEFAULT 'high',
        pyq_question_ids        TEXT,
        data_as_of              TEXT
    );

    -- Cross-paper: GS3 Economy ↔ Economics Optional bridges (Python-merge, no cross-DB JOIN)
    CREATE TABLE IF NOT EXISTS eco_opt_bridges (
        bridge_id               TEXT PRIMARY KEY,
        gs_topic_id             TEXT NOT NULL,
        gs_paper_id             TEXT NOT NULL DEFAULT 'gs3',
        eco_opt_topic_id        TEXT NOT NULL,
        eco_opt_paper_id        TEXT NOT NULL,
        bridge_type             TEXT CHECK(bridge_type IN ('full_overlap','theory_only','application_only','partial')),
        bridge_note             TEXT,
        opt_mastery_threshold   REAL DEFAULT 0.7
    );

    -- Synthesis questions spanning multiple GS papers
    CREATE TABLE IF NOT EXISTS synthesis_questions (
        synth_id            TEXT PRIMARY KEY,
        question_text       TEXT NOT NULL,
        required_papers     TEXT NOT NULL,
        required_topic_ids  TEXT NOT NULL,
        synthesis_type      TEXT CHECK(synthesis_type IN ('thematic','causal','comparative','evaluative')),
        marks_equivalent    INTEGER,
        word_limit          INTEGER,
        difficulty          TEXT DEFAULT 'hard',
        source_pyq_year     INTEGER,
        ca_event_ids        TEXT,
        is_ca_triggered     INTEGER DEFAULT 0,
        priority_score      REAL DEFAULT 0.0
    );

    """)
    conn.commit()
