"""m069 — upsc_gs.db: add model_revealed/revealed_at/input_mode to essay_attempts
(PLAN-024 Phase 1). See m066's docstring for the shared rationale. essay_attempts'
attempt_id is TEXT (unlike descriptive_attempts' INTEGER PK) -- irrelevant to this
additive column change, noted for anyone writing cross-table query logic later.
"""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""
    ALTER TABLE essay_attempts ADD COLUMN model_revealed INTEGER DEFAULT 0;
    ALTER TABLE essay_attempts ADD COLUMN revealed_at TEXT;
    ALTER TABLE essay_attempts ADD COLUMN input_mode TEXT DEFAULT 'typed';
    """)
    conn.commit()
