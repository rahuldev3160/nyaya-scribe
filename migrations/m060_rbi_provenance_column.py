"""m060 — rbi.db: add source_type provenance column to rbi_questions (PLAN-021 Area 6)

DRAFT — DO NOT MERGE TO main / DO NOT DEPLOY until Rahul explicitly approves.
See m059's docstring for why -- same rule applies to all five provenance migrations
in this batch (m059-m063).

rbi.db has no separate pyq_questions/model_answers tables like ies/upsc_eco_opt/
upsc_gs -- it has one MCQ table, rbi_questions (321 rows), which is the exact same
content that lives in Recall's question_bank as exam_source='rbi_grade_b' (see
Devthorium commit e0a20db, same session). That backfill traced the real origin to
scripts/rbi/02_generate_mcq_bank.py (Haiku batch, from data/notebooklm/
rbi_theory_mcq_source.md) -- 100% AI-generated, no official RBI Grade B PYQ+
answer-key source exists (confirmed via B-13). Same finding applies here.
"""

DB = "rbi"


def run(conn):
    conn.executescript("""
    ALTER TABLE rbi_questions ADD COLUMN source_type TEXT DEFAULT 'ai_generated';
    """)
    conn.commit()
