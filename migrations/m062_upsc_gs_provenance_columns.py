"""m062 — upsc_gs.db: add source_type provenance columns (PLAN-021 Area 6)

DRAFT — DO NOT MERGE TO main / DO NOT DEPLOY until Rahul explicitly approves.
See m059's docstring for why.

DEVIATION FROM PLAN-021's stated backfill ("pyq_questions rows -> official_pyq by
default"): that default is WRONG for this specific DB. .knowledge/bugs/BUG-035.md
(OPEN, CRITICAL) already established that gs1/gs2/gs3 (128 of 221 rows, ~65-90%)
are scraped blog-comment junk, not real exam questions -- and this session's own
GS4 model-answer generation pass (see scripts/upsc_gs/10_generate_answers_gs4.py,
commit c891f7c) found 12 more gs4 rows that are junk (YouTube links/nav text) or
multiple case studies jammed into one row.

Blanket-defaulting all of this to 'official_pyq' would encode FALSE provenance
information for content already known to be unreliable -- directly defeating the
point of an honest provenance taxonomy. Instead:

- All of gs1/gs2/gs3 (128 rows) left source_type = NULL (unclassified) -- BUG-035
  never did a precise row-by-row classification, only a sampled contamination
  estimate, so a false-precision label would be worse than admitting "unresolved."
- The 12 already-identified gs4 junk/jumbled rows (see EXCLUDE_IDS in
  scripts/upsc_gs/10_generate_answers_gs4.py) also left NULL.
- The remaining 81 gs4 rows (the ones this session actually generated model
  answers for) default to 'official_pyq' -- these are real historical GS4 topics,
  even where thin (title-only stems rather than full narratives, per PLAN-021
  Area 3's finding).
- All 81 model_answers rows confirmed generator_model='claude-sonnet-4-6' from
  this session's own generation run -- 'ai_generated' is exact, not inferred.
"""

DB = "upsc_gs"

GS4_EXCLUDED_IDS = [
    "gs4_2025_q07", "gs4_2024_q01", "gs4_2024_q09", "gs4_2023_q09", "gs4_2022_q07",
    "gs4_2024_q03", "gs4_2020_q05", "gs4_2019_q02", "gs4_2016_q03",
    "gs4_2016_q05", "gs4_2016_q09", "gs4_2013_q04",
]


def run(conn):
    conn.executescript("""
    ALTER TABLE pyq_questions ADD COLUMN source_type TEXT;
    ALTER TABLE model_answers ADD COLUMN source_type TEXT DEFAULT 'ai_generated';
    """)
    placeholders = ",".join("?" * len(GS4_EXCLUDED_IDS))
    conn.execute(f"""
        UPDATE pyq_questions
        SET source_type = 'official_pyq'
        WHERE paper_id = 'gs4' AND question_id NOT IN ({placeholders})
    """, GS4_EXCLUDED_IDS)
    # gs1/gs2/gs3 and the 12 excluded gs4 rows stay NULL -- see docstring.
    conn.commit()
