---
id: DIAG-005
type: diagnostic
project: descriptive-exams
session: 2027-redesign-implementation
date: 2026-08-30
status: RESOLVED
resolution: Dockerfile relocated out of repo root; local-only DB edits converted to real migrations; all verified live via railway ssh
---

# DIAG-005: Root Dockerfile silently broke every Railway deploy for ~2.5 hours across multiple sessions' commits

## What happened

The portable-hosting `Dockerfile` added at the repo root the previous session (commit `6d6ba40`,
2026-08-29 23:43) caused **every single deploy since then to fail at the build stage**. Railway
auto-detects a root-level `Dockerfile` and silently switches its builder away from Nixpacks
regardless of `railway.toml`'s explicit `builder = "NIXPACKS"` setting. That Dockerfile's `VOLUME`
directive isn't supported by Railway's Docker builder, so the build failed immediately every time:
`dockerfile invalid: docker VOLUME at Line 43 is not supported, use Railway Volumes`.

`docs/PORTABLE_HOSTING.md` explicitly (and wrongly) asserted "Railway itself does not use this
file — Railway still builds via Nixpacks per railway.toml, unchanged." That assertion was never
verified against a real deploy before being written.

**Impact:** from 2026-08-29 23:43 to 2026-08-30 ~04:14, every push to `main` (7+ commits across
two more sessions' worth of work — 2027 retargeting, IES nudge, GS4 model answers, RBI English
Sim, provenance migration) triggered a failed deploy. Production kept serving the pre-Dockerfile
build (`485858c`) the entire time. This wasn't caught because `/healthz` on the *old, still-running*
deployment kept returning 200 — a healthy healthcheck on stale code looks identical to a healthy
healthcheck on new code from the outside. Session summaries reported work as "pushed and live"
based on git push success + a healthz check, not on confirming the *active deployment's commit
hash* matched.

## Compounding issue found during the fix

Two pieces of this session's work had been applied via direct `sqlite3` CLI edits (or an
API-generation script) against the **local development copy** of the SQLite DBs
(`data/*.db` in the git working tree) rather than through a `migrations/mNNN_*.py` file:

1. The IES `exam_configurations` 2027 date/name fix.
2. The 81 real GS4 model answers generated via `scripts/upsc_gs/10_generate_answers_gs4.py`.

Local `data/*.db` files and Railway's volume-mounted production DBs are **physically separate
files** — a local edit never reaches production on its own. Only code + `migrations/` files
(which `scripts/migrate.py` applies fresh against whatever DB it's pointed at) travel to
production via deploy. Both were converted into real migrations (`m064`, `m065`) so they'd apply
correctly to Railway's actual volume on the next successful deploy.

## Fix

1. Moved `Dockerfile`/`.dockerignore` to `docker/` (commit `b798a3c`) so Railway's root-level
   auto-detection no longer finds it — Nixpacks builds resumed working immediately.
2. `m064_fix_ies_exam_config_2027.py`, `m065_seed_gs4_model_answers.py` (commit `9c9be3c`) —
   the latter verified by deleting the 81 rows from a throwaway test copy, re-running the
   migration, and confirming exact content match before trusting it.
3. Corrected `docs/PORTABLE_HOSTING.md`'s wrong claim.
4. **Verified against the real live database via `railway ssh`** (not just HTTP/healthz) after
   redeploying: `_migrations` table shows m058-m065 applied on the actual production `rbi.db`/
   `ies.db`/`upsc_gs.db`; `ies.db`'s `exam_configurations` row shows the corrected 2027 name/date;
   `upsc_gs.db.model_answers` has exactly 81 rows; provenance backfill matches the exact expected
   pattern (gs1-3 all NULL, 81 gs4 rows `official_pyq`, 12 excluded gs4 rows NULL).

## Lesson

1. **Never put a `Dockerfile` at the repo root of a project deployed via Railway Nixpacks.**
   Railway's auto-detection overrides `railway.toml`'s explicit builder setting. If a Dockerfile
   must exist for portability/future-migration purposes, it must live in a subdirectory (`docker/`)
   and be built with an explicit `-f` flag, never left where Railway's platform-level
   auto-detection can find it.
2. **"Pushed to git" and "live in production" are not the same claim** — verify the *active
   deployment's commit hash* (`railway status --json` → `activeDeployments[0].meta.commitHash`)
   matches the latest push before reporting anything as live, not just that `/healthz` returns
   200 (a healthy old build looks identical to a healthy new build from a healthcheck alone).
3. **Local `data/*.db` files are dev copies, not production** for any Railway-hosted service with
   a persistent volume. Any real data change meant for production must go through a
   `migrations/mNNN_*.py` file, never a one-off local `sqlite3` edit or a locally-run generation
   script — even when the intent is "apply this to production," a local edit silently only
   changes the local dev copy.
