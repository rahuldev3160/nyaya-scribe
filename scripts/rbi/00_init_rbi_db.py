"""Initialize rbi.db with 5-table schema for the RBI DEPR MCQ bank."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"


def ensure_schema(conn) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS rbi_questions (
        id              TEXT PRIMARY KEY,
        question        TEXT NOT NULL,
        option_a        TEXT NOT NULL,
        option_b        TEXT NOT NULL,
        option_c        TEXT NOT NULL,
        option_d        TEXT NOT NULL,
        correct_option  TEXT NOT NULL CHECK(correct_option IN ('A','B','C','D')),
        explanation     TEXT NOT NULL,
        subject         TEXT NOT NULL,
        topic           TEXT NOT NULL,
        subtopic        TEXT DEFAULT '',
        dimension       TEXT DEFAULT 'definition'
                        CHECK(dimension IN ('definition','trap','application','calculation','comparison','statement')),
        tier            INTEGER DEFAULT 1 CHECK(tier IN (1,2)),
        difficulty      TEXT DEFAULT 'medium' CHECK(difficulty IN ('easy','medium','hard')),
        is_core_concept INTEGER DEFAULT 0,
        is_recent_dev   INTEGER DEFAULT 0,
        is_trap         INTEGER DEFAULT 0,
        question_type   TEXT DEFAULT 'standard'
                        CHECK(question_type IN ('standard','statement_based','scenario','calculation')),
        tags            TEXT DEFAULT '[]',
        priority_weight REAL DEFAULT 1.0,
        created_at      TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS rbi_attempts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         TEXT NOT NULL DEFAULT 'rahul',
        question_id     TEXT NOT NULL,
        answer_given    TEXT NOT NULL CHECK(answer_given IN ('A','B','C','D')),
        is_correct      INTEGER NOT NULL CHECK(is_correct IN (0,1)),
        time_taken_s    INTEGER,
        session_id      TEXT,
        created_at      TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (question_id) REFERENCES rbi_questions(id)
    );

    CREATE TABLE IF NOT EXISTS rbi_topic_mastery (
        user_id         TEXT NOT NULL DEFAULT 'rahul',
        topic           TEXT NOT NULL,
        subject         TEXT NOT NULL,
        attempts        INTEGER DEFAULT 0,
        correct         INTEGER DEFAULT 0,
        mastery_score   REAL DEFAULT 0.0,
        coverage_pct    REAL DEFAULT 0.0,
        flag_impact     REAL DEFAULT 0.0,
        gap_state       TEXT DEFAULT 'UNVISITED'
                        CHECK(gap_state IN ('UNVISITED','IN_STUDY','DECAYING','VERIFIED','FLAGGED')),
        last_updated    TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (user_id, topic)
    );

    CREATE TABLE IF NOT EXISTS rbi_sessions (
        session_id      TEXT PRIMARY KEY,
        user_id         TEXT NOT NULL DEFAULT 'rahul',
        mode            TEXT NOT NULL CHECK(mode IN ('smart_serve','filter')),
        filter_params   TEXT DEFAULT '{}',
        total_questions INTEGER DEFAULT 0,
        correct         INTEGER DEFAULT 0,
        started_at      TEXT DEFAULT (datetime('now')),
        ended_at        TEXT
    );

    CREATE TABLE IF NOT EXISTS rbi_topic_weights (
        topic           TEXT PRIMARY KEY,
        subject         TEXT NOT NULL,
        base_weight     REAL NOT NULL,
        exam_mcqs_2024  INTEGER NOT NULL,
        phase2_present  INTEGER DEFAULT 0,
        trend           TEXT DEFAULT 'stable' CHECK(trend IN ('stable','increasing','declining')),
        notes           TEXT DEFAULT ''
    );

    CREATE INDEX IF NOT EXISTS idx_questions_subject   ON rbi_questions(subject);
    CREATE INDEX IF NOT EXISTS idx_questions_topic     ON rbi_questions(topic);
    CREATE INDEX IF NOT EXISTS idx_questions_tier      ON rbi_questions(tier);
    CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON rbi_questions(difficulty);
    CREATE INDEX IF NOT EXISTS idx_questions_is_trap   ON rbi_questions(is_trap);
    CREATE INDEX IF NOT EXISTS idx_questions_is_recent ON rbi_questions(is_recent_dev);
    CREATE INDEX IF NOT EXISTS idx_attempts_user       ON rbi_attempts(user_id, question_id);
    CREATE INDEX IF NOT EXISTS idx_mastery_user        ON rbi_topic_mastery(user_id);
    CREATE INDEX IF NOT EXISTS idx_rbi_sess_user       ON rbi_sessions(user_id);
    """)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    ensure_schema(conn)
    conn.close()
    print(f"rbi.db initialised at {DB_PATH}")


if __name__ == "__main__":
    init_db()
