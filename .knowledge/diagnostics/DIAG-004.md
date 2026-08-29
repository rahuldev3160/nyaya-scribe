---
id: DIAG-004
type: diagnostic
project: descriptive-exams
session: railway-outage-and-portable-hosting
date: 2026-08-29
status: RESOLVED
resolution: production restored; portable Docker/backup readiness package added
---

# DIAG-004: Production outage (Railway trial expiry + healthcheck bug) + portable hosting package

## What happened

Scribe had been offline for about a month. Two separate, stacked causes:

1. **Railway trial expired.** The project was on the free trial plan, not a paid one.
   Every redeploy attempt failed outright with "Your trial has expired." Fixed by Rahul
   selecting a real plan (`hobby`) on Railway's dashboard — not something Claude Code
   can do (no billing access).
2. **Even after billing was fixed, deploys still failed.** Root cause: `/` always
   redirects (302 to `/auth/login` or `/dashboard`, never a bare 200), but Railway's
   healthcheck (`healthcheckPath = "/"`) requires a direct success status, not a
   redirect — so every deploy was being killed as "unhealthy" even once gunicorn was
   actually up and correctly serving requests. A red herring along the way: raising
   `healthcheckTimeout` (60s → 300s) alone did NOT fix it, because the real problem
   was the status code, not timing (56 migrations running on every startup DID make
   the app slow to boot, real ~60-70s, but that was a secondary factor, not the
   actual blocker).

## Fix

- Added `GET /healthz` → plain `"ok", 200` (`web/app.py`).
- `railway.toml`: `healthcheckPath` → `/healthz`, `healthcheckTimeout` kept at 300 (safety
  margin for the migration-runner startup cost, which is real even though it wasn't the
  root cause).
- Verified live: `/healthz` returns `ok`, `/auth/login` returns a real 200, Railway shows
  the deployment healthy.
- Commits: `5a5f245` (timeout bump), `d26a1dc` (`/healthz` + healthcheck path fix).

## Data safety during the incident

All 7 real `.db` files (`english`, `ies`, `nyaya`, `rbi`, `upsc`, `upsc_eco_opt`, `upsc_gs`)
were confirmed intact on Railway's persistent volume throughout — this was a
deploy/billing outage, never a data-loss risk. A full local copy was pulled and verified
(exact size match + SQLite-openable) at `data/railway-backup-20260829/` (gitignored).

## Portable hosting readiness package (separate follow-up, same session)

Rahul's decision: **stay on Railway for now** (already paid, just restored) — no
migration happening. Built a readiness package so a future move to a different server
is not a scramble:

- `Dockerfile` (repo root) — builds this exact app (Python 3.11, same deps, same
  `railway.toml` startCommand) into a portable container image. Does not change how
  Railway itself deploys (still Nixpacks via `railway.toml`, untouched).
- `.dockerignore` — excludes real data, secrets, `.git`, `.knowledge`, etc. from the
  build context.
- `scripts/backup_production_data.sh` — one-command repeatable backup of all 7 real DB
  files off Railway's volume into a fresh dated `data/railway-backup-<timestamp>/`
  folder, with per-file size verification and up to 3 retries (the Railway CLI's file
  download was observed to occasionally stall/truncate on the larger files, ~10MB+, in
  a single attempt — the retry logic exists specifically because this was reproduced
  during testing, not a hypothetical). Tested end-to-end against the real volume: all 7
  files downloaded, sizes matched exactly, all opened cleanly in SQLite.
- `docs/PORTABLE_HOSTING.md` — plain-language explanation of what "portable" means here,
  explicitly **not** a recommendation to migrate now, and the numbered steps for
  whenever Rahul does decide to move.
- **Docker verification not run**: Docker was not successfully installed on this machine
  during this session (a `brew install --cask docker` attempt hit an interactive sudo
  password prompt that couldn't be satisfied non-interactively). The Dockerfile itself
  has not been `docker build`-tested — flag this to whoever picks up the actual future
  migration: build and smoke-test the image before relying on it for a real cutover.

## Lesson

A healthcheck path returning a redirect instead of a real 200 is a silent, total deploy
blocker that looks identical to "just needs a longer timeout" from the logs alone
(gunicorn genuinely does boot and listen). Any Flask/Django app whose root route
redirects should get a dedicated `/healthz`-style route rather than pointing
infrastructure healthchecks at `/`.
