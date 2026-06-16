# Handoff — Descriptive Exams (Nyaya Scribe)
**Session:** S39 → S40 | 2026-06-16 | Branch: main

## Active Work
- PLAN-017 Phase 1 ✅ · Phase 2 PYQ: 221 seeded (GS4 solid, GS1-3 thin — official PDFs needed)
- UI-REDESIGN-001 Phase 1 ✅ — 11 changes shipped · Pending: GS toggle stub (item 3)
- PLAN-017 Phase 3 next: Flask blueprints for GS tab

## Done This Session
- m034 migration: widened gs4_keywords.keyword_category CHECK (7→22 values)
- scripts/setup_upsc_gs.py: seeded 15 thinkers + 123 keywords + 430 synonyms
- scripts/parse_mrunal_pyqs.py + seed_upsc_gs_pyqs.py: 221 PYQs in upsc_gs.db
- Fixed 2 seed bugs: `TARGET_DB`→`DB` in migration; synonym source `'seed'`→`'human'`
- UI: mobile nav UPSC replaces Quick Drill (4 tabs, CSS-MOB-001 safe)
- UI: sidebar brand "Nyaya Scribe"; Feedback+Setup demoted to bottom
- UI: removed duplicate IES CTA + all Reset buttons from topic rows
- UI: fixed UPSC duplicate `id` bug + scroll anchor (#topics→#upsc-papers)
- UI: merged duplicate RBI metrics grid (Mastery/Readiness/Topics removed)
- UI: fixed broken `/dashboard#ies-progress` anchor
- CSS: topic-row 6-col→5-col desktop, 4-col→3-col mobile
- Created MASTER_INDEX.md (9 DECIDEs, 5 SCHEMAs, 2 PLANs, 4 METHODs, 4 RISKs)

## PYQ Coverage Gap
GS4: 93q (2013-2025) ✅ · GS1: 62q · GS2: 29q · GS3: 37q
Root cause: Mrunal pages are topic samples, not year banks
**To complete**: download UPSC official PDFs from upsc.gov.in/examinations/previous-question-papers → drop in `data/cache/upsc_gs_pdfs/` → `python3.11 scripts/parse_upsc_gs_pdfs.py && python3.11 scripts/seed_upsc_gs_pyqs.py`

## Next Actions (start here)
1. **Phase 3 blueprints**: create `web/blueprints/gs_dashboard_bp.py` (route `/upsc?section=gs_mains`) mirroring `upsc_dashboard_bp.py` but reading `g.upsc_gs_conn`
2. Add UPSC tab GS toggle in `web/templates/upsc_dashboard.html` after line 16 (see UI-REDESIGN-001 item 3 for exact HTML)
3. Register `gs_dashboard_bp` in `web/app.py` alongside upsc_dashboard_bp
4. PYQ gap: download official PDFs manually when available

## Files Modified
- migrations/m034_upsc_gs_widen_keyword_category.py (new — fix CHECK constraint)
- scripts/setup_upsc_gs.py (new — GS4 thinker/keyword seed)
- scripts/parse_mrunal_pyqs.py (new — Mrunal scraper)
- scripts/parse_upsc_gs_pdfs.py (new — PDF parser, ready for manual PDF drop)
- scripts/fetch_upsc_gs_pdfs.py (new — PDF fetcher)
- scripts/seed_upsc_gs_pyqs.py (new — PYQ DB seeder, schema-corrected)
- .knowledge/plans/UI-REDESIGN-001.md (new — full audit + ranked plan)
- .knowledge/plans/PLAN-017.md (Phase 1+2 completion records)
- .knowledge/INDEX.md (S39 entries)
- MASTER_INDEX.md (new — 9 decisions + schema + patterns)
- web/templates/base.html (mobile nav + sidebar)
- web/templates/dashboard.html (duplicate CTA + Reset removed)
- web/templates/upsc_dashboard.html (id bug + Reset + header)
- web/templates/rbi_dashboard.html (duplicate metrics merged)
- web/templates/progress.html (broken anchor fixed)
- web/blueprints/upsc_dashboard_bp.py (scroll anchor fix)
- web/static/style.css (topic-row grid)
- .gitignore (upsc_gs.db + nyaya.db + cache/ + logs/ added)

## Blockers
None. PYQ gap needs manual PDF download (upsc.gov.in is CloudFlare-protected).

## Context Pointers — load ONLY if task requires
| Need | Read |
|---|---|
| Full PLAN-017 detail + PYQ sources | .knowledge/plans/PLAN-017.md |
| UI redesign plan + pending items | .knowledge/plans/UI-REDESIGN-001.md |
| Bug/audit history | .knowledge/INDEX.md |
| All architectural decisions | MASTER_INDEX.md |
| Architecture spec | docs/FOUNDATION.md |
| Migration runner | scripts/migrate.py |
| GS4 seed (thinkers/keywords) | scripts/setup_upsc_gs.py |
