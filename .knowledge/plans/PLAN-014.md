# PLAN-014 — Single-Source Architecture Refactor

**Date:** 2026-06-07 (Session 33)
**Status:** PLANNED — implementation starts S34
**Scope:** All 4 exam domains (IES, RBI, UPSC, English)

---

## Problem Summary

The app has multiple disconnected copies of the same data. When one copy is updated, others silently stay stale. This caused the GDP rank bug (4th instead of 6th), the UPSC exam date being 24 days wrong, and will cause more silent data errors as exam facts change in the lead-up to exams.

Root causes:
1. `INSERT OR IGNORE` used for content rows — existing rows are never updated even when the Python source changes
2. `KEY_SECTIONS` + `BUCKETS` in `rbi_prep_bp.py` are pure Python literals disconnected from the DB
3. Paper labels, exam dates, and gap state metadata hardcoded in multiple files with no canonical form
4. No shared DB helper contract — `db.py` is secretly `ies_db.py`; profile page reads users from wrong DB

---

## Target Architecture

- DB is the single source of truth for all content
- Python defines structure and behaviour, never content
- All content updates go through numbered migrations using INSERT OR REPLACE
- New exam papers: run 3 scripts → deploy → all pages update automatically

---

## Implementation Phases

### Phase 0 — Fix live bugs ✅ DONE (S33)
- [x] UPSC exam date: `data/upsc.db` + `seeds/upsc_seed.db` updated to 2026-08-22
- [x] GDP rank: production `rbi_key_data` updated via Railway SSH; code deployed via commit 3d5ca61

---

### Phase 4 — Profile page reads from wrong DB ← START HERE (S34)
**Risk: None — fixes active bug for post-S25 users**

- [ ] `web/blueprints/profile_bp.py` lines 55–59: replace `conn.execute("SELECT ... FROM users")` with `nyaya_conn.execute(...)`
- [ ] Use `g.nyaya_conn` (available in all requests via app.py before_request)
- [ ] Test: profile page loads for a user whose record exists only in nyaya.db

---

### Phase 1 — Kill INSERT OR IGNORE drift
**Risk: Low — deploy m015 FIRST, verify live, then remove boot-time seed**

- [ ] Write `migrations/m015_update_rbi_key_data.py` (DB="rbi"):
  - Use `INSERT OR REPLACE` for all rows from `_RBI_KEY_DATA_SEED`
  - Verify it runs on Railway before next step
- [ ] Remove `_run_rbi_migrations()` boot-time seeding from `web/app.py` (after m015 confirmed)
- [ ] Write `migrations/m016_seed_english_types.py` (DB="ies"):
  - `INSERT OR REPLACE` from `QUESTION_TYPES_SEED` in english_bp.py
  - Remove `_ensure_types_seeded()` from `english_bp.py` after m016 confirmed
- [ ] `db.py:submit_return_quiz()` — remove 0.80/0.50 hardcoded fallbacks; raise if exam_configurations read fails

---

### Phase 2 — Eliminate KEY_SECTIONS and BUCKETS from rbi_prep_bp.py
**Risk: Medium — verify DB has all data before removing Python fallback**

Pre-check (do before any code change):
- [ ] Count `KEY_SECTIONS` rows in Python vs `rbi_key_data` DB — must match
- [ ] Count `BUCKETS` questions vs `rbi_questions` DB questions by topic — find any gaps
- [ ] Add missing DB rows via migration if gaps found

Implementation:
- [ ] Replace `KEY_SECTIONS` (75-line literal) with `SELECT * FROM rbi_key_data ORDER BY section_sort, sort_order`; group sections in Python after query
- [ ] Replace `BUCKETS` dict with `SELECT * FROM rbi_questions ORDER BY topic, created_at` grouped by topic/subject
- [ ] Update prep page template to render from query results
- [ ] Delete both Python literals from `rbi_prep_bp.py`

---

### Phase 3 — Centralise exam metadata
**Risk: Low — add COALESCE fallback to all DB date reads**

- [ ] Read exam dates from `exam_configurations.exam_date` in all blueprints:
  - `db.py`: remove `EXAM_DATE = "2026-06-19"` constant; read from DB with hardcoded fallback as COALESCE default
  - `progress_bp.py`: remove `_EXAM_DATES` list; read from all 3 exam DBs
  - `upsc_dashboard_bp.py`: remove `UPSC_DATE` constant; read from DB
- [ ] Add `rbi_exam_configurations` row to `rbi.db` (RBI currently has no exam_configurations table)
- [ ] Create `papers` lookup table seeded via migration; delete 5-file IES paper label duplication and 2-file UPSC duplication

---

### Phase 5 — Shared DB helper layer
**Risk: Medium — full refactor, needs smoke-test in branch before merge**

- [ ] Add explicit comment/prefix to `web/db.py` marking it as IES-specific
- [ ] Create `web/rbi_db.py` — extract inline sqlite3 calls from rbi blueprints into named helpers
- [ ] Create `web/upsc_db.py` — consolidate duplicate `g.upsc_conn` open/close from both UPSC blueprints
- [ ] Test: all routes still respond 200 after refactor

---

### Phase 6 — English to its own DB
**Risk: Medium — new Railway volume file; keep fallback until confirmed live**

- [ ] Create `migrations/m017_create_english_db.py` (DB="english"):
  - Creates `english_questions`, `english_question_types`, `english_attempts` tables
  - Copies data from ies.db via cross-DB read (open both connections in migration)
- [ ] Update `web/app.py`: open/close `g.english_conn` in before_request/teardown
- [ ] Update `english_bp.py` to use `g.english_conn` instead of `g.conn`
- [ ] Verify Railway volume includes `data/english.db` path before deploying
- [ ] Keep `ies.db` english tables in place until Railway confirms `english.db` is live

---

### Phase 7 — Migration gap audit
**Risk: None — additive only**

- [ ] Verify what m009, m010, m011 represent (git log check)
- [ ] Create retrospective migration files for any gaps so Railway deploys are reproducible
- [ ] Add deploy check: warn if `_migrations` row count < number of m*.py files

---

### Phase 8 — UPSC priority scores
**Risk: None — additive, fills empty table**

- [ ] Port `scripts/compute_base_scores.py` to accept `--exam upsc_eco_opt` argument
- [ ] Run against UPSC topics to populate `topic_base_scores`
- [ ] Verify dashboard sorts by score instead of arbitrary order

---

### Phase 9 — Generic ingestion pipeline
**Risk: None — new scripts only, no existing code changes**

- [ ] `scripts/ingest_pyq.py --exam <id> --year <year> --pdf <path>` — exam-agnostic
- [ ] `scripts/generate_rubrics.py --new-only` — only questions with no rubric row
- [ ] `scripts/generate_answers.py --new-only` — only questions with no model answer row
- [ ] Write one-page runbook: "New exam paper → 3 commands → deploy"

---

## Deployment Safety Rules (non-negotiable)

1. **Never remove a Python fallback before the DB replacement is confirmed live on Railway.**
2. **Phase 2 gate**: row count check Python vs DB before any code change. If counts differ, add missing DB rows first.
3. **Phase 1 gate**: deploy m015, verify via Railway logs, then remove `_run_rbi_migrations()` in a separate commit.
4. **Phase 6 gate**: verify `data/english.db` exists on Railway volume before removing ies.db fallback.
5. **Each phase is independent** — do not bundle multiple phases in one deploy.

---

## Audit Findings Reference

Full findings from S33 4-agent audit documented in:
- [AUDIT-004](../audits/AUDIT-004.md) — architecture audit findings (8 problem classes, all file:line locations)
- This plan synthesises those findings into actionable phases
