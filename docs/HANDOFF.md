# HANDOFF — Nyaya Scribe / Descriptive Exams

Last updated: 2026-06-16 (Session 38)

---

## S38 — What was done

**Pure planning session. No code written.**

### UPSC GS Mains expansion — PLAN-017 complete

6 parallel sub-agents researched all 4 GS papers (GS1 History/Geo/Culture/Society, GS2 Polity/Governance/IR, GS3 Economy/Environment/Tech/Security, GS4 Ethics/Integrity/Aptitude). Full plan written to `.knowledge/plans/PLAN-017.md`.

**Architecture decision:** New `upsc_gs.db` (not expanding `upsc.db`). `exam_id='upsc_gs_mains'`, `paper_id` values: gs1/gs2/gs3/gs4. New Flask connection `g.upsc_gs_conn` + `web/upsc_gs_db.py`. Three new blueprints: `gs_dashboard_bp`, `gs_quiz_bp`, `gs4_ethics_bp`. GS accessed under UPSC nav tab (toggle EO / GS Mains) — no 5th tab (CSS-MOB-001).

**Content pipeline:** ~935 PYQs across 4 papers. Migrations m020-m026. AI cost estimate ~$4.54 ($9-10 with buffer). Sources confirmed: 2019-2024 from upsc.gov.in (text PDFs), 2013-2018 from Mrunal.org.

**Key decisions:**
- GS4 Ethics: concept frequency not question recurrence for w1; concept dependency graph; 3-tier mastery (Tier 3 mini case study mandatory for VERIFIED); self-assess only (no AI descriptive scoring)
- Disaster Management: `floor_priority=0.40` + `w5=0.40` (section_weight_overrides table) — only 16 PYQs in 12 years
- GS3 Economy / Economics Optional: `eco_opt_bridges` table; Python-merge (SYNC-001 pattern); no priority transfer from opt mastery
- IR model answers: 180-day auto-stale; pending legislation stale in 30d
- GS3 Economy model answers: placeholder tokens (`[FISCAL_DEFICIT_FY26]`) filled at render from `economic_indicators` table
- 2013-2018 OCR: pdftotext first → pytesseract fallback if <50 words/page
- Technology recurrence: scored at L2 level (policy structure), not L3 (specific missions)
- Cross-paper linking: 9 link types, 30 critical links; materialised in `bridge_topic_scores`
- Ethics thinkers top 5: Gandhi(0.97), Vivekananda(0.93), Kant(0.90), Aristotle(0.88), Ambedkar(0.88)
- Taxonomy: GS1 9L1/47L2/182L3; GS2 7L1/40L2/145L3; GS3 7L1/42L2/148L3; GS4 6L1/42 concepts

---

## Current DB connection map

| Flask var | File | Contents |
|---|---|---|
| `g.conn` | `data/ies.db` | IES questions, rubrics, model answers, attempts, mastery |
| `g.rbi_conn` | `data/rbi.db` | RBI MCQs, attempts, gap state |
| `g.upsc_conn` | `data/upsc.db` | UPSC Economics Optional questions, rubrics, model answers, attempts |
| `g.nyaya_conn` | `data/nyaya.db` | users, sessions, user_events (identity + events) |
| `g.english_conn` | `data/english.db` | English question types, questions, keywords, attempts |
| `g.upsc_gs_conn` | `data/upsc_gs.db` | **PENDING** — GS Mains: all 4 papers questions, rubrics, model answers, ethics concepts |

---

## S38 — Exact next step

**Start implementation of PLAN-017 Phase 1:**

1. Write `web/upsc_gs_db.py` — copy `web/upsc_db.py` exactly, swap all `upsc` references to `upsc_gs`
2. Write `migrations/m020_upsc_gs_core_tables.py` — creates `topics`, `pyq_questions`, `model_answers`, `question_rubrics`, `gap_states`, `gap_state_events`, `user_mastery`, `return_quiz_questions`, `descriptive_attempts`, `topic_base_scores`, `_migrations` with the GS-specific ALTER TABLE additions from PLAN-017
3. Add `"upsc_gs"` to `scripts/migrate.py` → DB_PATHS
4. Add `g.upsc_gs_conn` open/close to `web/app.py` before_request + teardown_appcontext
5. Write `scripts/setup_upsc_gs.py` to create seed DB with taxonomy

Full implementation order and file list in `.knowledge/plans/PLAN-017.md`.

---

## Previous sessions

## S37 — What was done

**RBI DEPR exam day. IES June 19-21 (5 days away).**

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
