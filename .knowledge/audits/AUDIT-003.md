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

### BUG-A: Mixed event types (HIGH) — analytics split across 3 labels
- `page_view` (449), `page_visit` (269), `page_time` (50)
- `get_time_breakdown()` only queries `page_view` → misses 319 historical events
- Fix: normalise old types via migration OR expand WHERE clause in get_time_breakdown()

### BUG-B: Dashboard visit never logged for new users (MEDIUM)
- `dashboard_bp.py:89-95`: redirect to /setup fires BEFORE `track_page_time`
- First dashboard visit for every new user is invisible in events
- Fix: log `first_visit` event at line 87 (after init_user, before onboarding check)

### BUG-C: `log_event()` conn parameter ignored + silent fallback (MEDIUM)
- Function signature takes `conn` but internally uses `get_nyaya_conn()` — caller's conn ignored
- `get_user_id()` falls back to `os.environ.get("IES_USER_ID", "rahul")` if g.user_id is None
- FK violation swallowed by bare `except Exception: pass`
- Fix: remove dead `conn` param from signature; validate uid before insert

### BUG-D: track_page_time() daemon threads lost on gunicorn worker recycle (LOW)
- `daemon=True` threads killed when worker is recycled
- page_view events near worker restart silently dropped
- Fix: write synchronously (SQLite write is ~1ms locally)

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
