# Deploying Nyaya Scribe to Google Cloud Run

**Scaffolding only.** Nothing in this doc or the `infra/cloud-run-scaffold` branch
provisions any GCP resource, spends money, or touches DNS. These are the exact commands
Rahul runs himself, in order. This is the GCP-specific companion to
`docs/PORTABLE_HOSTING.md` (generic Docker portability) and `DEPLOY.md` (Railway/Hetzner) —
read those first for the parts that don't change (seed→live DB copy-on-first-boot logic,
the `docker/Dockerfile`-must-not-move-to-repo-root lesson).

## 0. What changed in code to make this possible

**Nothing.** `docker/Dockerfile` and `docker/.dockerignore` already exist (built
2026-08-29/30 for portable hosting) and already do exactly what Cloud Run needs: bind
`0.0.0.0:$PORT` (default 8080), run the same `python3 scripts/migrate.py && gunicorn
--chdir web 'wsgi:app' --bind 0.0.0.0:$PORT ...` command as `railway.toml`, and never bake
`data/` into the image. Cloud Run's GCS FUSE volume mount (step 3) just mounts over
`/app/data` at container start — the existing `VOLUME /app/data` line in the Dockerfile is
inert on Cloud Run (Cloud Run ignores Docker `VOLUME`/uses its own mount mechanism) but
harmless to leave in place, since it still documents the mount path correctly.

`RECALL_API_URL` (`web/blueprints/_recall_client.py`) and `OAUTH_REDIRECT_URI`
(`web/auth.py`) were already read from env with `localhost` defaults for local dev — no
code fix needed, just real values at deploy time (step 4).

## Prerequisites

Same GCP project setup as nyaya-core's `docs/DEPLOY.md` (same project if you want one
bill): `gcloud auth login`, `gcloud config set project <PROJECT_ID>`,
`gcloud services enable run.googleapis.com artifactregistry.googleapis.com storage.googleapis.com`.
**Verify current Cloud Run free tier limits/region eligibility at
cloud.google.com/run/pricing before deploying** — written 2026-09-18, terms can change.

## 1. Backup current data first (this repo's own existing tooling)

```bash
bash scripts/backup_production_data.sh
```

This pulls a fresh dated copy of all 6 real DB files off Railway's volume — do this before
any first upload to GCS so the hosted copy starts from the actual latest production state,
not a stale local copy.

## 2. Create the GCS bucket and upload data (one-time)

```bash
gcloud storage buckets create gs://nyaya-scribe-data --location=asia-south1 --uniform-bucket-level-access

# Upload the freshest backup from step 1 (adjust the timestamp to match):
gsutil -m rsync -r data/railway-backup-<timestamp> gs://nyaya-scribe-data
```

The 6 live DB files (`ies.db`, `rbi.db`, `upsc_eco_opt.db`, `nyaya.db`, `english.db`,
`upsc_gs.db`) should land directly at the bucket root so the Cloud Run mount path below
matches `data/<file>.db` exactly as the app already expects.

## 3. Build and deploy

```bash
gcloud run deploy nyaya-scribe \
  --source . \
  --dockerfile docker/Dockerfile \
  --region asia-south1 \
  --allow-unauthenticated \
  --add-volume=name=data,type=cloud-storage,bucket=nyaya-scribe-data \
  --add-volume-mount=volume=data,mount-path=/app/data \
  --set-env-vars="ANTHROPIC_API_KEY=<key>,GOOGLE_CLIENT_ID=<id>,GOOGLE_CLIENT_SECRET=<secret>,OAUTH_REDIRECT_URI=https://scribe.fluxdev.in/0_Login,ARENA_SERVICE_API_KEY=<shared-secret>,RBI_CONTENT_SOURCE=local,RECALL_API_URL=<Devthorium Cloud Run URL, once deployed>,INTERNAL_API_KEY_SCRIBE_RBI=<shared-secret-matching-devthorium>" \
  --memory=1Gi \
  --execution-environment=gen2
```

Notes:
- `--allow-unauthenticated` — this app is public-facing (real users sign in via Google
  OAuth); Cloud Run network access isn't the access-control layer here, `@login_required` +
  `g.user_id` in the app already is (per this repo's own `CLAUDE.md`).
- GCS FUSE has no file locking. This is fine here because, per this task's own research,
  Scribe's real write pattern is low-concurrency user actions (quiz attempts, profile
  updates) — not the kind of high-frequency concurrent-writer load that needs real file
  locking. If usage ever grows past that, revisit before it becomes a real bug (silent
  write loss under true concurrent access is the failure mode to watch for, not a crash).
- Leave `RBI_CONTENT_SOURCE=local` unless Rahul has explicitly approved the PLAN-008 §3
  cutover to `recall` — this matches the existing `.env.example` warning verbatim, this
  scaffolding doesn't change that decision.
- The deploy prints a URL like `https://nyaya-scribe-xxxxx-uc.a.run.app`. Once DNS (step 5)
  points `scribe.fluxdev.in` at it, `OAUTH_REDIRECT_URI` above must match exactly what's
  registered in Google Cloud Console (step 4).

## 4. Update Google OAuth redirect URI

In Google Cloud Console → APIs & Services → Credentials → your OAuth 2.0 Client ID: add
`https://scribe.fluxdev.in` to Authorized JavaScript origins and
`https://scribe.fluxdev.in/0_Login` to Authorized redirect URIs (alongside the existing
Railway ones, until Railway is decommissioned).

## 5. DNS + smoke test

1. Point `scribe.fluxdev.in` at the Cloud Run URL (registrar DNS: CNAME to
   `ghs.googlehosted.com` for a verified custom domain mapping, or use `gcloud run domain-
   mappings create` — check current Cloud Run custom-domain docs, the exact flow has
   changed over time).
2. Sign in with a real Google account → confirm onboarding + dashboard load (proves the
   GCS-mounted DB is readable/writable).
3. Test with a second Google account to confirm user isolation still holds.
4. Only decommission Railway once this is verified stable for a few days — same discipline
   `docs/PORTABLE_HOSTING.md` already documents.

## Not touched by this scaffolding

- `data/` in this repo (including the uncommitted `data/nyaya.db` runtime change already
  present on `main` when this branch was cut) — untouched, unstaged, uncommitted here.
- `railway.toml` / the live Railway deployment.
- The `RBI_CONTENT_SOURCE=local` → `recall` cutover decision (PLAN-008 §3).
