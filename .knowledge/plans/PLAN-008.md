# PLAN-008 — S19: English Dashboard UX + Feedback Feature

**Date:** 2026-06-06 (Session 19)
**Status:** COMPLETE
**Routes after:** 34 (added /feedback, /feedback/submit)

---

## English Dashboard UX Fixes

**Problem 1: Recent attempts showed raw `question_id` hex code**
- Fixed: added `eq.prompt_text` to the JOIN query in `english_dashboard()` in `english_bp.py`
- Template now shows first 60 chars of prompt as a clickable link to that question in practice

**Problem 2: Practice cards showed question count but no attempt progress**
- Fixed: `attempt_counts` dict (type_id → count) now passed to template
- Cards show a green "N done" chip when attempts > 0

**Problem 3: No way back to English Dashboard from practice page**
- Fixed: added "← English Dashboard" breadcrumb link at top of `english.html`

---

## Feedback Feature

New end-to-end feature for logging bugs, feature requests, and issues.

### Schema (added to `ies.db` via `_run_migrations`)
```sql
CREATE TABLE user_feedback (
    feedback_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'bug'  -- bug | feature | issue | other
        CHECK(category IN ('bug','feature','issue','other')),
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT DEFAULT 'open'
        CHECK(status IN ('open','acknowledged','resolved')),
    created_at TEXT DEFAULT (datetime('now'))
);
```

### Files changed/created
- `web/blueprints/feedback_bp.py` — new blueprint with `GET /feedback` + `POST /feedback/submit`
- `web/templates/feedback.html` — submit form + sorted list of all feedback
- `web/app.py` — `_FEEDBACK_TABLE_SQL` migration + blueprint registration
- `web/templates/base.html` — added "💬 Feedback" nav link under Account section

### Design decisions
- Feedback list shows **all users' submissions** (admin-style) — this is Rahul's personal prep app
- Category displayed as colored left-border card (bug=red, feature=blue, issue=amber)
- Status badge (open/acknowledged/resolved) shown right-aligned per item
- No status-update UI yet — status can be updated directly in SQLite if needed
