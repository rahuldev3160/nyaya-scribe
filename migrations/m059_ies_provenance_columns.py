"""m059 — ies.db: add source_type provenance columns (PLAN-021 Area 6, Scribe half)

DRAFT — DO NOT MERGE TO main / DO NOT DEPLOY until Rahul explicitly approves.
This repo's own CLAUDE.md requires explicit sign-off for any ALTER TABLE on an
existing live table with real user data. Written and tested against a LOCAL COPY
of ies.db only (2026-08-30) -- never run against the real data/ies.db file, and
this repo's scripts/migrate.py auto-applies every pending migration on the next
Railway deploy, so this file must stay off `main` until approved (see PR/commit
notes for exactly what was tested).

Additive only: nullable TEXT column, backfilled with sensible defaults, no
existing column/constraint/data touched.

Verified before writing this file (all 1,219 rows checked, not just sampled):
zero contamination found in ies.db's pyq_questions (unlike upsc_gs.db's BUG-035
gs1-3 problem) -- every row is a legitimate exam question. All 1,219 model_answers
rows confirmed generator_model='claude-sonnet-4-6' (100% AI-generated, matches
DECIDE-27).
"""

DB = "ies"


def run(conn):
    conn.executescript("""
    ALTER TABLE pyq_questions ADD COLUMN source_type TEXT DEFAULT 'official_pyq';
    ALTER TABLE model_answers ADD COLUMN source_type TEXT DEFAULT 'ai_generated';
    """)
    conn.commit()
