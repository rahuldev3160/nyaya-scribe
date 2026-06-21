# Handoff — Nyaya Scribe (Descriptive Exams)
**Session:** S43 → S44 | 2026-06-21 | Branch: main @ 5f2e5f0

## Active Work
PLAN-018 Phase 1 — Essay module migrations + seed scripts ⏳ pending
PLAN-019 Phase 1 — Ethics module migrations + seed scripts ⏳ pending
UI-REDESIGN-001 Phase 2b — Photo eval (handwritten → Claude Vision scoring) ⏳ pending
PLAN-017 Phase 2+ — GS Mains blueprints + PYQ completion ⏳ pending

## Done This Session (S43)
- PLAN-018 created: UPSC Essay Paper module — adaptive annual CA→essay pipeline, PART A/B/C framework with body_dimensions_json, 36 questions planned (8 PYQ-2024 + 8 PYQ-2025 + 20 practice-2026), combined 315-item Anthropic Batch API plan
- PLAN-019 created: GS4 Ethics paper simulation — IDEA-U (Section A theory) + STAKE (Section B case studies), 13-year research done, 2 practice papers designed, self-compare only (no AI scoring)
- DECIDE-25 through DECIDE-31 logged + SCHEMA-09 through SCHEMA-15 logged in MASTER_INDEX.md
- PLAN-018 + PLAN-019 added to MASTER_INDEX.md PLAN table; RISK-08 added
- .knowledge/INDEX.md updated with both plans
- Adaptive architecture: essay count/year/framework/hook all data in DB registries; annual refresh = 2 script runs, zero code change (DECIDE-25)
- Indexing layer: normalized junction tables (essay_thinker_links, ethics_concept_links, ethics_thinker_links, ethics_scenario_links) + FTS5 virtual tables replacing JSON blobs (DECIDE-30)
- CSS-MOB-001 compliance: essay + ethics enter as toggle states inside UPSC tab, not new nav tabs

## Exact Next Step (S44 start here)
**Answer two questions first** (determines Tier 3 scope of indexing work — see AUDIT-008):
1. Cross-DB topic linking: should "Monetary Policy" in IES + RBI + essay share a single canonical topic entity in nyaya.db? (Y → master_topics project; N → column-name consistency only)
2. rbi.db year data: do the seeded rbi_questions have known exam years, or were they compiled without year attribution?

Then begin **Tier 1 indexing** (safe, no decisions needed):
- Write `docs/SCHEMA_CONVENTIONS.md` (naming rulebook — see AUDIT-008 for the 7 proposed rules)
- Write `migrations/m047_ies_indexes.py` (DB="ies") — 3 missing indexes + DROP stale tables after grep
- Write `migrations/m048_eco_opt_indexes.py` (DB="upsc_eco_opt") — 5 missing indexes
- Write `migrations/m049_english_indexes.py` (DB="english") — 2 missing indexes
- Write `migrations/m050_rbi_composite.py` (DB="rbi") — 1 composite index

Then **essay/ethics migrations** (m039–m046 in upsc_gs.db) — confirm question_id format for essay/ethics before writing (proposed: `essay_a_2024_001`, `ethics_b_2024_c01_s01`).

## Files Modified This Session
- `.knowledge/plans/PLAN-018.md` — new (S43)
- `.knowledge/plans/PLAN-019.md` — new (S43)
- `.knowledge/audits/AUDIT-008.md` — new (S43) — global DB schema + indexing audit
- `.knowledge/INDEX.md` — PLAN-018 + PLAN-019 + AUDIT-008 added
- `MASTER_INDEX.md` — DECIDE-25..31, SCHEMA-09..15, PLAN-018/019, RISK-08 added
- `HANDOFF.md` — this file

## Blockers
GS1-3 PYQ gap: ~680 questions missing. Needs manual download from upsc.gov.in → drop in `data/cache/upsc_gs_pdfs/` → `python3.11 scripts/parse_upsc_gs_pdfs.py && python3.11 scripts/seed_upsc_gs_pyqs.py`

## Context Pointers — load ONLY if task requires
| Need | Read |
|---|---|
| Essay Paper module full spec (schema, 36 Qs, batch plan) | .knowledge/plans/PLAN-018.md |
| Ethics Paper module full spec (IDEA-U, STAKE, 2 practice papers) | .knowledge/plans/PLAN-019.md |
| Full product redesign plan (Phases 2b onward) | .knowledge/plans/UI-REDESIGN-001.md |
| GS Mains blueprint spec + PYQ pipeline | .knowledge/plans/PLAN-017.md |
| All architectural decisions (DECIDE-01 to DECIDE-31) | MASTER_INDEX.md |
| Bug/audit history | .knowledge/INDEX.md |
| Feature gate schema + freemium logic | migrations/m035_feature_gates.py |
| AI scoring helper + tool schema | web/blueprints/ies_quiz_bp.py `_score_answer()` |
| Optional subject expansion map | web/app.py `_UPSC_OPT_DB_MAP` (~line 17) |
