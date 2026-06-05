# PLAN-009 — S19: RBI Dashboard Redesign + Sidebar Overhaul

**Date:** 2026-06-06 (Session 19)
**Status:** COMPLETE

---

## Context

Two research agents audited all 4 dashboards + sidebar + RBI prep page before implementation.
Goal: public-facing UX — make every page self-explanatory without clicking into sub-pages.

---

## Changes

### 1. `rbi_key_data` DB table (rbi.db)
- 40 items across 6 sections seeded from Python constant (app.py `_run_rbi_migrations()`)
- `is_must_know=1` on 6 items: Repo Rate, CRR, SLR, NPA trigger, GFD FY26-27 BE, Real GDP growth FY26
- Schema: data_id, section, section_color, section_sort, item_name, item_value, item_note, needs_verify, is_must_know, sort_order

### 2. RBI Dashboard (`/rbi`) — `rbi_dashboard.html` + `rbi_dashboard_bp.py`
New layout (always visible, no click needed):
- **Must-Know panel** (left): 6 must-know facts inline + `<details>` expand to all 40 grouped by section
- **My Progress panel** (right): 4 stat cards (Mastery, Readiness, Qs Attempted, Topics ≥50%) + `<details>` for subject bars
- **Subject Coverage**: 3 worst bars visible + `<details>` expand to all
- **Top Gaps**: 3 gaps visible + `<details>` expand to remaining
- **Action buttons**: "Priority 1 MCQs — Smart Session" + "Priority 2 Quiz" + "Full Key Data"

### 3. RBI Prep (`/rbi/prep`) — `rbi_prep.html`
- Tab "Phase 1 Drill" → **Priority 1 MCQs**
- Tab "Tier 2 Quiz" → **Priority 2**
- Added info-box under each tab explaining what it contains
- All internal text references updated (score labels, empty states, completion messages)

### 4. Sidebar — `base.html`
Restructured from 5 groups (16 links) to 3 groups (17 links — cleaner grouping):
- **Dashboards**: IES 2026, RBI Grade B, UPSC Mains, English (cleaner labels)
- **Study & Practice**: IES PYQ Answers, Study Brief, IES Quiz, IES Past Papers (was "Return Quiz"), RBI Priority 1, RBI Priority 2, UPSC Mains Topics, English Practice
- **Track & Account**: My Progress, Answer Review, Feedback, Setup, Profile, Sign Out

### 5. CSS — `style.css`
Added:
- `.expand-section` / `.expand-arrow` — `<details>/<summary>` styled expand toggle (blue arrow, rotates on open)
- `.dash-panel` — inline dashboard panel (replaces bare gem-card where summary content goes)
- `.dash-panel-title` — small uppercase label for panel headings
- `.kd-row`, `.kd-name`, `.kd-value` — key data row layout

---

## Design principles applied
- "Summary + expand" pattern everywhere: show 3–6 items, `<details>` for the rest
- No content hidden behind page navigation — everything on the dashboard
- Consistent section headings (`.dash-panel-title`) across all inline panels
- Labels clarify function: "Priority 1 MCQs" not "Phase 1 Drill"
