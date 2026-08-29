---
id: PLAN-020
type: plan
project: descriptive-exams
date: 2026-08-29
status: DRAFT — schema sketch only, nothing created or applied
---

# PLAN-020: `law.db` schema draft (Nyaya Arena law track, DECIDE-36)

**Scope note:** This is a reviewable draft only. No file was added to `migrations/`, no
`data/law.db` was created, and `scripts/migrate.py`'s `DB_PATHS` was not touched — the
migration runner auto-applies anything in `migrations/` on every app start (confirmed by
reading `web/app.py`'s `_run_content_migrations()` → `scripts/migrate.py::main()`), so
adding a live migration file here would risk it running against a real database before
Rahul has seen or approved the schema. This file is the schema for review; turning it
into a real `migrations/mNNN_law_db.py` + wiring `g.law_conn` into `web/app.py` (per
DECIDE-36) is a separate, later step.

Per DECIDE-36: reuse the existing `pyq_questions` / `model_answers` / `rubrics` shape
(see `data/ies.db`'s real schema, read directly for this draft) rather than inventing a
new shape. `exam_id` values below cover CLC DU semester exams (confirmed bilingual,
100 marks/3hrs/8 questions/answer-5-of-8/pass-45 — Nyaya-Arena `docs/research.md`
RESEARCH-01) and Rajasthan Judicial Service (prioritized per DECIDE-08/RESEARCH-04).

```sql
-- New, standalone database: data/law.db (does not touch ies.db/rbi.db/upsc_eco_opt.db/nyaya.db)

CREATE TABLE pyq_questions (
    question_id     TEXT PRIMARY KEY,
    exam_id         TEXT NOT NULL,        -- 'clc_du_sem1' | 'rjs_mains' | ... (extend per DECIDE-08 backlog)
    paper_id        TEXT NOT NULL,        -- e.g. 'LB-102' (Contract), 'LB-103' (Torts), 'LB-106' (Jurisprudence)
    year            INTEGER NOT NULL,
    question_text   TEXT NOT NULL,
    language        TEXT NOT NULL DEFAULT 'bilingual',  -- 'en' | 'hi' | 'bilingual' -- new column, ies/rbi/upsc have no equivalent (RISK-02)
    topic_id        TEXT NOT NULL,
    subtopic_id     TEXT,
    marks           INTEGER NOT NULL DEFAULT 20,        -- CLC DU: 100/5 answered = 20 marks/question
    answer_length   TEXT,
    key_concepts    TEXT,
    question_hash   TEXT
);

CREATE TABLE model_answers (
    answer_id            TEXT PRIMARY KEY,
    question_id          TEXT NOT NULL REFERENCES pyq_questions(question_id),
    exam_id              TEXT NOT NULL,
    language             TEXT NOT NULL DEFAULT 'bilingual',  -- must match the answer's actual language, not just the question's
    intro_text           TEXT NOT NULL,
    body_text            TEXT NOT NULL,
    conclusion_text      TEXT NOT NULL,
    key_terms_used       TEXT,
    critique_json        TEXT,
    needs_review         INTEGER DEFAULT 0,
    overall_quality      TEXT,
    generator_model      TEXT,
    generated_at         TEXT DEFAULT (datetime('now')),
    version              INTEGER DEFAULT 1
);

CREATE TABLE rubrics (
    rubric_id       TEXT PRIMARY KEY,
    question_id     TEXT NOT NULL REFERENCES pyq_questions(question_id),
    exam_id         TEXT NOT NULL,
    dimension       TEXT NOT NULL,        -- e.g. 'issue_identification', 'application_of_law', 'structure'
    max_marks       REAL NOT NULL,
    description     TEXT NOT NULL
);

CREATE TABLE law_attempts (
    attempt_id       TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL,       -- Scribe's own real user_id (nyaya.db), same isolation pattern as ies/rbi
    question_id      TEXT NOT NULL REFERENCES pyq_questions(question_id),
    exam_id          TEXT NOT NULL,
    language         TEXT NOT NULL,       -- language the STUDENT actually answered in
    answer_text      TEXT NOT NULL,
    score            REAL,
    max_score        REAL NOT NULL,
    dimensions_json  TEXT,                -- per-rubric-dimension breakdown, matches API_CONTRACTS.md's descriptive result shape
    feedback         TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_law_pyq_exam ON pyq_questions(exam_id, paper_id, year);
CREATE INDEX idx_law_attempts_user ON law_attempts(user_id, exam_id);
```

## Deliberate deviations from the ies.db shape, and why
- **`language` column added to every table** — ies/rbi/upsc_eco_opt have no bilingual
  concept at all; this is CLC DU's defining feature, not optional here.
- **`law_attempts` is new** — ies.db's equivalent attempts live in a differently-shaped
  table not reused verbatim, since law needs `language` threaded through per-attempt
  (a student may answer some of their 5 questions in Hindi, some in English).
- **No `diagram_*`/`_tex` columns from `model_answers`** — those are IES/UPSC-specific
  (economics diagrams); law model answers are prose-only. Add back only if a real need
  surfaces (Rule 4 — don't pre-build for a hypothetical).

## Explicitly not part of this draft
- No `g.law_conn` wiring in `web/app.py` (DECIDE-36's own scope note).
- No actual PYQ content — Phase 5b's real ingestion needs official-source sourcing
  (Bar Council/DU Faculty of Law/court sites) and Rahul's 5–10 sample validation per
  RISK-03's protocol before any bulk seed. Nothing here is real exam content.
- No `migrations/mNNN_law_db.py` file — see scope note at top.

## Next step, if Rahul wants to proceed
1. Rahul reviews this schema.
2. Turn it into a real numbered migration + `g.law_conn` wiring, following the exact
   pattern `m057_rbi_attempts_source_column.py` and `internal_arena.py`'s RBI cutover
   already established.
3. Only then does real PYQ sourcing (Phase 5b) start.
