# PLAN-016 — Engagement Activation Overhaul
**Date:** 2026-06-13 (Session 36)
**Status:** COMPLETE (commit e51b27a) — deployed to Railway ✅

---

## Context

Production analytics pulled via Railway SSH before implementation:
- **95 users** signed up · **46 onboarded** (completed setup) · **~0 content engagement** from 44/46 onboarded users
- Root causes: post-setup dead end (setup POST redirected to `/`), wrong default landing for RBI/UPSC-only users, nav dead ends that left users with no clear next action

---

## Changes Shipped (8 files)

| File | Change |
|------|--------|
| `web/app.py` | `index()` smart routing — RBI-only users → `/rbi`, UPSC-only → `/upsc`, IES → `/dashboard` |
| `web/blueprints/setup_bp.py` | POST redirects to exam content + `?welcome=1` instead of `/`; GET passes `primary_exam_url` to template |
| `web/blueprints/dashboard_bp.py` | `_FOCUS_LABEL["UNVISITED"]` changed from generic label to `"→ Begin Topic"` |
| `web/templates/setup.html` | "Start Studying →" primary CTA; "⚙️ Change Setup" demoted to secondary |
| `web/templates/base.html` | Answer Review removed from nav; "My Plan" → "Study Plan"; UPSC mobile slot → "⚡ Quick Drill" |
| `web/templates/dashboard.html` | First Action card (0-attempt users) + welcome banner (`?welcome=1`) + CTA hierarchy |
| `web/templates/rbi_dashboard.html` | Must-Know Facts moved above metrics; CTA renames; welcome banner |
| `web/templates/rbi_prep.html` | "Auto-Pick (Recommended)" + "Choose Topic" radio replace unlabelled default |

---

## Key Decisions

- Smart routing in `index()` reads `exam_focus` from nyaya.db enrollment — no new column, reuses existing setup data
- Welcome banner fires once on `?welcome=1` param (no session state or DB write needed)
- "First Action" card targets `attempt_count = 0` users — disappears automatically after first quiz attempt
- No new routes or migrations — pure template + routing changes

---

## Outcome

Post-deploy next steps: monitor `drill_attempt` / `return_quiz_submitted` event counts in nyaya.db; check `user_agent` breakdown (added in S37 follow-up).
