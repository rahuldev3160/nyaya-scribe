# AUDIT-002 — Performance & Multi-User Lag Root Cause Analysis

**Date:** 2026-06-06 (Session 27)
**Scope:** Dashboard load lag, inter-page navigation lag, multi-user correctness
**Method:** Query plan analysis, file-by-file code audit, real benchmark timing

---

## Root Causes Found (9 total)

| ID | Severity | Description | Fix |
|----|----------|-------------|-----|
| RC-1 | CRITICAL | `get_topics()` called 5× per IES dashboard load (4 redundant) — measured 31.8ms | Group by paper in Python after 1 fetch |
| RC-2 | CRITICAL | Auto-covering indexes built on-the-fly for `pyq_questions` + `model_answers` per query | migrations/m013 + m014 added 5 explicit indexes to ies.db + upsc.db |
| RC-3 | HIGH | N+1 in `ies_answers_bp.answers()` — `get_answer()` called per-question in loop | Batch fetch via `IN` clause |
| RC-4 | HIGH | `init_user()` runs 94 INSERT OR IGNORE + commit on every `/dashboard` and `/ies/return-quiz` load | Existence-gate: 1 SELECT, return if user exists |
| RC-5 | HIGH | `SECRET_KEY = secrets.token_hex(32)` fallback → different key per worker → redirect storm | File-backed persistent key (`.secret_key`) |
| RC-6 | MEDIUM | `g.conn` (ies.db) opened on every request even for UPSC/RBI routes | Deferred; `track_page_time` already writes to nyaya.db internally |
| RC-7 | MEDIUM | `track_page_time()` INSERT+COMMIT blocks response; write queue under concurrency | Daemon thread fires async write |
| RC-8 | LOW | `_run_content_migrations()` called per gunicorn worker on startup | Not fixed — idempotent, harmless |
| RC-9 | MEDIUM | `_init_user()` in upsc_dashboard loops 16 SELECTs per visit for existing users | Same existence-gate as RC-4 |

---

## Files Changed

- `web/blueprints/dashboard_bp.py` — RC-1: `topics_by_paper` dict replaces 4× `get_topics()` calls
- `web/blueprints/upsc_dashboard_bp.py` — RC-1: same pattern; RC-9: `_init_user()` existence gate
- `web/blueprints/ies_answers_bp.py` — RC-3: batch `IN` query → `answers_map` dict
- `web/db.py` — RC-4: `init_user()` gate; RC-7: `track_page_time()` daemon thread; added `import threading`
- `web/app.py` — RC-5: file-backed `.secret_key` fallback
- `migrations/m013_perf_indexes_ies.py` — RC-2: 5 indexes on ies.db
- `migrations/m014_perf_indexes_upsc.py` — RC-2: 5 indexes on upsc.db

---

## Benchmark Data (local SSD)

- `init_user()` existing user: 0.3ms → ~0.05ms (1 SELECT)
- `get_topics()` × 5 (IES dashboard): 31.8ms → ~6.4ms (1 call)
- `get_topics()` × 3 (UPSC dashboard): ~19ms → ~6ms (1 call)
- `ies_answers_bp` answers load: N selects → 1 batched select
- Railway disk (estimated): multiply local times by 3–5×

---

## Multi-User Failure Mode Fixed

RC-5 (SECRET_KEY) was the most dangerous: multiple gunicorn workers each got a different random key → ~50% of session validation failures → redirect loops appearing as lag. File-backed key fixes this for local dev; `FLASK_SECRET_KEY` env var required for production.

---

## Indexes Added (both ies.db and upsc.db)

```
idx_pyq_exam_topic   ON pyq_questions(exam_id, topic_id)
idx_ma_exam_qid      ON model_answers(exam_id, question_id)
idx_topics_exam_level ON topics(exam_id, topic_level)
idx_gs_user_exam     ON gap_states(user_id, exam_id)
idx_um_user_exam     ON user_mastery(user_id, exam_id)
```

Eliminates: AUTOMATIC COVERING INDEX build-on-the-fly, TEMP B-TREE for COUNT(DISTINCT), TEMP B-TREE for ORDER BY.
