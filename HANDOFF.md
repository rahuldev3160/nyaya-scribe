# Handoff — Nyaya Scribe (Descriptive Exams)
**Session:** S45 → S46 | 2026-06-26 | Branch: main

## Active Work
PLAN-018 Phase 4 — Essay AI scoring (`_score_essay()` + `essay_eval` feature gate) ⏳ pending
PLAN-017 Phase 2+ — GS Mains blueprints + PYQ completion ⏳ pending
UI-REDESIGN-001 Phase 2b — Photo eval (handwritten → Claude Vision scoring) ⏳ deferred

## Done This Session (S45)
- .env created with ANTHROPIC_API_KEY (key from Devthorium project)
- Batch test mode: 4 items; BUG-029 fixed (_parse_json non-greedy regex → greedy with rfind)
- Full batch: 108 items; BUG-030 fixed (max_tokens 2048→4096 for Section B STAKE)
- Result: 36/36 essay model answers + 75/75 ethics model answers in upsc_gs.db
- web/blueprints/essay_bp.py — 5 routes (/upsc/essay, /upsc/essay/<id>, /upsc/essay/<id>/submit, /upsc/essay/pyq, /upsc/essay/framework-guide)
- web/blueprints/ethics_paper_bp.py — 4 routes (/upsc/ethics, /upsc/ethics/<paper_id>, /upsc/ethics/<paper_id>/q/<question_id>, /upsc/ethics/framework-guide)
- 9 new templates: essay_landing.html, essay_detail.html, essay_framework.html, ethics_landing.html, ethics_paper.html, ethics_question.html, ethics_framework.html
- web/app.py — essay_bp + ethics_paper_bp registered
- upsc_dashboard.html + upsc_mains.html — 4-item module toggle added (Eco Optional | GS Mains | Essay Paper | Ethics Paper)
- App boots clean; 9 new routes all respond correctly

## Exact Next Step (S46 start here)
**Phase 4 — Essay AI scoring:**
1. Open `web/blueprints/essay_bp.py` — add `_score_essay(attempt_text, essay_prompt, framework_id)` using claude-haiku-4-5-20251001
2. Scoring rubric: intro:20 + body:40 + challenges+solutions:20 + concl:20 = 100
3. Gate: `can_use_feature(g.user_id, "essay_eval")` from `web/db.py` (same pattern as ies_quiz_bp.py `_score_answer`)
4. On submit in essay_submit route: call `_score_essay()`, store in `essay_attempts.ai_score_json` + `ai_score_overall`
5. First verify `essay_eval` gate exists: `sqlite3 data/upsc_gs.db "SELECT * FROM feature_gates WHERE gate_id='essay_eval'"`
   → If missing: INSERT row (quota_free=15, quota_period='monthly')

**After essay scoring:**
- PLAN-017 Phase 2+ — GS1-3 PYQ data (680 questions gap; manual PDF download from upsc.gov.in)
- UI-REDESIGN-001 Phase 2b — Photo eval (POST /practice/submit-photo → Claude Vision)

## Files Modified This Session (S45)
- `web/blueprints/essay_bp.py` — new
- `web/blueprints/ethics_paper_bp.py` — new
- `web/templates/essay_landing.html` — new
- `web/templates/essay_detail.html` — new
- `web/templates/essay_framework.html` — new
- `web/templates/ethics_landing.html` — new
- `web/templates/ethics_paper.html` — new
- `web/templates/ethics_question.html` — new
- `web/templates/ethics_framework.html` — new
- `web/templates/upsc_dashboard.html` — 4-item module toggle added
- `web/templates/upsc_mains.html` — 4-item module toggle added
- `web/app.py` — essay_bp + ethics_paper_bp registered
- `scripts/generate_model_answers_batch.py` — BUG-029 fix (_parse_json) + BUG-030 fix (max_tokens=4096 for Section B)
- `.env` — created (not committed — in .gitignore)
- `data/upsc_gs.db` — 111 model answers inserted (36 essay + 75 ethics)
- `.knowledge/INDEX.md` — BUG-029, BUG-030 added
- `.knowledge/plans/PLAN-018.md` — Phase 2+3 marked complete
- `.knowledge/plans/PLAN-019.md` — Phase 2+3 marked complete
- `MASTER_INDEX.md` — DECIDE-34, DECIDE-35 added; RISK-08 mitigated

## Blockers
- Essay AI scoring: verify `essay_eval` gate exists in feature_gates before wiring
- GS1-3 PYQ gap: ~680 questions missing — manual PDF download required
- nyaya_seed.db missing feature_gates tables (needed before next prod deploy)

## Pending Decisions
- DECIDE-32: Cross-DB topic linking (Y → master_topics; N → document only)
- DECIDE-33: rbi.db year column (Y → ALTER TABLE; N → keep is_recent_dev flag)

## Context Pointers
| Need | Read |
|---|---|
| Essay scoring rubric + gate spec | .knowledge/plans/PLAN-018.md — "AI Scoring Rubric" section |
| Existing AI scoring pattern | web/blueprints/ies_quiz_bp.py `_score_answer()` |
| Feature gate API | web/db.py `can_use_feature()` |
| Photo eval spec | .knowledge/plans/UI-REDESIGN-001.md |
| GS Mains PYQ pipeline | .knowledge/plans/PLAN-017.md |
| All decisions (DECIDE-01 to DECIDE-35) | MASTER_INDEX.md |
| Bug history | .knowledge/INDEX.md |
