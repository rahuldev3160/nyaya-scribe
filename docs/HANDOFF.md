# HANDOFF — Nyaya Scribe / Descriptive Exams

Last updated: 2026-06-14 (Session 37)

---

## S37 — What was done

**RBI DEPR exam day. IES June 19-21 (5 days away).**

All S37 tasks complete — commit `bc90ab4`, pushed to Railway ✅.

1. **Model review** — confirmed on track; no course changes. All plans (PLAN-014 through PLAN-016) complete.

2. **PLAN-016 deploy** — already deployed (S36 commit pushed before S37 opened). Confirmed via "Everything up-to-date" on push.

3. **m024 — device tracking**: `user_agent TEXT` column on `user_events` (nyaya.db). `log_event()` + `track_page_time()` capture `request.user_agent.string`.

4. **Phase 5 — DB lifecycle centralised**: `g.rbi_conn`, `g.upsc_conn`, `g.english_conn` now opened/closed in `app.py` before_request/teardown. Removed duplicate handlers from 4 blueprints (-93 lines). New helper files: `web/rbi_db.py`, `web/upsc_db.py`, `web/english_db.py`.

5. **Phase 6 — english.db bootstrapped**: `migrations/m025_create_english_db.py` (DB="english") creates schema + copies from ies.db. "english" in DB_PATHS + BOOTSTRAP_DBS. `english_bp.py` uses `g.english_conn`.

6. **Phase 7 — Migration audit check**: `scripts/migrate.py` warns on deploy if any DB has fewer applied migrations than migration files targeting it.

7. **DNS diagnostic**: `ies-descriptive-prep-production.up.railway.app` returned NXDOMAIN on Rahul's machine. Root cause: router DNS refusing `*.railway.app`. Railway shows Online; local gunicorn test confirms all routes working. Fix requires Rahul to run in Terminal.app (not Claude shell):
   ```bash
   sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
   ```
   Or change DNS to 8.8.8.8 in System Settings → Network → WiFi → Details → DNS.

---

## Current DB connection map

| Flask var | File | Contents |
|---|---|---|
| `g.conn` | `data/ies.db` | IES questions, rubrics, model answers, attempts, mastery |
| `g.rbi_conn` | `data/rbi.db` | RBI MCQs, attempts, gap state |
| `g.upsc_conn` | `data/upsc.db` | UPSC questions, rubrics, model answers, attempts |
| `g.nyaya_conn` | `data/nyaya.db` | users, sessions, user_events (identity + events) |
| `g.english_conn` | `data/english.db` | English question types, questions, keywords, attempts |

---

## Next session — pending tasks (ordered by priority)

1. **IES exam prep** (June 19-21) — 5 days. No dev work during exam week.
2. **Monitor engagement metrics** after PLAN-016: check `drill_attempt` / `return_quiz_submitted` counts in nyaya.db via Railway SSH.
3. **Check user_agent breakdown** once m024 collects data — mobile vs desktop split.
4. **Unprocessed batch outputs**: `data/rbi_mcq_batch.txt`, `data/upsc_answers_batch.txt`, `data/upsc_rubrics_batch.txt` — Anthropic batch API results not yet imported.
5. **9 remaining NotebookLM episodes**: `scripts/generate_remaining.sh` — GE-03 A2b/A3a/A3b/A4 + GE-04 A1c/A2/A3/A4/A5.
6. **Post-exam review**: after IES June 19-21, assess which features to build for UPSC run.
