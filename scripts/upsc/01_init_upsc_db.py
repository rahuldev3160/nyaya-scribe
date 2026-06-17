"""
Stage 1 (UPSC): Initialise upsc_eco_opt.db with full schema.
Run: python3 scripts/upsc/01_init_upsc_db.py

Creates all 16 IES tables + 5 UPSC-specific tables.
Seeds exam_configurations for upsc_eco_opt.
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_eco_opt.db"
EXAM_ID = "upsc_eco_opt"


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
        marks           INTEGER,
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
        session_id              TEXT NOT NULL,
        created_at              TEXT DEFAULT (datetime('now'))
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

    -- ═════════════════════════════════════════════
    -- UPSC-SPECIFIC TABLES (new — not in ies.db)
    -- ═════════════════════════════════════════════

    -- Multi-user support (future scaling)
    CREATE TABLE IF NOT EXISTS users (
        user_id         TEXT PRIMARY KEY,
        display_name    TEXT,
        exam_target     TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        last_active_at  TEXT
    );

    -- Index of every source PDF/document
    CREATE TABLE IF NOT EXISTS source_documents (
        doc_id              TEXT PRIMARY KEY,
        exam_id             TEXT NOT NULL,
        paper_id            TEXT,
        topic_id            TEXT,
        filename            TEXT NOT NULL,
        doc_type            TEXT NOT NULL,
        file_path           TEXT NOT NULL,
        total_pages         INTEGER DEFAULT 0,
        extracted_pages     INTEGER DEFAULT 0,
        extractable_chars   INTEGER DEFAULT 0,
        status              TEXT DEFAULT 'pending',
        notes               TEXT,
        indexed_at          TEXT DEFAULT (datetime('now'))
    );

    -- Chunked text from notes PDFs (for future RAG)
    CREATE TABLE IF NOT EXISTS document_chunks (
        chunk_id        TEXT PRIMARY KEY,
        doc_id          TEXT NOT NULL REFERENCES source_documents(doc_id),
        exam_id         TEXT NOT NULL,
        paper_id        TEXT,
        topic_id        TEXT,
        chunk_index     INTEGER NOT NULL,
        chunk_text      TEXT NOT NULL,
        page_start      INTEGER,
        page_end        INTEGER,
        word_count      INTEGER DEFAULT 0,
        embedding_slot  TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    -- Pre-solved coaching Q+A pairs (reference answers)
    CREATE TABLE IF NOT EXISTS reference_answers (
        ref_id          TEXT PRIMARY KEY,
        question_id     TEXT,
        exam_id         TEXT NOT NULL,
        source_doc      TEXT NOT NULL,
        question_text   TEXT NOT NULL,
        answer_text     TEXT NOT NULL,
        year            INTEGER,
        topic_id        TEXT,
        paper_id        TEXT,
        quality_flag    TEXT DEFAULT 'unreviewed',
        notes           TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    -- Key data points from Economic Surveys, Budgets, RBI data
    CREATE TABLE IF NOT EXISTS economic_data_points (
        data_id         TEXT PRIMARY KEY,
        exam_id         TEXT NOT NULL,
        topic_id        TEXT,
        category        TEXT NOT NULL,
        source          TEXT NOT NULL,
        indicator       TEXT NOT NULL,
        value           TEXT NOT NULL,
        year            INTEGER,
        context_text    TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    """)
    conn.commit()


def seed_exam_config(conn: sqlite3.Connection) -> None:
    conn.execute("""
        INSERT OR IGNORE INTO exam_configurations (
            exam_id, exam_name, exam_date,
            w1_pyq_recurrence, w2_pyq_recency, w3_concept_persistence,
            w4_ca_relevance, w5_syllabus_weight, w6_graph_centrality,
            w7_mastery_discount, w8_quiz_only_discount, w9_full_loop_discount,
            paper_ids
        ) VALUES (
            'upsc_eco_opt', 'UPSC Economics Optional (Mains)', '2026-09-15',
            0.22, 0.20, 0.10,
            0.08, 0.12, 0.08,
            0.20, 0.05, 0.15,
            '["upsc_p1","upsc_p2"]'
        )
    """)
    conn.commit()


def verify(conn: sqlite3.Connection) -> None:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    exam = conn.execute(
        "SELECT exam_id, exam_date FROM exam_configurations WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()

    print("\n── Stage 1 (UPSC) Sense Check ──────────────────────")
    print(f"Tables created : {len(tables)}")
    for t in tables:
        print(f"  ✓ {t[0]}")
    print(f"\nexam_configurations seeded:")
    print(f"  exam_id   : {exam[0]}")
    print(f"  exam_date : {exam[1]}")

    expected = 21  # 16 IES tables + 5 new
    assert len(tables) >= expected, f"Expected {expected}+ tables, got {len(tables)}"
    print(f"\n✓ All {len(tables)} tables created")
    print("────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    if DB_PATH.exists() and DB_PATH.stat().st_size > 4096:
        print(f"DB already initialised at {DB_PATH} ({DB_PATH.stat().st_size} bytes). Skipping.")
        sys.exit(0)

    conn = get_connection()
    print("Creating tables...")
    create_tables(conn)
    print("Seeding exam configuration...")
    seed_exam_config(conn)
    verify(conn)
    conn.close()
    print(f"DB created at: {DB_PATH}")
