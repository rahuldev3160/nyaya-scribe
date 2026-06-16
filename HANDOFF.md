# Handoff — Descriptive Exams (Nyaya Scribe)
**Session:** S40 → S41 | 2026-06-16 | Branch: main @ afe431e

## Active Work
- UI-REDESIGN-001 Phase 0 ✅ · Phase 1 next (dashboard redesign + topic browser)
- PLAN-017 Phase 2 partial (221/~900 PYQs; GS1-3 gap needs official PDFs)
- PLAN-017 Phase 3 pending (GS Mains Flask blueprints + UPSC tab toggle)

## Done This Session (S40)
- 3-agent research: edtech UX patterns, feature audit (all 15 blueprints), DB architecture audit
- Product decisions locked: implicit tracking, UPSC GS Mains template, partial-free freemium, 15 evals/mo free, photo eval Phase 2
- m035: feature_gates + user_feature_overrides + user_feature_usage in nyaya.db (5 gates seeded)
- m036/m037: inferred_state + inferred_at on gap_states (ies.db, upsc.db)
- web/db.py: has_feature(), get_monthly_usage(), increment_feature_usage() helpers added
- dashboard.html: removed Begin Study/Mark Partial/Verify forms → Study+Write links; removed state badges, State Overview section, Readiness formula %, self-rating column
- upsc_dashboard.html: removed Quick Verify/advance forms → Study+Write links; removed state badges, State Overview, Verified/In Progress metrics
- ies_quiz.html: removed Got It/Partial/Missed buttons; added live word count bar (red/yellow/green vs target); added collapsible "View Model Answer" panel before submission
- Key discovery: current quiz has NO live AI evaluation (scores_json/weighted_score never populated by web routes) — AI eval is a new feature for Phase 2
- MASTER_INDEX.md: DECIDE-10→17, SCHEMA-06→07, METHOD-05→06, RISK-05→07 added
- Commit afe431e: 7 files, 244 insertions, 170 deletions

## Next Actions (start here)
1. **Phase 1 — Dashboard redesign**: edit `web/templates/dashboard.html` to replace current header metrics with: single recommended-question card (largest element, above fold) + behavior-inferred readiness score (0–100 from attempt data) + exam countdown + daily goal (3 answers/day ○○○). Recommendation algorithm: highest `topic_base_scores.base_priority_score` topic where user has zero attempts OR avg_score < 6.0 AND last attempt > 3 days ago.
2. **Phase 1 — compute_inferred_states.py**: write `scripts/compute_inferred_states.py` using METHOD-06 rules (UNVISITED=0 attempts, LEARNING=avg<5, etc.) — batch script that updates `gap_states.inferred_state` + `inferred_at` for all users × topics.
3. **Phase 1 — Topic browser color coding**: replace state badges in dashboard topic rows with attempt count + avg score + "Refresh recommended" (🔴 avg<4 or never attempted+high priority, 🟢 avg≥7, ⚪ not attempted+lower priority).
4. **Phase 2 — Claude API eval**: add AI scoring to `ies_quiz_bp.quiz_submit()` for premium users (check `has_feature(g.user_id, 'ai_scoring')` + `get_monthly_usage()`); store result in `descriptive_attempts.weighted_score` + `scores_json`; display 5-dimension breakdown in post-submit view.
5. **Phase 2 — Photo eval**: new route `POST /practice/submit-photo`; PIL compress → Claude Vision API call with question + image; same scoring pipeline as typed answers.

## Files Modified (S40)
- migrations/m035_feature_gates.py (new — freemium gating tables in nyaya.db)
- migrations/m036_inferred_state_ies.py (new — gap_states columns, ies.db)
- migrations/m037_inferred_state_upsc.py (new — gap_states columns, upsc.db)
- web/db.py (has_feature + monthly usage helpers added after get_nyaya_conn())
- web/templates/dashboard.html (state buttons removed, Study/Write links, state_summary removed)
- web/templates/ies_quiz.html (Got It/Partial/Missed removed, word count bar, model answer panel)
- web/templates/upsc_dashboard.html (state buttons removed, State Overview removed)

## Blockers
PYQ gap: GS1-3 missing ~680 questions. Needs manual download from upsc.gov.in/examinations/previous-question-papers → drop PDFs in `data/cache/upsc_gs_pdfs/` → run `python3.11 scripts/parse_upsc_gs_pdfs.py && python3.11 scripts/seed_upsc_gs_pyqs.py`

## Context Pointers — load ONLY if task requires
| Need | Read |
|---|---|
| Full product redesign plan (Phases 1-4) | .knowledge/plans/UI-REDESIGN-001.md |
| PLAN-017 PYQ pipeline + GS blueprints | .knowledge/plans/PLAN-017.md |
| All architectural decisions (DECIDE-01 to DECIDE-17) | MASTER_INDEX.md |
| Bug/audit history | .knowledge/INDEX.md |
| Feature gate schema + seeds | migrations/m035_feature_gates.py |
| has_feature() / increment_feature_usage() | web/db.py lines ~99-158 |
