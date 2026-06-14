"""Create english.db with all English practice tables, copying data from ies.db."""
import sqlite3
from pathlib import Path

DB = "english"

_IES_DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS english_question_types (
    type_id TEXT NOT NULL, exam_id TEXT NOT NULL DEFAULT 'english_practice',
    type_name TEXT NOT NULL, description TEXT,
    section_labels_json TEXT, section_weights_json TEXT,
    rubric_type TEXT, sort_order INTEGER DEFAULT 0,
    PRIMARY KEY (type_id, exam_id)
);
CREATE TABLE IF NOT EXISTS english_questions (
    question_id TEXT NOT NULL, exam_id TEXT NOT NULL DEFAULT 'english_practice',
    type_id TEXT NOT NULL, prompt_text TEXT NOT NULL,
    marks INTEGER, word_guide_json TEXT, word_count_target INTEGER,
    section_weights_json TEXT, intro_text TEXT, body_text TEXT,
    conclusion_text TEXT, difficulty TEXT DEFAULT 'medium',
    source_exam TEXT, created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (question_id, exam_id)
);
CREATE TABLE IF NOT EXISTS english_keywords (
    keyword_id TEXT NOT NULL, question_id TEXT NOT NULL,
    exam_id TEXT NOT NULL DEFAULT 'english_practice',
    section TEXT NOT NULL CHECK(section IN ('intro','body','conclusion')),
    keyword TEXT NOT NULL, variants_json TEXT, weight INTEGER DEFAULT 1,
    keyword_type TEXT DEFAULT 'required'
        CHECK(keyword_type IN ('required','bonus','negative','phrase')),
    fuzzy_threshold REAL DEFAULT 0.82, penalty REAL,
    PRIMARY KEY (keyword_id, exam_id)
);
CREATE TABLE IF NOT EXISTS english_attempts (
    attempt_id TEXT NOT NULL, exam_id TEXT NOT NULL DEFAULT 'english_practice',
    user_id TEXT NOT NULL, question_id TEXT NOT NULL,
    user_answer_intro TEXT, user_answer_body TEXT, user_answer_conclusion TEXT,
    word_count_intro INTEGER DEFAULT 0, word_count_body INTEGER DEFAULT 0,
    word_count_conclusion INTEGER DEFAULT 0,
    score_intro REAL DEFAULT 0.0, score_body REAL DEFAULT 0.0,
    score_conclusion REAL DEFAULT 0.0, auto_score REAL DEFAULT 0.0,
    self_assess_score REAL DEFAULT 0.0,
    keywords_matched_json TEXT, keywords_missed_json TEXT,
    self_assess_json TEXT, session_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (attempt_id, exam_id)
);
CREATE INDEX IF NOT EXISTS idx_english_attempts_user
    ON english_attempts(user_id, exam_id, created_at DESC);
"""


def run(conn):
    conn.executescript(_SCHEMA)

    if not _IES_DB_PATH.exists():
        return

    ies = sqlite3.connect(str(_IES_DB_PATH))
    ies.row_factory = sqlite3.Row
    try:
        for table in ("english_question_types", "english_questions", "english_keywords", "english_attempts"):
            try:
                rows = ies.execute(f"SELECT * FROM {table}").fetchall()
            except Exception:
                continue
            if not rows:
                continue
            cols = rows[0].keys()
            placeholders = ",".join("?" * len(cols))
            col_names = ",".join(cols)
            conn.executemany(
                f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})",
                [tuple(r) for r in rows],
            )
        conn.commit()
    finally:
        ies.close()
