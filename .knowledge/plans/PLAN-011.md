---
name: PLAN-011
description: S23 — Multi-DB migrations (m003–m008), remove keyword scoring, DB-driven model answers tab, new open-ended essay questions
metadata:
  type: plan
---

# PLAN-011: S23 — English UX overhaul + multi-DB migration extension

**Date:** 2026-06-06 (Session 23)  
**Status:** COMPLETE  

---

## Changes shipped

### 1. Multi-DB migration extension (m003–m007)

Extended `scripts/migrate.py` from IES-only to full multi-DB routing:
- Reads `DB = "ies"|"rbi"|"upsc"` attribute from each migration file via `getattr(mod, "DB", "ies")`
- Lazy-opens only needed DBs; per-DB `done` set; skips absent DB files gracefully
- `DB_PATHS` dict maps all three keys to `data/*.db` paths

New migration files:
- `m003_init_rbi_schema.py` — wraps `scripts/rbi/00_init_rbi_db.py::ensure_schema(conn)`
- `m004_seed_rbi_topic_weights.py` — wraps `scripts/rbi/01_seed_topic_weights.py::seed_into(conn)`
- `m005_seed_rbi_tier2.py` — wraps `scripts/rbi/03_migrate_tier2.py::seed_into(conn)`
- `m006_init_upsc_schema.py` — wraps `scripts/upsc/init_upsc_db.py::create_tables + seed_exam_config`
- `m007_seed_upsc_topics.py` — wraps topic seeder with `config/topics_upsc_eco.json`

Refactored RBI scripts to expose connection-accepting functions:
- `00_init_rbi_db.py` — added `ensure_schema(conn)`
- `01_seed_topic_weights.py` — added `seed_into(conn)`
- `03_migrate_tier2.py` — added `seed_into(conn)` (skips questions already in DB by ID)

### 2. Removed keyword scoring — model answer comparison

Replaced the 3-phase write→auto_scored→self_assess flow with a 2-phase write→done flow:
- Removed `scoring/` import from `english_bp.py` entirely
- Removed `_load_keyword_schema()`, `criteria`, `rubric_type`, `sec_weights` from GET route
- `_save_attempt()` simplified — stores word counts + raw text only (no score fields)
- POST `/score` route: saves attempt, stores `{qid, intro, body, conclusion}` in session, redirects
- Removed `/practice/english/assess` route entirely
- Done phase in `english.html`: 2-tab compare — "Your Answer" | "Model Answer"

### 3. m008 — 5 new open-ended essay questions

Replaced the original 5 closed/analytical essay questions with UPSC/IES-style open-ended topics:
1. India's informal economy — structural problem or strength to harness?
2. Growth without equity is not development
3. Technology as the great equaliser — critically examine for India
4. Environmental sustainability and economic development are compatible
5. Automation will create more opportunities than it destroys

Each with ~500-word model answers across intro/body/conclusion. Applied via `m008_update_essay_questions.py` (SQL UPDATE by question_id).

### 4. DB-driven Model Answers tab

Replaced hardcoded 5-example HTML in `english_dashboard.html` with a loop over `model_questions` dict:
- Route passes `model_questions = {type_id: [list of questions with model answers]}`
- Template loops `all_types → model_questions[type_id]` — shows every question
- First question in each type starts expanded (`open` attribute)
- Full `prompt_text` rendered above model sections — fixes précis/RC where passage was hidden
- Section label headers pulled from `t.section_labels` (pre-parsed Python dict in `_load_types()`)

**Fix:** `_load_types()` now parses `section_labels_json` → `section_labels` Python dict to avoid Jinja2's missing `fromjson` built-in filter.

**DB state at session end:** 19 questions across 5 types — all have model answers (intro + body at minimum).

---

## Commits

| Hash | Summary |
|---|---|
| `ed19014` | feat(migrations): extend auto-migration to rbi.db + upsc.db |
| `5a006b9` | refactor(english): replace keyword scoring with model answer comparison |
| `9b0b09e` | feat(english): replace hardcoded model answers with DB-driven loop + new essay topics |

---

## Open items (P2/P3)

| Item | Detail |
|---|---|
| Progress tab score columns | Shows "Avg Auto Score / Avg Self Score" — both always 0 after scoring removal. Should be removed or replaced with attempt count / word count stats. |
| Précis word count inconsistency | Insights tab says 150–170w; seed `word_count_target` = 140. Align to one standard. |
| RC marks mismatch | Insights says 5m each; seeds have 10m per question. Audit and fix. |
| Custom domain | `nyayascribe.com` → Railway custom domain + OAuth redirect update (pending domain registration) |
