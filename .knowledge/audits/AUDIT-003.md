# AUDIT-003 — Auth & Event Recording Flow
Date: 2026-06-07 (Session 32)
Scope: Full journey audit — user sign-in → DB recording → event logging
Method: Code trace + live production DB query via Railway SSH

## Trigger
User observed no users in local `data/nyaya.db` despite knowing real users had signed in.
Root cause: local DB ≠ production DB. Production is on Railway persistent volume.

## Production State (as of audit)
- 36 users (33 onboarding complete, 3 stuck at setup)
- 945 events across 6 types
- Railway persistent volume at `/app/data` is working correctly

## Journey Map

| Step | Route | DB Write |
|------|-------|----------|
| Click link | GET / | None |
| Login page | GET /auth/login | None (CSRF in cookie) |
| Click Google | POST /auth/login | None |
| Google OAuth | Google-side | None |
| Callback | GET /auth/callback | **users row + sessions row → nyaya.db** |
| Index | GET / | None (validate_session reads only) |
| Dashboard | GET /dashboard | **~80 rows → ies.db** (init_user) |
| → new user | redirect /setup | page_view NOT logged (redirect before track_page_time) |
| Setup | GET+POST /setup | **users updated + config_changed events → nyaya.db** |

## Bugs Found

### BUG-A: Mixed event types (HIGH) — FIXED S32 `203f8cf`
- `page_view` (449), `page_visit` (269), `page_time` (50) — analytics split across 3 labels
- Fix: `normalize_event_types` migration in `_run_nyaya_migrations()` — one-time UPDATE guarded by `_migrations` table

### BUG-B: Dashboard visit never logged for new users (MEDIUM) — FIXED S32 `203f8cf`
- `dashboard_bp.py`: redirect to /setup fired BEFORE `track_page_time`
- Fix: moved `track_page_time()` to immediately after `init_user()`, before any branching

### BUG-C: `log_event()` conn parameter ignored + silent fallback (MEDIUM) — FIXED S32 `203f8cf`
- Dead `conn` param removed from signature; early return when uid is falsy or matches env-var fallback
- `upsert_user()` now returns `(user_id, is_new)`; `g.user_id` set before any `log_event()` call in auth_bp
- `signed_up` event fires on first OAuth login only

### BUG-D: track_page_time() daemon threads lost on gunicorn worker recycle (LOW) — OPEN
- `daemon=True` threads killed when worker is recycled; page_view events near restart silently dropped
- Deferred per DECIDE-S27-01: fire-and-forget analytics loss acceptable for now
- Fix if analytics completeness required: drop `daemon=True` flag

## Non-bugs (confirmed working)
- Railway persistent volume at /app/data — survives redeploys ✓
- upsert_user() + create_session() both commit in callback — users correctly persisted ✓
- validate_session() correctly JOINs users — orphaned sessions are rejected ✓
- init_user() called before onboarding redirect — ies.db initialised for all users ✓
- Orphaned sessions in local DB — testing artifacts, harmless

## 3 Users Stuck at Onboarding
- Sunil Singh (click.singh.su@gmail.com) — 1 event, signed in, never set up
- surjeet patel (sppatel1447270@gmail.com) — onboarding_completed=0
- Sushant kr Ganguli (sushantkrganguly@gmail.com) — onboarding_completed=0
- They are permanently redirected to /setup on every login until they complete it
