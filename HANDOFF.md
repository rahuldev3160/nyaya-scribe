# Handoff — Nyaya Scribe (Descriptive Exams)
**Session:** S46 → S47 | 2026-07-05 | Branch: main

## Active Work
UI-REDESIGN-001 Phase 2b — Photo eval (handwritten → Claude Vision scoring) ⏳ deferred
PLAN-017 Phase 2+ — GS Mains model answers (not yet generated; questions live on Railway now)

## Done This Session (S46)

### PLAN-018 Phase 4 — Essay AI Scoring ✅
- `web/blueprints/essay_bp.py` — added `_score_essay()` (claude-haiku-4-5, tool_use, 4-dim rubric: intro:20 + body:40 + ch_sol:20 + concl:20)
- `migrations/m051_essay_eval_gate.py` — adds `essay_eval` gate (15 free/month, unlimited pro)
- `essay_submit` route: gates on `essay_eval`, calls `_score_essay()`, stores `ai_score_json` + `ai_score_overall`, redirects with `attempt_id`
- `essay_detail` route: loads attempt scores when `attempt_id` in query
- `web/templates/essay_detail.html` — score breakdown card (overall badge + 4 color bars + feedback)
- Committed `77de724` + deployed to Railway

### BUG: upsc_gs.db content missing on Railway ✅ fixed (m052–m055)
- Root cause: ethics/essay/GS questions were seeded via scripts locally, never in migrations
- Railway had empty schema-only tables; all content was local-only
- `m052` — essay_frameworks, hook_types, theme_analysis, gs4_thinkers, 36 essay questions, 93 ethics questions
- `m053` — 36 essay model answers
- `m054` — 75 ethics model answers  
- `m055` — 221 GS Mains PYQ questions (gs1–gs4)
- All use `INSERT OR IGNORE` — idempotent
- Committed `db8f4bc` + `540172a`

### BUG: GS Mains showing Eco Optional content ✅ fixed
- `upsc_bp.py` (serves `/upsc/mains`) had `_EXAM_ID = "upsc_eco_opt"` + `g.upsc_conn` — completely wrong
- Fix: `_EXAM_ID = "upsc_gs_mains"`, `g.upsc_gs_conn`, paper defaults `gs1–gs4`
- Paper labels updated: GS Paper I–IV with subject labels
- `upsc_mains.html` title corrected

## Exact Next Step (S47 start here)

**Option A — UI Phase 2b: Photo eval**
- `POST /practice/submit-photo` — PIL compress → Claude Vision OCR + eval
- Template: add camera upload option to essay_detail.html or create separate route
- Spec: `.knowledge/plans/UI-REDESIGN-001.md` Phase 2b

**Option B — GS Mains model answers**
- 221 questions exist (gs1–gs4); 0 model answers
- Run batch generation script against upsc_gs.db (same pipeline as essay/ethics)
- See `scripts/generate_answers.py --exam upsc_gs_mains`

**Option C — AUDIT-008 index migrations**
- m047–m050 already committed (ies, eco_opt, english, rbi indexes)
- Verify Railway applied them; confirm with EXPLAIN QUERY PLAN

## Files Modified This Session (S46)
- `web/blueprints/essay_bp.py` — _score_essay() + gate wiring
- `web/blueprints/upsc_bp.py` — _EXAM_ID + conn fixed (GS Mains bug)
- `web/templates/essay_detail.html` — score breakdown card
- `web/templates/upsc_mains.html` — title fixed
- `migrations/m051_essay_eval_gate.py` — new
- `migrations/m052_seed_upsc_gs_questions.py` — new
- `migrations/m053_seed_essay_model_answers.py` — new
- `migrations/m054_seed_ethics_model_answers.py` — new
- `migrations/m055_seed_gs_mains_pyqs.py` — new
- `.knowledge/INDEX.md` — updated
- `.knowledge/plans/PLAN-018.md` — Phase 4 marked complete

## Pending Decisions
- DECIDE-32: Cross-DB topic linking (Y → master_topics; N → document only)
- DECIDE-33: rbi.db year column (Y → ALTER TABLE; N → keep is_recent_dev flag)

## Context Pointers
| Need | Read |
|---|---|
| Photo eval spec | .knowledge/plans/UI-REDESIGN-001.md Phase 2b |
| Essay scoring implementation | web/blueprints/essay_bp.py `_score_essay()` |
| Feature gate API | web/db.py `can_use_feature()` |
| GS Mains PYQ pipeline | .knowledge/plans/PLAN-017.md |
| Bug history | .knowledge/INDEX.md |
