"""Create upsc_gs.db core schema — all standard tables + seed exam_configurations for gs1-gs4."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    CREATE TABLE IF NOT EXISTS exam_configurations (
        exam_id                         TEXT PRIMARY KEY,
        exam_name                       TEXT NOT NULL,
        exam_date                       TEXT,
        pyq_decay_factor                REAL DEFAULT 0.9,
        flag_threshold                  REAL DEFAULT 0.55,
        verified_quiz_threshold         REAL DEFAULT 0.80,
        partial_quiz_threshold          REAL DEFAULT 0.50,
        proximity_verified_threshold    REAL DEFAULT 0.70,
        decay_halflife_days             INTEGER DEFAULT 14,
        exam_proximity_compress_days    INTEGER DEFAULT 7,
        ca_weight_cap                   REAL DEFAULT 0.40,
        w1_pyq_recurrence               REAL DEFAULT 0.22,
        w2_pyq_recency                  REAL DEFAULT 0.20,
        w3_concept_persistence          REAL DEFAULT 0.10,
        w4_ca_relevance                 REAL DEFAULT 0.08,
        w5_syllabus_weight              REAL DEFAULT 0.12,
        w6_graph_centrality             REAL DEFAULT 0.08,
        w7_mastery_discount             REAL DEFAULT 0.20,
        w8_quiz_only_discount           REAL DEFAULT 0.05,
        w9_full_loop_discount           REAL DEFAULT 0.15,
        paper_ids                       TEXT,
        created_at                      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS topics (
        topic_id        TEXT NOT NULL,
        exam_id         TEXT NOT NULL,
        paper_id        TEXT NOT NULL,
        topic_name      TEXT NOT NULL,
        subtopic_of     TEXT,
        topic_level     TEXT DEFAULT 'topic',
        syllabus_weight REAL DEFAULT 1.0,
        PRIMARY KEY (topic_id, exam_id),
        CHECK (topic_level IN ('topic', 'subtopic'))
    );

    CREATE TABLE IF NOT EXISTS pyq_questions (
        question_id     TEXT NOT NULL,
        exam_id         TEXT NOT NULL,
        paper_id        TEXT NOT NULL,
        year            INTEGER NOT NULL,
        question_text   TEXT NOT NULL,
        topic_id        TEXT NOT NULL,
        subtopic_id     TEXT,
        marks           INTEGER,
        answer_length   TEXT,
        key_concepts    TEXT,
        question_hash   TEXT UNIQUE,
        PRIMARY KEY (question_id, exam_id)
    );

    CREATE TABLE IF NOT EXISTS topic_base_scores (
        topic_id                    TEXT NOT NULL,
        exam_id                     TEXT NOT NULL,
        paper_id                    TEXT NOT NULL,
        pyq_count                   INTEGER DEFAULT 0,
        distinct_years              INTEGER DEFAULT 0,
        pyq_recurrence_score        REAL DEFAULT 0.0,
        pyq_recency_score           REAL DEFAULT 0.0,
        concept_persistence_score   REAL DEFAULT 0.0,
        ca_relevance_score          REAL DEFAULT 0.0,
        graph_centrality_score      REAL DEFAULT 0.0,
        syllabus_floor_score        REAL DEFAULT 0.0,
        base_priority_score         REAL DEFAULT 0.0,
        computed_at                 TEXT,
        PRIMARY KEY (topic_id, exam_id)
    );

    CREATE TABLE IF NOT EXISTS user_mastery (
        user_id                 TEXT NOT NULL,
        topic_id                TEXT NOT NULL,
        exam_id                 TEXT NOT NULL,
        mastery_level           REAL DEFAULT 0.0,
        claimed_level           REAL DEFAULT 0.5,
        sar_score               REAL DEFAULT 0.5,
        last_quiz_score         REAL,
        quiz_attempt_count      INTEGER DEFAULT 0,
        last_tested_at          TEXT,
        attestation_source      TEXT DEFAULT 'none',
        is_diagnostic_seeded    INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, topic_id, exam_id)
    );

    CREATE TABLE IF NOT EXISTS gap_states (
        user_id                 TEXT NOT NULL,
        topic_id                TEXT NOT NULL,
        exam_id                 TEXT NOT NULL,
        paper_id                TEXT NOT NULL,
        state                   TEXT NOT NULL DEFAULT 'UNVISITED',
        urgency_multiplier      REAL DEFAULT 1.0,
        flagged_at              TEXT,
        study_started_at        TEXT,
        last_verified_at        TEXT,
        next_review_at          TEXT,
        last_return_quiz_score  REAL,
        context_package_hash    TEXT,
        attempt_count           INTEGER DEFAULT 0,
        stuck_flag              INTEGER DEFAULT 0,
        last_active_at          TEXT,
        PRIMARY KEY (user_id, topic_id, exam_id),
        CHECK (state IN ('UNVISITED','FLAGGED','IN_STUDY','PARTIAL','VERIFIED','DECAYING'))
    );

    CREATE TABLE IF NOT EXISTS gap_state_events (
        event_id                INTEGER PRIMARY KEY,
        user_id                 TEXT NOT NULL,
        topic_id                TEXT NOT NULL,
        exam_id                 TEXT NOT NULL,
        from_state              TEXT,
        to_state                TEXT NOT NULL,
        trigger                 TEXT NOT NULL,
        quiz_score              REAL,
        priority_score_at_event REAL,
        metadata                TEXT,
        created_at              TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS user_paper_preferences (
        user_id     TEXT NOT NULL,
        exam_id     TEXT NOT NULL,
        paper_id    TEXT NOT NULL,
        enabled     INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, exam_id, paper_id)
    );

    CREATE TABLE IF NOT EXISTS topic_attempt_summary (
        user_id             TEXT NOT NULL,
        topic_id            TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        total_attempts      INTEGER DEFAULT 0,
        correct_attempts    INTEGER DEFAULT 0,
        coverage_pct        REAL DEFAULT 0.0,
        flag_impact_score   REAL DEFAULT 0.0,
        last_updated        TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (user_id, topic_id, exam_id)
    );

    CREATE TABLE IF NOT EXISTS return_quiz_questions (
        question_id         TEXT PRIMARY KEY,
        topic_id            TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        question_text       TEXT NOT NULL,
        question_type       TEXT NOT NULL,
        quiz_tier           INTEGER DEFAULT 1
            CHECK(quiz_tier IN (1, 2, 3)),
        correct_answer      TEXT NOT NULL,
        option_b            TEXT,
        option_c            TEXT,
        option_d            TEXT,
        difficulty          REAL DEFAULT 0.5,
        dimension_id        TEXT,
        generated_at        TEXT DEFAULT (datetime('now')),
        validation_status   TEXT DEFAULT 'pending'
    );

    CREATE TABLE IF NOT EXISTS return_quiz_attempts (
        attempt_id          INTEGER PRIMARY KEY,
        user_id             TEXT NOT NULL,
        topic_id            TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        question_id         TEXT NOT NULL,
        quiz_tier           INTEGER DEFAULT 1,
        user_answer         TEXT,
        is_correct          INTEGER,
        ai_score            REAL,
        time_taken_ms       INTEGER,
        confidence_rating   INTEGER,
        session_id          TEXT NOT NULL,
        created_at          TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS descriptive_attempts (
        attempt_id              INTEGER PRIMARY KEY,
        user_id                 TEXT NOT NULL,
        question_id             TEXT NOT NULL,
        exam_id                 TEXT NOT NULL,
        quiz_mode               TEXT NOT NULL,
        user_answer_intro       TEXT,
        user_answer_body        TEXT,
        user_answer_conclusion  TEXT,
        user_diagram_block      TEXT,
        word_count_intro        INTEGER,
        word_count_body         INTEGER,
        word_count_conclusion   INTEGER,
        scores_json             TEXT,
        weighted_score          REAL,
        self_rating             INTEGER,
        session_id              TEXT NOT NULL,
        created_at              TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS context_packages (
        package_id          TEXT PRIMARY KEY,
        user_id             TEXT NOT NULL,
        topic_id            TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        package_hash        TEXT NOT NULL,
        brief_text          TEXT NOT NULL,
        pyq_ids_included    TEXT,
        ca_events_included  TEXT,
        traps_included      TEXT,
        generated_at        TEXT DEFAULT (datetime('now')),
        is_stale            INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS question_rubrics (
        question_id             TEXT NOT NULL,
        exam_id                 TEXT NOT NULL,
        rubric_points           TEXT NOT NULL,
        key_terms               TEXT,
        diagram_expected        INTEGER DEFAULT 0,
        diagram_type            TEXT,
        extractor_model         TEXT,
        extracted_at            TEXT,
        PRIMARY KEY (question_id, exam_id)
    );

    CREATE TABLE IF NOT EXISTS model_answers (
        answer_id           TEXT PRIMARY KEY,
        question_id         TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        intro_text          TEXT NOT NULL,
        body_text           TEXT NOT NULL,
        conclusion_text     TEXT NOT NULL,
        diagram_mode        TEXT,
        diagram_type        TEXT,
        diagram_description TEXT,
        diagram_labels      TEXT,
        data_points         TEXT,
        schemes_referenced  TEXT,
        key_terms_used      TEXT,
        wc_intro            INTEGER,
        wc_body             INTEGER,
        wc_conclusion       INTEGER,
        critique_json       TEXT,
        needs_review        INTEGER DEFAULT 0,
        overall_quality     TEXT,
        generator_model     TEXT,
        generated_at        TEXT DEFAULT (datetime('now')),
        version             INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS dimensions (
        dimension_id    TEXT NOT NULL,
        topic_id        TEXT NOT NULL,
        exam_id         TEXT NOT NULL,
        dimension_name  TEXT NOT NULL,
        dimension_desc  TEXT,
        PRIMARY KEY (dimension_id, exam_id)
    );

    CREATE TABLE IF NOT EXISTS section_weight_overrides (
        paper_id        TEXT NOT NULL,
        section_name    TEXT NOT NULL,
        floor_priority  REAL DEFAULT 0.0,
        w5_multiplier   REAL DEFAULT 1.0,
        PRIMARY KEY (paper_id, section_name)
    );

    """)

    # Seed exam_configurations for all 4 GS papers
    configs = [
        # gs1: History/Geo/Culture/Society — w2 (recency) high, w4 (CA) moderate
        ("gs1", "GS Paper I — History, Geography, Art & Culture, Society", "2026-09-15",
         0.18, 0.22, 0.12, 0.12, 0.15, 0.06, 0.20, 0.05, 0.15, 0.50,
         '["gs1"]'),
        # gs2 const section: persistence >> recency for static provisions
        ("gs2", "GS Paper II — Polity, Governance, Constitution & IR", "2026-09-15",
         0.20, 0.15, 0.16, 0.12, 0.14, 0.08, 0.20, 0.05, 0.15, 0.40,
         '["gs2"]'),
        # gs3: economy/env — CA very heavy (0.20), recurrence high (0.30)
        ("gs3", "GS Paper III — Economy, Environment, Technology & Security", "2026-09-15",
         0.25, 0.22, 0.12, 0.18, 0.10, 0.05, 0.20, 0.05, 0.15, 0.50,
         '["gs3"]'),
        # gs4: ethics — concept_frequency as w1, persistence high
        ("gs4", "GS Paper IV — Ethics, Integrity & Aptitude", "2026-09-15",
         0.15, 0.20, 0.20, 0.10, 0.15, 0.10, 0.20, 0.05, 0.15, 0.35,
         '["gs4"]'),
    ]

    for (exam_id, exam_name, exam_date,
         w1, w2, w3, w4, w5, w6, w7, w8, w9, ca_weight_cap, paper_ids) in configs:
        conn.execute("""
            INSERT OR IGNORE INTO exam_configurations (
                exam_id, exam_name, exam_date,
                w1_pyq_recurrence, w2_pyq_recency, w3_concept_persistence,
                w4_ca_relevance, w5_syllabus_weight, w6_graph_centrality,
                w7_mastery_discount, w8_quiz_only_discount, w9_full_loop_discount,
                ca_weight_cap, paper_ids
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (exam_id, exam_name, exam_date,
              w1, w2, w3, w4, w5, w6, w7, w8, w9, ca_weight_cap, paper_ids))

    # Disaster Management section_weight_override — thin PYQ signal needs floor
    conn.execute("""
        INSERT OR IGNORE INTO section_weight_overrides (paper_id, section_name, floor_priority, w5_multiplier)
        VALUES ('gs3', 'Disaster Management', 0.40, 3.33)
    """)

    conn.commit()
