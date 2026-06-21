# Handoff — Nyaya Scribe (Descriptive Exams)
**Session:** S44 → S45 | 2026-06-21 | Branch: main

## Active Work
PLAN-018 Phase 2 — Essay model answer batch generation ⏳ pending (script written, needs API key)
PLAN-019 Phase 2 — Ethics model answer batch generation ⏳ pending (same script)
PLAN-018/019 Phase 3 — Blueprint + UI ⏳ pending (after batch answers land)
UI-REDESIGN-001 Phase 2b — Photo eval (handwritten → Claude Vision scoring) ⏳ deferred
PLAN-017 Phase 2+ — GS Mains blueprints + PYQ completion ⏳ pending

## Done This Session (S44)
- Migrations m039–m050 applied to upsc_gs.db (essay core tables, proposals, questions, answers, attempts; ethics questions, answers, attempts; ies/eco_opt/english/rbi index gaps)
- All 5 seed scripts ran clean: essay_frameworks (19 rows), essay_questions (36), ethics_concepts (25), ethics_pyq (31), ethics_practice (62) → 173 rows total into upsc_gs.db
- web/utils.py written: parse_search() + build_query() for section-wise search bar (KNOWN_CONCEPTS 42 terms, KNOWN_THINKERS 23, KNOWN_SCENARIOS 13, ESSAY_THEMES 17)
- scripts/generate_model_answers_batch.py written: Anthropic Batch API for 111 model answers (36 essay + 75 ethics), --test-mode --count 4, --poll, --retrieve, id_map in status file

## Exact Next Step (S45 start here)
**Phase 2 batch — unblock with API key:**
1. Create `.env` with `ANTHROPIC_API_KEY=sk-ant-api03-...`
2. Run test mode: `python scripts/generate_model_answers_batch.py --test-mode`
3. Poll: `python scripts/generate_model_answers_batch.py --poll <batch_id>`
4. Retrieve: `python scripts/generate_model_answers_batch.py --retrieve <batch_id>` — verify 1 essay + 3 ethics rows in DB
5. Full batch: `python scripts/generate_model_answers_batch.py` — 111 items, ~$1 at batch pricing

**After batch completes → Phase 3 (Blueprint + UI):**
- `web/blueprints/essay_bp.py` — 6 routes: landing, detail, attempt, results, search, framework_guide
- `web/blueprints/ethics_paper_bp.py` — landing, paper view, question view, framework guide
- HTML templates: essay_landing.html, essay_detail.html, ethics_landing.html, ethics_paper.html, ethics_question.html
- UPSC toggle: add "Essay Paper" + "Ethics Paper" as 3rd/4th toggle states in the UPSC tab
- Section-wise search bars calling parse_search() + build_query() from web/utils.py

## Files Modified This Session (S44)
- `scripts/generate_model_answers_batch.py` — new: Phase 2 Batch API script
- `web/utils.py` — new: parse_search + build_query search utility
- `scripts/essay/seed_frameworks.py` — new: seeds essay_frameworks, hook_types, theme_analysis
- `scripts/essay/seed_questions.py` — new: seeds essay_questions from JSONL
- `scripts/ethics/seed_concepts.py` — new: seeds ethics_concept_analysis + ethics_scenario_analysis
- `scripts/ethics/seed_questions.py` — new: seeds ethics_questions from JSONL (--input flag)
- `data/essay_questions_seed.jsonl` — new: 36 essay questions (8 PYQ-2024 + 8 PYQ-2025 + 20 practice)
- `data/ethics_questions_pyq.jsonl` — new: 31 ethics PYQ 2025 rows
- `data/ethics_questions_practice.jsonl` — new: 62 ethics practice rows (2 papers)
- `migrations/m039_essay_core_tables.py` through `m050_rbi_composite_index.py` — new: 12 migrations
- `data/upsc_gs.db` — modified: 12 migrations applied, 173 seed rows inserted
- `data/nyaya.db` — modified: schema updates from earlier sessions

## Blockers
- ANTHROPIC_API_KEY needed locally to run batch script (create .env)
- GS1-3 PYQ gap: ~680 questions missing. Needs manual download from upsc.gov.in → `data/cache/upsc_gs_pdfs/` → `python3.11 scripts/parse_upsc_gs_pdfs.py && python3.11 scripts/seed_upsc_gs_pyqs.py`
- nyaya_seed.db missing feature_gates, user_feature_overrides, user_feature_usage, user_feedback tables (needed before next prod deploy)

## Pending Decisions (Stale from S43 — no blocker on Phase 3)
- DECIDE-32: Cross-DB topic linking (Y → master_topics project; N → document only)
- DECIDE-33: rbi.db year column (Y → ALTER TABLE; N → keep is_recent_dev flag)

## Context Pointers — load ONLY if task requires
| Need | Read |
|---|---|
| Essay Paper module full spec (schema, 36 Qs, batch plan) | .knowledge/plans/PLAN-018.md |
| Ethics Paper module full spec (IDEA-U, STAKE, 2 practice papers) | .knowledge/plans/PLAN-019.md |
| Batch script usage + id_map design | scripts/generate_model_answers_batch.py |
| Search utility API (parse_search, build_query) | web/utils.py |
| Full product redesign plan (Phases 2b onward) | .knowledge/plans/UI-REDESIGN-001.md |
| GS Mains blueprint spec + PYQ pipeline | .knowledge/plans/PLAN-017.md |
| All architectural decisions (DECIDE-01 to DECIDE-32) | MASTER_INDEX.md |
| Bug/audit history | .knowledge/INDEX.md |
| Feature gate schema + freemium logic | migrations/m035_feature_gates.py |
| AI scoring helper + tool schema | web/blueprints/ies_quiz_bp.py `_score_answer()` |
