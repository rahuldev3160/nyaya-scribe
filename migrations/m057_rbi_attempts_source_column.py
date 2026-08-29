"""m057 — rbi.db: add rbi_attempts.source column (PLAN-008 §3, approved by Rahul as B-12)

Additive-only: NOT NULL with a DEFAULT, so existing rows are unaffected (SQLite
backfills the default for all prior rows automatically, no rewrite needed).
Distinguishes attempts served via the local rbi_questions table ('local', today's
only value) from attempts served via Recall's internal API ('recall', once
RBI_CONTENT_SOURCE is ever flipped — see web/blueprints/rbi_prep_bp.py).
"""

DB = "rbi"


def run(conn):
    conn.executescript("""
    ALTER TABLE rbi_attempts ADD COLUMN source TEXT NOT NULL DEFAULT 'local';
    """)
    conn.commit()
