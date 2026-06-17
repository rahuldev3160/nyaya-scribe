"""Add self_rating column to upsc_eco_opt.db descriptive_attempts.

m016 added self_rating to ies.db only; UPSC dashboard queries
CASE da.self_rating ... crash with 'no such column' without this.
"""
DB = "upsc_eco_opt"


def run(conn):
    try:
        conn.execute("ALTER TABLE descriptive_attempts ADD COLUMN self_rating TEXT")
        conn.commit()
    except Exception:
        pass  # column already exists — safe to skip
