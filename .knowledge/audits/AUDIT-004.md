# AUDIT-004 — Data Flow Architecture Audit

**Date:** 2026-06-07 (Session 33)
**Scope:** Full data flow audit across all exam domains — RBI, IES, UPSC, English + shared
**Method:** 4 parallel agents + inline DB queries
**Agents:** RBI (inline), IES (subagent), UPSC (subagent), English+shared (subagent)
**Bugs found:** 8 problem classes, 2 live bugs fixed same session
**Plan created:** PLAN-014

---

## Summary Table

| Domain | Data largely in DB? | Hardcoded Python blobs | Live bugs found |
|---|---|---|---|
| RBI | Partial — 4 copies of same data | KEY_SECTIONS (75 lines), BUCKETS MCQs, _RBI_KEY_DATA_SEED (40 rows) | GDP rank wrong (4th→6th), fixed S33 |
| IES | Yes — questions/answers/rubrics all DB | Paper labels × 5 files, exam date × 2 files, gap state metadata × 8 locations | Exam date hardcoded but correct |
| UPSC | Yes — similar schema to IES | Paper labels × 2 files (diverged punctuation), exam date constant | Exam date 24 days wrong (fixed S33) |
| English | Partial — questions in DB, types seed on every request | QUESTION_TYPES_SEED in english_bp.py | None critical |

---

## Problem Class 1 — INSERT OR IGNORE Drift (highest risk)

`INSERT OR IGNORE` prevents existing DB rows from ever being updated by Python source changes. Content that changes (facts, rates, dates) should use `INSERT OR REPLACE`.

| Location | Table | Runs when | Risk |
|---|---|---|---|
| `web/app.py:95–155` `_RBI_KEY_DATA_SEED` (40 rows) | `rbi_key_data` (rbi.db) | Every app boot | **CRITICAL** — exam-critical numbers (Repo Rate, CRR, GDP rank) silently stale. Already caused GDP bug. |
| `web/blueprints/english_bp.py:59` `QUESTION_TYPES_SEED` (5 rows) | `english_question_types` (ies.db) | Every `/english` request | MEDIUM — type descriptions can't be updated in DB |
| `migrations/init_db.py:399` | `exam_configurations` (ies.db) | Migration (once) | LOW — formula weights (w1–w9) need migration to update, not script re-run |
| `web/blueprints/upsc_dashboard_bp.py:102` | `gap_states` (upsc.db) | Per-user first visit | CORRECT — per-user init rows should OR IGNORE |

**Fix:** PLAN-014 Phase 1 — migrate all content rows to `INSERT OR REPLACE` via m015, m016.

---

## Problem Class 2 — RBI Has 4 Copies of the Same Data

RBI key facts exist in 4 disconnected places simultaneously:

```
_RBI_KEY_DATA_SEED in app.py (Python list, 40 rows)
    ↓ INSERT OR IGNORE (one-way)
rbi_key_data table in rbi.db
    ↓ SELECT
rbi_dashboard_bp.py renders dashboard widget

KEY_SECTIONS in rbi_prep_bp.py (Python literal, 75 lines) ← COMPLETELY SEPARATE
    ↓ hardcoded
prep page template renders key facts tab

rbi_questions table in rbi.db (303 rows, MCQs)
    ↓ SELECT
rbi_prep_bp.py phase1_drill + tier2_quiz tabs

BUCKETS in rbi_prep_bp.py (Python dict, ~200 lines) ← SAME QUESTIONS AS DB, different IDs
    ↓ hardcoded
prep page template renders bucket MCQ drills
```

**Confirmed same questions:** DB `t2_ri_001` = "Which rate serves as the floor of the LAF corridor?" and BUCKETS `ri_1` = same question. Different ID system, same content.

**Fix:** PLAN-014 Phase 2 — replace KEY_SECTIONS and BUCKETS with DB queries.

---

## Problem Class 3 — Paper Labels Defined in 5+ Files with Inconsistent Strings

IES paper `ge_01` appears as:

| File | Label used |
|---|---|
| `web/blueprints/ies_answers_bp.py:39` | `"GE Paper I"` |
| `web/blueprints/ies_brief_bp.py:13` | `"GE-01 Micro/Macro"` |
| `web/blueprints/ies_quiz_bp.py:27` | `"GE-01"` |
| `web/blueprints/ies_return_quiz_bp.py:18` | `"GE-01 · Micro & Macro"` |
| `web/blueprints/dashboard_bp.py:21` | `"GE-01 · Micro & Macro"` |

Already diverged — users see 3 different labels for the same paper across pages.

UPSC paper labels diverged across 2 files:
- `upsc_bp.py:17`: `"Paper I — Theory"` (em dash)
- `upsc_dashboard_bp.py:18`: `"Paper I · Theory"` (middle dot)

Also: `db.py:116` hardcodes `["ge_01", "ge_02", "ge_03", "ge_04"]` directly in `init_user()` — a new paper would never get a `user_paper_preferences` row for new users.

**Fix:** PLAN-014 Phase 3 — `papers` lookup table seeded via migration.

---

## Problem Class 4 — Exam Dates in 3 Files, Not in DB

| File | Variable | Value | Used for |
|---|---|---|---|
| `web/db.py:27` | `EXAM_DATE = "2026-06-19"` | IES date | `is_crunch_mode()`, `_days_left()` |
| `web/blueprints/progress_bp.py:41` | `_EXAM_DATES` list | All 3 exams | Countdown tile |
| `web/blueprints/upsc_dashboard_bp.py:14` | `UPSC_DATE = "2026-08-22"` | UPSC | UPSC countdown |
| `web/blueprints/setup_bp.py:15` | `EXAM_LABELS` | All 3 exams | Setup page labels |

`exam_configurations` table already exists in ies.db and upsc.db with `exam_date` column — it is just never read for these purposes. The Python constants are redundant dead data.

**Live bug found:** `upsc.db` `exam_configurations.exam_date = '2026-09-15'` while Python had `"2026-08-22"`. Countdown used Python constant (correct). DB was wrong. Fixed S33: DB updated to `'2026-08-22'`.

**Fix:** PLAN-014 Phase 3 — read exam dates from `exam_configurations` with COALESCE fallback.

---

## Problem Class 5 — Gap State Metadata in 8 Python Locations Across 2 Files

Adding a new gap state requires updating all of these manually with no compile-time check:

**`web/blueprints/dashboard_bp.py`:**
- `_STATE_DISPLAY` (line ~27) — display labels
- `_STATE_META` (line ~30) — descriptions
- `_STATE_COLORS` (line ~40) — CSS colours
- `_STATE_EMOJI` (line ~47) — emoji per state
- `_NEXT_STATE` (line ~55) — transition map
- `_FOCUS_LABEL` (line ~62) — action button labels
- `valid_states` set in `set_state()` (line 255) — must match DB CHECK constraint

**`web/blueprints/ies_return_quiz_bp.py`:**
- `_STATE_ORDER` (line 25)
- `_STATE_ICON` (line 27)

DB `CHECK (state IN ('UNVISITED','FLAGGED','IN_STUDY','PARTIAL','VERIFIED','DECAYING'))` is the only enforcement. Python dicts have no automated check against DB constraint.

**Risk:** Add a new state to DB schema → page partially broken with no error. Would require 8+ manual Python updates across 2 files.

**Fix:** PLAN-014 Phase 3 (long-term) — consider a `gap_state_config` table, or at minimum consolidate all 8 dicts into a single `STATE_CONFIG` dict in one file.

---

## Problem Class 6 — English Content in ies.db, Not Portable

All English content lives in `ies.db` under `exam_id = 'english_practice'`:
- `english_questions` (22 rows)
- `english_question_types` (5 rows)
- `english_attempts` (user data)
- `english_keywords` (exists in schema, data unused since S23 keyword scoring removal)

`english_bp.py` uses `g.conn` — the IES connection. English writing practice is exam-agnostic but is tightly coupled to the IES DB connection.

**Consequence:** Any RBI-specific or UPSC-specific English content would need to go into the same ies.db, creating an architectural smell. New user with no IES enrollment still shares the IES connection for English.

**Decision (S33):** Move English to dedicated `english.db`. See PLAN-014 Phase 6.

---

## Problem Class 7 — Missing Migrations m009–m011

Migration files `m009_*.py`, `m010_*.py`, `m011_*.py` are referenced in knowledge but do not exist as files in `migrations/` directory.

**Evidence:** PLAN-013 Phase 1 mentions "m011 — rbi user_id DEFAULT 'rahul' fix". `data/upsc_answers_batch.txt` and `data/upsc_rubrics_batch.txt` suggest UPSC content was loaded via Anthropic Batch API but no migration file captures this for Railway reproducibility.

**Risk:** Fresh Railway deploy or new developer cannot reproduce the exact DB state from migrations alone. The gap is bridged by seed DBs, but the migration trail has holes.

**Note:** Existing migrations in directory skip from m008 to m012 (nyaya schema), then m013/m014 (indexes). Three slots unaccounted for.

**Fix:** PLAN-014 Phase 7 — audit and backfill.

---

## Problem Class 8 — profile_bp.py Reads users from Wrong DB (PLAN-013 Phase 3 Debt)

Since S25, `users` and `sessions` are canonical in `nyaya.db`. `profile_bp.py:55–59` still queries `users` from `g.conn` (ies.db).

**Risk:** Any user registered after the nyaya.db migration (post-S25) has no row in ies.db `users` table. Profile page returns null `user` row → likely template crash or blank profile.

**This is an active bug affecting real users.**

**Fix:** PLAN-014 Phase 4 — change `conn` to `nyaya_conn` in `profile_bp.py`. Safest fix, start here in S34.

---

## DB Schema State at Audit Time

### ies.db tables (26 tables)
`_migrations`, `context_packages`, `descriptive_attempts`, `dimensions`, `english_attempts`, `english_keywords`, `english_question_types`, `english_questions`, `exam_configurations`, `gap_state_events`, `gap_states`, `model_answers`, `pyq_questions`, `question_rubrics`, `rbi_attempts_new`, `return_quiz_attempts`, `return_quiz_questions`, `sessions`, `topic_attempt_summary`, `topic_base_scores`, `topics`, `user_events`, `user_feedback`, `user_mastery`, `user_paper_preferences`, `users`

Row counts: `pyq_questions` 1219, `topics` 156, `model_answers` 1219, `english_questions` 22, `return_quiz_questions` 150

### rbi.db tables (7 tables)
`_migrations`, `rbi_attempts`, `rbi_key_data`, `rbi_questions`, `rbi_sessions`, `rbi_topic_mastery`, `rbi_topic_weights`

Row counts: `rbi_questions` 303, `rbi_topic_weights` 29, `rbi_key_data` ~40

### upsc.db tables (21 tables)
`_migrations`, `context_packages`, `descriptive_attempts`, `dimensions`, `document_chunks`, `economic_data_points`, `exam_configurations`, `gap_state_events`, `gap_states`, `model_answers`, `pyq_questions`, `question_rubrics`, `reference_answers`, `return_quiz_attempts`, `return_quiz_questions`, `source_documents`, `topic_attempt_summary`, `topic_base_scores`, `topics`, `user_mastery`, `user_paper_preferences`, `users`

Row counts: `pyq_questions` 908, `topics` 81 (16 topics + 64 subtopics), `model_answers` 908, `return_quiz_questions` 0 (unused), `topic_base_scores` — unpopulated (all default 0.5)

### nyaya.db tables (6 tables)
`_migrations`, `product_enrollments`, `sessions`, `sqlite_sequence`, `user_events`, `user_feedback`, `users`

---

## Additional Findings

**UPSC priority scores inert:** `topic_base_scores` for UPSC all default to 0.5 — the priority-ordering dashboard sort is functionally dead for UPSC. IES has a `compute_base_scores.py` script; no UPSC equivalent exists. Fix: Phase 8.

**Duplicate `g.upsc_conn` open/close:** Both `upsc_bp.py` and `upsc_dashboard_bp.py` independently open and close `g.upsc_conn` in their own `before_request`/`teardown_request` hooks. Safe now but fragile. Fix: Phase 5 (shared DB helper).

**`_PAGE_EXAM` fragility in `progress_bp.py:14`:** Maps page name strings to exam labels for time-tracking. If any blueprint calls `track_page_time(conn, "New Page Name")` with a name not in this dict, time is silently dropped. No error. Adding a new page requires updating both the call site and `_PAGE_EXAM`.

**ies.db has a `users` table:** Pre-nyaya migration residue. After full PLAN-013 Phase 3 rollout, ies.db `users` should be read-only legacy data, with all active reads pointing to nyaya.db.

---

## Fixes Applied This Session (S33)

| Fix | What | Commit |
|---|---|---|
| GDP rank nominal | `ine_01` updated: "4th globally" → "6th globally (IMF 2025)" | 3d5ca61 |
| GDP rank PPP | `ine_01b` added: "3rd globally (IMF 2025)" | 3d5ca61 |
| MCQ ie_1 answer | Corrected from "B) 4th largest" to "D) 6th largest" | 3d5ca61 |
| UPSC seed DB date | `seeds/upsc_seed.db` exam_date: '2026-09-15' → '2026-08-22' | 3d5ca61 |
| Production rbi_key_data | Railway SSH UPDATE on live `data/rbi.db` (INSERT OR IGNORE blocked auto-fix) | 7010521 (script) |
| UPSC live DB date | `data/upsc.db` exam_date updated to '2026-08-22' | local only (gitignored) |

---

## Open Items → PLAN-014

All 8 problem classes are addressed in PLAN-014 phases 1–9.
Deploy order: Phase 4 → 1 → 3 → 2 → 6 → 5 → 7 → 8 → 9
Start S34 with Phase 4 (profile_bp.py nyaya fix) — zero regression risk.
