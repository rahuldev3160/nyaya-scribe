"""m061 — upsc_eco_opt.db: add source_type provenance columns (PLAN-021 Area 6)

DRAFT — DO NOT MERGE TO main / DO NOT DEPLOY until Rahul explicitly approves.
See m059's docstring for why.

Checked all 908 pyq_questions rows (not just sampled) before writing this: 5 rows
carry an explicit coaching-source attribution ("By Vibhas Jha Sir N", N=1-5) --
a small, easily identified batch, not pervasive contamination like BUG-035's
gs1-3 problem. Those 5 get 'coaching_derived'; the remaining 903 default to
'official_pyq'. All 908 model_answers rows confirmed generator_model=
'claude-sonnet-4-6' (100% AI-generated, matches DECIDE-27).
"""

DB = "upsc_eco_opt"

COACHING_DERIVED_IDS = [
    "upsc_p2_0397", "upsc_p2_0415", "upsc_p2_0417", "upsc_p2_0434", "upsc_p2_0437",
]


def run(conn):
    conn.executescript("""
    ALTER TABLE pyq_questions ADD COLUMN source_type TEXT DEFAULT 'official_pyq';
    ALTER TABLE model_answers ADD COLUMN source_type TEXT DEFAULT 'ai_generated';
    """)
    conn.executemany(
        "UPDATE pyq_questions SET source_type = 'coaching_derived' WHERE question_id = ?",
        [(qid,) for qid in COACHING_DERIVED_IDS],
    )
    conn.commit()
