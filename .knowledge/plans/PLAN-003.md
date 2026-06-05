# PLAN-003 — S15: Multi-Exam Dashboards + Plan Reduction

**Date:** 2026-06-05  
**Session:** S15  
**Status:** COMPLETE

## What was built

### 1. Study plan templates reduced (144 → 24)
- Dropped multi-exam combo `["ies","rbi"]` (edge case, most users prep one exam)
- Collapsed 3 time buckets → 2: `crunch` (≤15d) and `standard` (>15d). "Intensive" removed.
- Collapsed 3 prep levels → 2: `fresh` and `revision`. "Foundation" removed (blurry middle ground).
- Collapsed 4 modes → 2: `answers_only` and `full_prep`. "mcq_drill" and "mixed" removed.
- Files changed: `scripts/generate_study_plan_templates.py`, `web/db.py` (`_days_bucket()`), `web/pages/8_My_Setup.py`

### 2. Exam date labels added everywhere
- IES: "IES 2026 · 19-21 June"
- RBI: "RBI DEPR · 14 June"
- UPSC: "UPSC Eco Optional · ~Aug 2026"
- Source: UPSC Mains 2025 = Aug 22-31 (official). 2026 dates TBD, placeholder Aug 22 used.

### 3. New page: `web/pages/RBI_Dashboard.py`
- Days to June 14 countdown
- Phase 1 drill metrics (answered/total, accuracy, total attempts)
- Formula readiness score (weighted mastery) + gap-adjusted exam readiness
- Subject coverage bars (weighted by topic importance)
- Top gaps list (coverage_pct < 0.5, sorted by flag_impact)
- Quick link to 6_RBI_Prep.py

### 4. New page: `web/pages/UPSC_Dashboard.py`
- Days to ~Aug 22 2026 countdown
- Auto-initializes gap_states for user if missing (same schema as IES)
- Topics verified / in-progress / model answers coverage metrics
- Paper tabs (Paper I Theory, Paper II Indian Economy) with topic state management
- Same advance/verify/reset buttons as IES Dashboard
- Overview state counts

### 5. Dashboard.py hub update
- Reads `exam_focus` from users table
- Shows page_link buttons to RBI/UPSC dashboards if those exams are in user's focus
- Non-disruptive: IES content unchanged

### 6. app.py nav update
- Added `_rbi_dash` (RBI Dashboard) and `_upsc_dash` (UPSC Dashboard) pages
- All three dashboards grouped under "Dashboards" nav section
- IES Dashboard remains default page

## Architecture notes
- RBI Dashboard reads from `rbi.db` directly (same pattern as 6_RBI_Prep.py)
- UPSC Dashboard reads from `upsc.db` with self-contained DB helpers
- Both auth via ies.db (require_user), then close ies connection before opening exam-specific DB
- UPSC Tier 2 quiz scores are session-only (not persisted) — not shown in UPSC Dashboard
- RBI Tier 2 quiz scores also session-only — RBI Dashboard shows Phase 1 drill only
