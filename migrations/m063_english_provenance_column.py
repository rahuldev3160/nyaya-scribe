"""m063 — english.db: add source_type provenance column to english_questions (PLAN-021 Area 6)

DRAFT — DO NOT MERGE TO main / DO NOT DEPLOY until Rahul explicitly approves.
See m059's docstring for why.

english.db has no separate pyq_questions/model_answers split -- english_questions
(22 rows) embeds both the prompt and the model answer (intro_text/body_text/
conclusion_text) in one row. Checked all 22 rows: entirely hand-authored-style
practice content (essay/precis/RC prompts with a `source_exam` style tag like
'upsc_style'/'rbi_2024', not a real official-exam citation) -- confirmed synthetic,
not sourced from any real past paper. 'ai_generated' for all rows.
"""

DB = "english"


def run(conn):
    conn.executescript("""
    ALTER TABLE english_questions ADD COLUMN source_type TEXT DEFAULT 'ai_generated';
    """)
    conn.commit()
