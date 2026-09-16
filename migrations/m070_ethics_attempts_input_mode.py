"""m070 — upsc_gs.db: add input_mode to ethics_attempts (PLAN-024 Phase 1).
ethics_attempts already has model_revealed/revealed_at from an earlier build (m046) --
this is the one remaining column of the shared 3-column set. See m066's docstring for
the overall rationale.
"""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""
    ALTER TABLE ethics_attempts ADD COLUMN input_mode TEXT DEFAULT 'typed';
    """)
    conn.commit()
