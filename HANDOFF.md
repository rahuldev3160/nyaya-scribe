# Handoff — Nyaya Scribe (Descriptive Exams)
**Session:** S42 → S43 | 2026-06-17 | Branch: main @ 3f8a529

## Active Work
UI-REDESIGN-001 Phase 2b — Photo eval (handwritten → Claude Vision scoring) ⏳ pending
PLAN-017 Phase 2+ — GS Mains blueprints + PYQ completion ⏳ pending

## Done This Session
- `upsc.db` → `upsc_eco_opt.db` rename: 18 files updated (migrate.py key, 5 migration DB= decls, app.py path + _boot_db + legacy-rename guard, upsc_db.py, profile_bp, progress_bp, all scripts/upsc/*.py, compute/generate/ingest scripts, templates, docs)
- `_UPSC_OPT_DB_MAP` stub added to web/app.py (DECIDE-23) — future optional subjects plug in here
- Knowledge base brought current: PLAN-016, BUG-026, BUG-027, AUDIT-007 created; UI-REDESIGN-001 + INDEX updated
- BUG-028 (CRITICAL, production 500): `self_rating` column missing from upsc_eco_opt.db — m016 was ies.db-only; S41 UPSC hero strip queries `da.self_rating` in 3 places; fixed by m038, pushed + deployed ✅
- DECIDE-24 + L-DEV-56 logged: shared-schema table migrations must have companion for every exam DB
- UPSC page confirmed working on production (200 OK)

## Next Actions (start here)
1. **Phase 2b — Photo eval:** `POST /ies/practice/submit-photo` in `web/blueprints/ies_quiz_bp.py`; base64 JPEG in Anthropic `image/jpeg` content block; reuse `_score_answer()` tool schema with Vision OCR step; gate under `can_use_feature(user_id, "photo_eval")`
2. **RBI dashboard Phase 1:** Add hero strip (recommended card + readiness/100 + daily ●○○) to `web/templates/rbi_dashboard.html` — mirror pattern from `web/blueprints/upsc_dashboard_bp.py` lines 110–174
3. **GS Mains blueprints:** Create `web/blueprints/gs_dashboard_bp.py` (mirrors upsc_dashboard_bp), register in app.py, add toggle to upsc_dashboard.html — upsc_gs.db already has 221 PYQs, no new DB work

## Files Modified
- `web/app.py` — `_UPSC_OPT_DB_MAP`, `_UPSC_DB_PATH`, `_boot_db("upsc_eco_opt")`, legacy-rename guard
- `web/upsc_db.py` — path constant → upsc_eco_opt.db
- `scripts/migrate.py` — DB key "upsc" → "upsc_eco_opt"
- `migrations/m038_add_self_rating_upsc.py` — new, production fix for BUG-028
- `migrations/m006,m007,m014,m023,m028,m037` — DB= declaration updated
- `seeds/upsc_eco_opt_seed.db` — renamed from upsc_seed.db
- `MASTER_INDEX.md` — DECIDE-23, DECIDE-24 added
- `.knowledge/` — PLAN-016, BUG-026/027/028, AUDIT-007 created; INDEX updated

## Blockers
GS1-3 PYQ gap: ~680 questions missing. Needs manual download from upsc.gov.in → drop in `data/cache/upsc_gs_pdfs/` → `python3.11 scripts/parse_upsc_gs_pdfs.py && python3.11 scripts/seed_upsc_gs_pyqs.py`

## Context Pointers — load ONLY if task requires
| Need | Read |
|---|---|
| Full product redesign plan (Phases 2b onward) | .knowledge/plans/UI-REDESIGN-001.md |
| GS Mains blueprint spec + PYQ pipeline | .knowledge/plans/PLAN-017.md |
| All architectural decisions (DECIDE-01 to DECIDE-24) | MASTER_INDEX.md |
| Bug/audit history | .knowledge/INDEX.md |
| Feature gate schema + freemium logic | migrations/m035_feature_gates.py |
| AI scoring helper + tool schema | web/blueprints/ies_quiz_bp.py `_score_answer()` |
| Optional subject expansion map | web/app.py `_UPSC_OPT_DB_MAP` (~line 17) |
