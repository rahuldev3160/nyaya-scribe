"""m058 — rbi.db: create rbi_english_sim_attempts table (PLAN-021 Area 4)

New table only, no ALTER on any existing table -- no approval gate needed.
Backs the RBI Grade B English Descriptive timed-writing simulator: a single
90-minute master countdown across Essay/Precis/RC with per-section sub-budgets,
client-sampled typing-pace tracking, and a post-submission pacing report.
Separate from rbi_attempts (MCQ-only, CHECK constrained to A/B/C/D answers).
"""

DB = "rbi"


def run(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS rbi_english_sim_attempts (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             TEXT NOT NULL,
        session_id          TEXT NOT NULL UNIQUE,
        essay_prompt_id     TEXT,
        precis_passage_id   TEXT,
        rc_passage_id       TEXT,
        essay_text          TEXT,
        precis_text         TEXT,
        rc_answer_text      TEXT,
        essay_budget_s      INTEGER NOT NULL DEFAULT 1800,
        precis_budget_s     INTEGER NOT NULL DEFAULT 1800,
        rc_budget_s         INTEGER NOT NULL DEFAULT 1800,
        essay_time_s        INTEGER,
        precis_time_s       INTEGER,
        rc_time_s           INTEGER,
        total_time_s        INTEGER,
        wpm_samples_json    TEXT,
        pacing_report_json  TEXT,
        essay_score_json    TEXT,
        started_at          TEXT DEFAULT (datetime('now')),
        submitted_at        TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_rbi_eng_sim_user ON rbi_english_sim_attempts(user_id, started_at);
    """)
    conn.commit()
