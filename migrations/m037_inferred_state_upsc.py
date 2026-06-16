"""Add inferred_state columns to upsc.db gap_states for implicit tracking."""
DB = "upsc"


def run(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gap_states)")}
    if "inferred_state" not in cols:
        conn.execute("ALTER TABLE gap_states ADD COLUMN inferred_state TEXT")
    if "inferred_at" not in cols:
        conn.execute("ALTER TABLE gap_states ADD COLUMN inferred_at TEXT")
    conn.commit()
