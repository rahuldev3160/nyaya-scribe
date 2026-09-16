"""m066 — ies.db: add model_revealed/revealed_at/input_mode to descriptive_attempts
(PLAN-024 Phase 1). Part of the Topper-Grounded Compare Loop's shared attempt-tracking
schema, mounted identically across ies/upsc_eco_opt/upsc_gs's descriptive_attempts tables
plus upsc_gs's essay_attempts (see m067-m069) and ethics_attempts, which already has
model_revealed/revealed_at and only needs input_mode (m070).

input_mode records how the answer was captured (typed/photo/canvas) — canvas capture itself
(PLAN-024 Phase 2) depends on this column existing first.
"""

DB = "ies"


def run(conn):
    conn.executescript("""
    ALTER TABLE descriptive_attempts ADD COLUMN model_revealed INTEGER DEFAULT 0;
    ALTER TABLE descriptive_attempts ADD COLUMN revealed_at TEXT;
    ALTER TABLE descriptive_attempts ADD COLUMN input_mode TEXT DEFAULT 'typed';
    """)
    conn.commit()
