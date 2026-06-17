# AUDIT-007 — Production Funnel Audit (S36)

**Date:** 2026-06-13 (Session 36)  
**Scope:** User activation funnel — signup → onboarding → content engagement  
**Method:** Railway SSH + `sqlite3 data/nyaya.db` + `user_events` analysis  
**Bugs Found:** 3 root causes  
**Fixed:** 3 (PLAN-016, same session)  
**Open:** 0

---

## Production Numbers (as of S36)

| Metric | Count |
|--------|-------|
| Total users | 95 |
| Onboarded (setup complete) | 46 |
| Content engagement (≥1 drill/quiz attempt) | ~2 of 46 |
| Drop-off rate post-onboarding | ~96% |

---

## Root Causes Found

### RC-1 — Post-setup dead end
`setup_bp.py` POST redirected to `/` after plan generation. `index()` defaulted to `/dashboard` for all users. RBI-only and UPSC-only users landed on the IES dashboard — wrong exam, wrong content. No welcome state, no "start here" signal.

**Fix (PLAN-016):** POST now redirects to `/{primary_exam}?welcome=1`. `index()` smart-routes by `exam_focus`.

### RC-2 — No first-action signal on dashboards
All exam dashboards showed the full topic list with no indication of where to start. Zero-attempt users and 50-attempt users saw the same layout. No "Start here" card, no recommended next action.

**Fix (PLAN-016):** First Action card added to IES and RBI dashboards for `attempt_count = 0` users. Welcome banner on `?welcome=1`.

### RC-3 — Nav dead ends for RBI/UPSC-only users
Users who enrolled for RBI only saw "IES Prep" as the default nav highlight. "Quick Drill" in mobile nav slot 3 was the only visible shortcut — but it wasn't labeled clearly as an entry point for first-time users.

**Fix (PLAN-016):** CTA labels updated ("Auto-Pick (Recommended)" on RBI), Must-Know Facts moved above fold on RBI dashboard, button hierarchy improved.

---

## Key Insight

The funnel break was at activation, not acquisition. Users were completing setup (high intent signal) but not taking a single study action. This is a first-session UX failure, not a content or retention failure — addressed entirely through routing and UI changes with no schema changes.
