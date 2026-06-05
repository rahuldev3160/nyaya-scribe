"""
Stage 1: Initialize the IES database with full schema.
Run: python scripts/init_db.py

Creates all tables, seeds exam_configurations for ies_2026.
Topics are seeded separately by seed_topics.py.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""

    -- ─────────────────────────────────────────────
    -- EXAM CONFIGURATION
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- TOPICS HIERARCHY
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- PYQ QUESTIONS
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS pyq_questions (
        question_id     TEXT NOT NULL,
        exam_id         TEXT NOT NULL,
        paper_id        TEXT NOT NULL,
        year            INTEGER NOT NULL,
        question_text   TEXT NOT NULL,
        topic_id        TEXT NOT NULL,
        subtopic_id     TEXT,
        marks           INTEGER DEFAULT 10,
        answer_length   TEXT,
        key_concepts    TEXT,
        question_hash   TEXT UNIQUE,
        PRIMARY KEY (question_id, exam_id)
    );

    -- ─────────────────────────────────────────────
    -- TOPIC BASE SCORES (priority formula components)
    -- ─────────────────────────────────────────────
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
        base_priority_score         REAL DEFAULT 0.0,
        computed_at                 TEXT,
        PRIMARY KEY (topic_id, exam_id)
    );

    -- ─────────────────────────────────────────────
    -- USER MASTERY
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- GAP STATES
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- GAP STATE EVENT LOG (immutable)
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- USER PAPER PREFERENCES
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS user_paper_preferences (
        user_id     TEXT NOT NULL,
        exam_id     TEXT NOT NULL,
        paper_id    TEXT NOT NULL,
        enabled     INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, exam_id, paper_id)
    );

    -- ─────────────────────────────────────────────
    -- TOPIC ATTEMPT SUMMARY (denormalised for dashboard)
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- RETURN QUIZ QUESTIONS
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS return_quiz_questions (
        question_id         TEXT PRIMARY KEY,
        topic_id            TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        question_text       TEXT NOT NULL,
        question_type       TEXT NOT NULL,
        correct_answer      TEXT NOT NULL,
        option_b            TEXT,
        option_c            TEXT,
        option_d            TEXT,
        difficulty          REAL DEFAULT 0.5,
        dimension_id        TEXT,
        generated_at        TEXT DEFAULT (datetime('now')),
        validation_status   TEXT DEFAULT 'pending'
    );

    -- ─────────────────────────────────────────────
    -- RETURN QUIZ ATTEMPTS
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS return_quiz_attempts (
        attempt_id          INTEGER PRIMARY KEY,
        user_id             TEXT NOT NULL,
        topic_id            TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        question_id         TEXT NOT NULL,
        user_answer         TEXT,
        is_correct          INTEGER,
        time_taken_ms       INTEGER,
        confidence_rating   INTEGER,
        session_id          TEXT NOT NULL,
        created_at          TEXT DEFAULT (datetime('now'))
    );

    -- ─────────────────────────────────────────────
    -- DESCRIPTIVE QUIZ ATTEMPTS
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS descriptive_attempts (
        attempt_id          INTEGER PRIMARY KEY,
        user_id             TEXT NOT NULL,
        question_id         TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        quiz_mode           TEXT NOT NULL,
        user_answer_intro   TEXT,
        user_answer_body    TEXT,
        user_answer_conclusion TEXT,
        user_diagram_block  TEXT,
        word_count_intro    INTEGER,
        word_count_body     INTEGER,
        word_count_conclusion INTEGER,
        scores_json         TEXT,
        weighted_score      REAL,
        session_id          TEXT NOT NULL,
        created_at          TEXT DEFAULT (datetime('now'))
    );

    -- ─────────────────────────────────────────────
    -- CONTEXT PACKAGES
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- QUESTION RUBRICS
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS question_rubrics (
        question_id         TEXT NOT NULL,
        exam_id             TEXT NOT NULL,
        rubric_points       TEXT NOT NULL,
        key_terms           TEXT,
        diagram_expected    INTEGER DEFAULT 0,
        diagram_type        TEXT,
        extractor_model     TEXT,
        extracted_at        TEXT,
        PRIMARY KEY (question_id, exam_id)
    );

    -- ─────────────────────────────────────────────
    -- MODEL ANSWERS
    -- ─────────────────────────────────────────────
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

    -- ─────────────────────────────────────────────
    -- DIMENSIONS (lowest level tracking unit)
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS dimensions (
        dimension_id    TEXT NOT NULL,
        topic_id        TEXT NOT NULL,
        exam_id         TEXT NOT NULL,
        dimension_name  TEXT NOT NULL,
        dimension_desc  TEXT,
        PRIMARY KEY (dimension_id, exam_id)
    );

    -- ─────────────────────────────────────────────
    -- USER EVENTS (append-only audit / ML log)
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS user_events (
        event_id    INTEGER PRIMARY KEY,
        user_id     TEXT NOT NULL,
        session_id  TEXT NOT NULL,
        event_type  TEXT NOT NULL,   -- 'topic_opened' | 'return_quiz_submitted' | 'drill_attempt' | 'gap_state_changed'
        entity_type TEXT,            -- 'topic' | 'question' | 'rbi_topic'
        entity_id   TEXT,            -- topic_id, question_id, etc.
        exam_id     TEXT,
        payload     TEXT,            -- JSON blob for extra context
        created_at  TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_ue_user ON user_events(user_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_ue_type ON user_events(event_type, created_at DESC);

    -- ─────────────────────────────────────────────
    -- USERS (Google OAuth)
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS users (
        user_id              TEXT PRIMARY KEY,
        google_sub           TEXT UNIQUE NOT NULL,
        email                TEXT NOT NULL,
        display_name         TEXT,
        avatar_url           TEXT,
        daily_api_calls      INTEGER DEFAULT 0,
        quota_resets_at      TEXT,
        exam_focus           TEXT,                  -- JSON array: ['ies','rbi','upsc']
        exam_date            TEXT,                  -- ISO date of primary exam
        prep_level           TEXT,                  -- 'fresh'|'foundation'|'revision'
        study_mode           TEXT,                  -- 'answers_only'|'full_prep'|'mcq_drill'|'mixed'
        study_path           TEXT,                  -- JSON blob: AI-generated plan
        onboarding_completed INTEGER DEFAULT 0,
        subscription_tier    TEXT DEFAULT 'free',   -- 'free'|'pro'
        created_at           TEXT DEFAULT (datetime('now')),
        last_seen_at         TEXT DEFAULT (datetime('now'))
    );

    -- ─────────────────────────────────────────────
    -- SESSIONS (rolling 7-day tokens)
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS sessions (
        session_token TEXT PRIMARY KEY,             -- secrets.token_hex(32)
        user_id       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        expires_at    TEXT NOT NULL,                -- ISO-8601; 1-day or 30-day rolling
        remember_me   INTEGER DEFAULT 0,            -- 1 = 30-day persistent, 0 = 1-day ephemeral
        created_at    TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

    -- Composite indexes for multi-user query performance
    CREATE INDEX IF NOT EXISTS idx_da_user_exam    ON descriptive_attempts(user_id, exam_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_gse_user_topic  ON gap_state_events(user_id, topic_id, exam_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_rqa_user_topic  ON return_quiz_attempts(user_id, topic_id, exam_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_um_user_exam    ON user_mastery(user_id, exam_id);
    CREATE INDEX IF NOT EXISTS idx_gs_user_exam_st ON gap_states(user_id, exam_id, state);
    CREATE INDEX IF NOT EXISTS idx_tas_user_exam   ON topic_attempt_summary(user_id, exam_id);

    -- ─────────────────────────────────────────────
    -- STUDY PLAN TEMPLATES (user-agnostic cache)
    -- ─────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS study_plan_templates (
        template_key    TEXT PRIMARY KEY,
        exam_focus      TEXT NOT NULL,
        days_bucket     TEXT NOT NULL CHECK (days_bucket IN ('crunch','intensive','standard')),
        prep_level      TEXT NOT NULL,
        study_mode      TEXT NOT NULL,
        plan_json       TEXT NOT NULL,
        generated_at    TEXT DEFAULT (datetime('now')),
        version         INTEGER DEFAULT 1
    );

    """)
    conn.commit()


def seed_exam_configurations(conn: sqlite3.Connection) -> None:
    conn.execute("""
        INSERT OR IGNORE INTO exam_configurations (
            exam_id, exam_name, exam_date,
            w1_pyq_recurrence, w2_pyq_recency, w3_concept_persistence,
            w4_ca_relevance, w5_syllabus_weight, w6_graph_centrality,
            w7_mastery_discount, w8_quiz_only_discount, w9_full_loop_discount,
            paper_ids
        ) VALUES (
            'ies_2026', 'Indian Economic Service 2026', '2026-06-17',
            0.22, 0.20, 0.10,
            0.08, 0.12, 0.08,
            0.20, 0.05, 0.15,
            '["ge_01","ge_02","ge_03","ge_04"]'
        )
    """)
    conn.commit()


def verify(conn: sqlite3.Connection) -> None:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t[0] for t in tables]

    exam = conn.execute(
        "SELECT exam_id, exam_date, w1_pyq_recurrence FROM exam_configurations"
    ).fetchone()

    print("\n── Stage 1 Sense Check ──────────────────────────")
    print(f"Tables created : {len(table_names)}")
    for name in table_names:
        print(f"  ✓ {name}")
    print(f"\nexam_configurations seeded:")
    print(f"  exam_id    : {exam[0]}")
    print(f"  exam_date  : {exam[1]}")
    print(f"  w1         : {exam[2]}")
    print("─────────────────────────────────────────────────\n")


def migrate(conn: sqlite3.Connection) -> None:
    """Apply incremental migrations to an existing DB. Safe to re-run."""
    try:
        conn.execute("ALTER TABLE sessions ADD COLUMN remember_me INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass  # Column already exists


if __name__ == "__main__":
    if DB_PATH.exists():
        print(f"DB already exists at {DB_PATH}. Delete it first to reinitialise.")
        sys.exit(1)

    conn = get_connection()
    print("Creating tables...")
    create_tables(conn)
    print("Seeding exam_configurations...")
    seed_exam_configurations(conn)
    verify(conn)
    conn.close()
    print(f"DB created at: {DB_PATH}")
