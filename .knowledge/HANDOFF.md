# HANDOFF — Descriptive Exams

Last updated: 2026-06-06 (Session 24)

---

## Session 24 — Essay Quality Overhaul

### What was done

1. **Root-cause diagnosis — essay quality bug**
   - `seeds/ies_seed.db` had old narrow, analytically-framed essay questions (e.g. "Analyse the causes of India's current account deficit") from the original seeding
   - `m008` (S23) only updated `data/ies.db` via `UPDATE` — it never touched the seed DB
   - Fresh local installs (seed copy → app start without running `scripts/migrate.py`) would get the old narrow questions
   - `_run_migrations()` in `app.py` only handles DDL (add column, create tables) — the `m*.py` content migrations were Railway-only

2. **Fix 1 — seed DB backfill**
   - Applied m008 and m009 directly to `seeds/ies_seed.db` so fresh installs start with the correct questions

3. **Fix 2 — auto-migration on app start**
   - Added `_run_content_migrations()` to `web/app.py::create_app()` — calls `scripts/migrate.py::main()` on every startup
   - Idempotent (tracks applied migrations in `_migrations` table) — safe to run on Railway too

4. **m009 — Open-ended UPSC-style essay replacement**
   - Replaced all 5 old proposition-based ("do you agree?") essays with open-canvas UPSC themes:
     1. The cost of inequality is borne by the whole society, not just the poor
     2. Agriculture is India's past — but it need not remain India's problem
     3. A democracy that fails its poor has failed its purpose
     4. India's cities are broken by design — but they can be repaired by will
     5. The climate crisis and the development crisis are one and the same crisis
   - Applied to `data/ies.db` and `seeds/ies_seed.db`

5. **m010 — 3 economics/banking essays added**
   - eng_essay_006: The invisible hand of the market needs the visible hand of regulation
   - eng_essay_007: A bank is not merely a custodian of money — it is a custodian of public trust
   - eng_essay_008: Financial inclusion is the unfinished agenda of Indian independence
   - All with ~500-word model answers (intro / body / conclusion)
   - Applied to `data/ies.db` and `seeds/ies_seed.db`

### Key decisions

- **DECIDE-S24-01**: Essay prompts must be open-canvas (no built-in thesis/binary choice) matching UPSC Essay Paper style. Proposition-test format ("do you agree") is not acceptable.
- **DECIDE-S24-02**: Every content migration must be applied to BOTH `data/ies.db` AND `seeds/ies_seed.db`. The seed is the source of truth for Railway fresh deploys.
- **DECIDE-S24-03**: `create_app()` now auto-runs `scripts/migrate.py` so local installs never require a manual migration step.

### DB state at session end (ies.db — english_questions)

| type_id | count | model answers |
|---------|-------|---------------|
| essay   | 8     | all ✅        |
| letter  | 3     | all ✅        |
| précis  | 4     | all ✅        |
| rc      | 4     | all ✅        |
| report  | 3     | all ✅        |
| **total** | **22** | **all ✅** |

---

## Session 27 — Performance Overhaul + Multi-User Fix (AUDIT-002)

### What was done

**Deep performance audit** — identified 9 root causes of dashboard/page lag. Fixed 8 via 4 parallel agents.

1. **RC-1 — Query deduplication** (`dashboard_bp.py`, `upsc_dashboard_bp.py`)
   - IES dashboard was calling `get_topics()` 5× per load (1 global + 4 per-paper). Reduced to 1.
   - UPSC dashboard was calling `_get_topics()` 3× per load. Reduced to 1.
   - Fix: fetch once, group by `paper_id` in Python via `topics_by_paper` dict.

2. **RC-2 — DB indexes** (`migrations/m013_perf_indexes_ies.py`, `m014_perf_indexes_upsc.py`)
   - EXPLAIN QUERY PLAN showed `pyq_questions` + `model_answers` JOINs building AUTOMATIC COVERING INDEX on-the-fly per query. ORDER BY and COUNT(DISTINCT) used TEMP B-TREE.
   - Added 5 explicit indexes to both ies.db and upsc.db: `idx_pyq_exam_topic`, `idx_ma_exam_qid`, `idx_topics_exam_level`, `idx_gs_user_exam`, `idx_um_user_exam`.

3. **RC-3 — N+1 answers** (`ies_answers_bp.py`)
   - `get_answer()` called per-question in a loop. Now batched via `IN` clause into `answers_map`.

4. **RC-4 — init_user gate** (`db.py`)
   - `init_user()` ran 94 INSERT OR IGNORE + commit on every `/dashboard` and `/ies/return-quiz` load.
   - Added `SELECT 1 ... LIMIT 1` existence check — returns immediately for existing users.

5. **RC-5 — SECRET_KEY** (`app.py`, Railway env var)
   - `secrets.token_hex(32)` fallback gave every gunicorn worker a different key → redirect storm.
   - Fixed: file-backed `.secret_key` for local dev + `FLASK_SECRET_KEY` env var set on Railway.

6. **RC-7 — Async event writes** (`db.py`)
   - `track_page_time()` blocked response with synchronous nyaya.db INSERT + COMMIT.
   - Now fires in daemon thread — page response unblocked from write queue.

7. **RC-9 — UPSC _init_user gate** (`upsc_dashboard_bp.py`)
   - Same existence gate as RC-4. Drops from 16 SELECTs to 1 for returning users.

**BUG-020 — Topic→paper mismatch (0 questions on answers/quiz pages)**

Root cause: `set_state()` in dashboard and `upsc_topic_state()` in UPSC dashboard redirected with `?topic=<id>` but NO `?paper=`. Receiving pages defaulted to ge_01/upsc_p1 — 23/30 IES topics and all UPSC Paper II topics returned 0 questions. Also: ies_quiz by-topic mode showed incoherent dropdown (wrong paper's topics listed while correct topic's questions displayed).

Five files fixed:
- `dashboard_bp.py`: DB lookup of `paper_id` before redirect, appends `&paper=`
- `ies_answers_bp.py`: auto-detects paper from topic_id when not found in current paper
- `upsc_dashboard_bp.py`: same DB lookup before redirect to `/upsc/mains`
- `upsc_bp.py`: same auto-detect defence
- `ies_quiz_bp.py`: by-topic mode switches `selected_paper` to match incoming topic

### Deploy status
- Performance fixes committed: `d0d43e3` → pushed → Railway deploy
- BUG-020 fix committed: `96f308e` → pushed → Railway deploy
- `FLASK_SECRET_KEY` set on Railway production via `railway variable set --json`
- Migrations m013+m014 applied locally; auto-apply on Railway on first startup via `_run_content_migrations()`

### Key decisions
- **DECIDE-S27-01**: `track_page_time()` events are non-critical — daemon thread fire-and-forget is acceptable; a missed event on thread timeout causes no data loss beyond analytics.
- **DECIDE-S27-02**: `FLASK_SECRET_KEY` is now a required production env var. Local dev uses file-backed `.secret_key`. Any future Railway service must have this set.
- **DECIDE-S27-03**: RC-8 (`_run_content_migrations()` per worker) deferred — idempotent, harmless, low priority.

---

### Watch For (S28)
- Railway deploy for `96f308e` — verify Economic Growth & Development "Study" button now lands on correct page with questions
- If any user reports 0 questions on any other topic, check if paper param is missing in the URL — same class of bug, same fix pattern
- RC-8 (migrations per worker on startup) is still deferred — low priority, harmless

---

## Exact Next Step

Resume here in S25:
- **Open items from PLAN-011 (P2/P3):**
  1. Progress tab: "Avg Auto Score / Avg Self Score" columns always show 0 after scoring removal — replace with attempt count + word count stats
  2. Précis word count inconsistency: Insights tab says 150–170w; seed `word_count_target` = 140 — align to one standard
  3. RC marks mismatch: Insights says 5m each; seeds have 10m per question — audit and fix
  4. Custom domain: `nyayascribe.com` → Railway custom domain + OAuth redirect update (pending domain registration)

---

## Watch For

- Seed DB sync: any future `m0XX` that uses `UPDATE` must also be applied to `seeds/ies_seed.db` explicitly (the migration runner only tracks `data/*.db`)
- `_run_content_migrations()` adds ~100ms to app cold start — acceptable for now; if startup time becomes an issue, add a filesystem-level lock check
