"""m067 — upsc_eco_opt.db: add model_revealed/revealed_at/input_mode to
descriptive_attempts (PLAN-024 Phase 1). See m066's docstring for the shared rationale.
"""

DB = "upsc_eco_opt"


def run(conn):
    conn.executescript("""
    ALTER TABLE descriptive_attempts ADD COLUMN model_revealed INTEGER DEFAULT 0;
    ALTER TABLE descriptive_attempts ADD COLUMN revealed_at TEXT;
    ALTER TABLE descriptive_attempts ADD COLUMN input_mode TEXT DEFAULT 'typed';
    """)
    conn.commit()
