# Portable hosting — readiness package (not a migration plan)

**Status as of 2026-08-29: staying on Railway.** This document does not recommend
moving anywhere right now. Rahul decided to keep Nyaya Scribe on Railway (already
paid for, just brought back online after an outage) rather than migrate immediately.
What follows is a *readiness package* — so that whenever he does decide to move
this to a different server (his own paid hosting, AWS, anywhere else), it's a
same-day task instead of a scramble.

## What "portable" means here, concretely

Three things now exist, on top of the unchanged live Railway deployment:

1. **`Dockerfile`** (repo root) — builds this exact app (same Python version, same
   dependencies, same startup command as `railway.toml`) into a container image that
   runs identically on any machine with Docker installed. Railway itself does **not**
   use this file — Railway still builds via Nixpacks per `railway.toml`, unchanged.
   This Dockerfile is the "take it somewhere else" path, sitting alongside.
2. **`scripts/backup_production_data.sh`** — one command that pulls a fresh copy of
   all 7 real database files off Railway's volume into a local, dated,
   never-committed folder (`data/railway-backup-<timestamp>/`). Re-run this
   periodically (weekly? monthly? — Rahul's call, no schedule is set up
   automatically) so the "adaptable backup" doesn't go stale.
3. **This document.**

## What actually moving to a new server would involve, later

When Rahul is ready (not now):

1. Run `bash scripts/backup_production_data.sh` one more time to get the freshest
   possible copy of all production data.
2. On the new server: install Docker, copy this repo there (or just the
   `Dockerfile` + app code via git clone), and copy the latest
   `data/railway-backup-<timestamp>/` folder to wherever the new server will keep
   its data.
3. `docker build -t nyaya-scribe .`
4. `docker run -p 8080:8080 -v /path/to/copied/backup:/app/data -e ANTHROPIC_API_KEY=... -e ARENA_SERVICE_API_KEY=... nyaya-scribe`
   (see `.env.example` for the full list of environment variables the app needs —
   on Railway these are set in the dashboard; on a new server they'd be passed the
   same way Docker normally takes env vars, or via a `.env` file + `--env-file`).
5. Test the new server thoroughly (login, take a quiz, check a few pages) while
   Railway is still live and serving real traffic.
6. Only once the new server is verified working: point the domain's DNS at the new
   server, and only decommission Railway some time after that once it's clear the
   new host is stable.

Step 5/6 is the part that actually needs care — it's the same "don't cut over until
proven" discipline as any production move, not a Docker-specific concern.

## What this package deliberately does NOT do

- Does not touch `railway.toml` or the live Railway deployment in any way.
- Does not migrate any data anywhere. The backup script only *copies* data out;
  Railway's volume remains the one live source of truth until Rahul explicitly
  decides otherwise.
- Does not pick a new hosting provider. That decision — and whether it's his own
  paid hosting, AWS, or something else — is entirely Rahul's, whenever he's ready.
- Does not set up any automatic/scheduled backups. `backup_production_data.sh` is
  a manual, on-demand command for now.
