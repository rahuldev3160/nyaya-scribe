# HANDOFF — Descriptive Exams

Last updated: 2026-06-07 (Session 31)

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

---

## Session 29+30 — Feedback Triage, Permanent Fixes, Skeleton Loading, BUG-025

### What was done

**Feedback sync fix (META)**
- `migrations/m015_move_feedback_to_nyaya.py`: moves `user_feedback` table from ies.db to nyaya.db (canonical identity+events store). Copies existing rows via ATTACH DATABASE with locked-DB guard.
- `scripts/pull_feedback.py`: SSH into Railway, query nyaya.db (post-m015) and ies.db (pre-migration), merge by `feedback_id`, save to `data/feedback_snapshot.json`.
- `feedback_bp.py`: all read/write now uses `get_nyaya_conn()` only; direct JOIN on `users` (same DB, no cross-DB merge needed).

**F1 — Sidebar toggle**
- `base.html`: sidebar gets `id="sidebar"`, toggle button `‹/›` in sidebar-title flex row. Nav link text wrapped in `<span class="nav-text">`.
- JS: `toggleSidebar()` toggles `body.sidebar-collapsed`, persists in `localStorage['sc']`. DOMContentLoaded restores state.
- `style.css`: `.sidebar-collapsed .sidebar { width: 52px }`, `.nav-text { display:none }`, `main-content margin-left` collapses.
- "Setup" renamed to "My Plan" in nav.

**F3 — Button labels fixed**
- Dashboard "✏️ IES Descriptive Quiz" and "📋 IES MCQ Quiz" (was ambiguous "Practice" labels).

**F5 — Study plan banner removed**
- `dashboard.html`: study_path banner removed entirely. Plan visible only via My Plan nav link.

**F4/F8 — Progress architecture (macro vs micro)**
- `progress_bp.py` + `progress.html`: rewritten as macro view — Exam Countdown (days left per exam), Today/Last 7 Days time-by-exam bars. No attempt history.
- `dashboard.html` + `dashboard_bp.py`: IES micro-progress section at bottom — descriptive_attempts count, MCQ count, recent 5 attempts table (date, topic, words, self-rating badge).

**F7 — Descriptive quiz: write → compare → rate**
- `migrations/m016_descriptive_self_rating.py`: adds `self_rating TEXT` to `descriptive_attempts` in ies.db.
- `ies_quiz_bp.py`: POST `/ies/quiz/submit` saves attempt, redirects with `attempt_id`. POST `/ies/quiz/rate` writes `self_rating`. GET `/ies/quiz?attempt_id=N` loads attempt.
- `ies_quiz.html`: enabled textareas; `{% if attempt %}` branch shows 2-column side-by-side (YOUR ANSWER | MODEL ANSWER), each with INTRO / BODY / CONCLUSION sub-sections. Self-rating buttons (✅ Got it / 🟡 Partially / ❌ Missed it). Navigation: Try again / Next Question.

**F9 — Per-topic MCQ Quiz links**
- `dashboard.html` topic grid: added 6th column with `📝 Quiz` link → `/ies/return-quiz?paper=X&topic=Y` for each topic row.

**F2 — Skeleton loading CSS (UX polish)**
- `style.css`: `@keyframes skel-shimmer`, `.skel`, `.skel-line`, `.skel-badge`, `.skel-bar`, `.skel-btn` classes. `.dashboard-skeleton` hidden by default; `.dashboard-content` transitions opacity.
- `base.html`: `<body class="page-loading">`. DOMContentLoaded removes `page-loading` — real content fades in at 0.25s.
- `dashboard.html`: `.dashboard-skeleton` block with 3 shimmer focus cards + 6 shimmer topic rows appears instantly during load. Real content wrapped in `.dashboard-content`.

**BUG-025 — Model answer panel empty**
- Root cause: `get_questions()` selects `ma.answer_id` only — not `intro_text/body_text/conclusion_text`. Too expensive to load full text for all 1219 questions per page view.
- Fix: in quiz GET handler, after `selected_q` resolved, call `get_answer(conn, qid)` for that single question and merge the 3 text fields. One indexed PK lookup.

### Commits (S29/S30)
| Commit | Description |
|--------|-------------|
| 7114b36 | feat(s28): feedback sync, quiz submit, macro progress, sidebar toggle |
| 8aa00f5 | feat(ux): skeleton loading for dashboard (F2) |
| 49d0d0e | fix(quiz): fetch model answer text for selected question (BUG-025) |

### Key decisions
- **DECIDE-S29-01**: `user_feedback` belongs in nyaya.db (canonical identity+events store), not ies.db. Pattern: all product-level user state in nyaya.db.
- **DECIDE-S29-02**: Macro progress page = cross-exam time + countdowns only. Exam-specific attempt data stays on each dashboard (IES micro section at bottom).
- **DECIDE-S29-03**: `get_questions()` must NOT include model answer text fields — too expensive at 1219 rows × ~3KB. Always fetch via `get_answer()` for the single selected question.
- **DECIDE-S29-04**: Sidebar collapse at 52px — only icons visible. `.nav-text` spans enable clean toggle without two separate nav lists.

### Watch For (S31)
- Verify Railway deploy applied m015 (feedback→nyaya.db) and m016 (self_rating column) — run `python3 scripts/pull_feedback.py` after deploy confirms.
- `track_page_time(exam_id=EXAM_ID)` only updated in dashboard_bp and ies_quiz_bp. Other blueprints (rbi_dashboard_bp, upsc_dashboard_bp, english_bp) still don't pass `exam_id` — macro progress time-by-exam will under-attribute RBI/UPSC/English study time until fixed.
- If users report the "My Progress" page shows 0 for RBI/UPSC/English, that's the cause.

### Watch For (S28)
- Railway deploy for `96f308e` — verify Economic Growth & Development "Study" button now lands on correct page with questions
- If any user reports 0 questions on any other topic, check if paper param is missing in the URL — same class of bug, same fix pattern
- RC-8 (migrations per worker on startup) is still deferred — low priority, harmless

---

---

## Session 31 — UX navigation pass: bucket model answers, back links, IES banner cleanup

### What was done

1. **English dashboard — Model Answers tab redesigned as bucket UI** (`english_dashboard.html`)
   - Default view: grid of type tiles (Essay, Précis, RC, Letter, Report) — click to open
   - Inside a bucket: type-specific model answers + `← Back` button at top and bottom
   - JS show/hide (`openMaBucket` / `closeMaBucket`) — no route change, no page reload
   - Matches the RBI prep tier2-quiz bucket pattern the user cited as reference

2. **IES dashboard — removed redundant cross-exam banner** (`dashboard.html`)
   - Deleted the `{% if other_exams %}` block that rendered `→ RBI DEPR Dashboard` / `→ UPSC Dashboard` buttons at the top of the IES dashboard
   - Sidebar already has those links; the banner was duplicate navigation
   - No data impact — route still computes `other_exams` (unused, harmless)

3. **Back link audit — all exam tool pages** (6 templates)
   - Added `← Dashboard` back links to every exam-specific tool page that had none:

   | Template | Link added |
   |---|---|
   | `rbi_prep.html` | `← RBI Dashboard` → `/rbi` |
   | `ies_answers.html` | `← IES Dashboard` → `/dashboard` |
   | `ies_quiz.html` | `← IES Dashboard` → `/dashboard` |
   | `ies_brief.html` | `← IES Dashboard` → `/dashboard` |
   | `ies_return_quiz.html` | `← IES Dashboard` → `/dashboard` |
   | `upsc_mains.html` | `← UPSC Dashboard` → `/upsc` |

   Account pages (Profile, Progress, Feedback, Setup) deliberately excluded — they're accessed from any context and don't need a specific dashboard back link.

### Commit and deploy
- Commit `52145be` — pushed to `origin/main` → Railway auto-deploy triggered
- All 8 modified templates validated with Jinja2 compiler before push (0 errors)

### Key decisions
- **DECIDE-S31-01**: Bucket navigation for model answers is pure front-end (JS show/hide). No Flask route change needed — all data already loaded in `model_questions` dict by the existing `english_dashboard` route.
- **DECIDE-S31-02**: Back links use consistent styling (`font-size:0.82rem; color:#9AA0A6; text-decoration:none`) matching the existing `← English Dashboard` link in `english.html`.

---

---

## Session 32 — Auth + Event Recording Audit + Onboarding Hard Gate Removal

### What was done

**AUDIT-003 — Full journey trace: sign-in → DB recording**
- Confirmed production is healthy: 36 users, 945 events on Railway persistent volume
- Local `data/nyaya.db` is a dev-only artifact — production DB is `/app/data/nyaya.db` on Railway
- Traced full journey: GET / → POST /auth/login → Google → GET /auth/callback → GET /dashboard
- Found 4 bugs (BUG-A through BUG-D), fixed 3 immediately

**Bug fixes in commit `203f8cf`:**

1. **BUG-A fixed — event type normalisation** (`web/app.py`)
   - 269 `page_visit` + 50 `page_time` events sitting alongside 449 `page_view` — analytics split across 3 labels
   - Added `normalize_event_types` migration in `_run_nyaya_migrations()`: one-time `UPDATE user_events SET event_type='page_view' WHERE event_type IN ('page_visit','page_time')`
   - Guarded by `_migrations` table — idempotent

2. **BUG-B fixed — dashboard visit logged before any branching** (`web/blueprints/dashboard_bp.py`)
   - `track_page_time()` was called AFTER the onboarding redirect — new users' first dashboard visit was invisible
   - Moved to immediately after `init_user()`, before any conditional logic

3. **BUG-C fixed — log_event() silent failure** (`web/db.py`, `web/blueprints/auth_bp.py`, 5 other blueprints)
   - `log_event()` took a dead `conn` param it never used — all callers passed wrong thing silently
   - `get_user_id()` fell back to `os.environ.get("IES_USER_ID", "rahul")` → FK violation swallowed by bare except
   - Fix: removed dead `conn` param; added early return when uid is falsy or matches env-var fallback
   - `upsert_user()` now returns `tuple[str, bool]` — `(user_id, is_new)`. Fires `signed_up` event on first OAuth login.
   - `g.user_id = user_id` set in `auth_bp.py` before `log_event()` call so uid is real, not fallback

4. **BUG-D deferred — daemon thread writes** (LOW priority)
   - `track_page_time()` uses `daemon=True` thread; writes can be lost on gunicorn worker recycle
   - Not fixed — decision from S27 (DECIDE-S27-01): fire-and-forget analytics loss is acceptable
   - Fix if analytics completeness becomes a requirement: drop `daemon=True` or write synchronously

**Hard gate removal + setup banner** (`web/blueprints/dashboard_bp.py`, `web/templates/dashboard.html`)
- Removed hard redirect to `/setup` for users with `onboarding_completed=0`
- Added dismissable yellow banner: `onboarding_incomplete = True` when `onboarding_completed=0` OR `exam_focus IS NULL`
- Banner dismiss: `sessionStorage.setItem('setup_dismissed','1')` — no DB write, no server round-trip
- 4 stuck production users (onboarding_completed=0, permanently looped on /setup) unblocked via direct Railway SSH SQLite UPDATE before deploy

**4 stuck users unblocked (pre-code fix):**
```sql
UPDATE users SET onboarding_completed=1 WHERE onboarding_completed=0;
```
Run via `railway ssh python3 -c "import sqlite3; ..."` — they can now reach the dashboard with the setup banner guiding them to complete their profile.

### Key decisions
- **DECIDE-S32-01**: Hard onboarding gate removed permanently. Dashboard always shows with defaults; setup is nudged via dismissable banner, not enforced via redirect.
- **DECIDE-S32-02**: `log_event()` must never take a `conn` param — it owns its own nyaya connection via `get_nyaya_conn()`. Any call site that passes conn as first arg is a bug.
- **DECIDE-S32-03**: `upsert_user()` contract: returns `(user_id: str, is_new: bool)`. Callers must unpack both values. The `signed_up` event is the only first-login marker — it fires once per user, at OAuth callback.
- **DECIDE-S32-04**: `onboarding_incomplete` flag = `not onb or not onb["onboarding_completed"] or not onb["exam_focus"]`. Both conditions required — a user with `onboarding_completed=1` but NULL `exam_focus` is still incomplete.

### Commit and deploy
- Commit `203f8cf` — pushed to `origin/main` → Railway auto-deploy triggered
- 13 files changed, 139 insertions, 57 deletions
- Verification: app boots clean; dashboard 200 with correct banner state for both complete and incomplete users

---

## Exact Next Step

Resume here in S33:
- **Phase 2 recording improvements (not urgent):**
  1. Add `quiz_attempted` event after MCQ quiz submission
  2. Add `answer_submitted` event after descriptive answer grading  
  3. Add `user_streaks` table (one row per user per day of study activity)
- **Open items from PLAN-011 (P2/P3):**
  1. Progress tab: "Avg Auto Score / Avg Self Score" columns always show 0 after scoring removal — replace with attempt count + word count stats
  2. Précis word count inconsistency: Insights tab says 150–170w; seed `word_count_target` = 140 — align to one standard
  3. RC marks mismatch: Insights says 5m each; seeds have 10m per question — audit and fix
  4. Custom domain: `nyayascribe.com` → Railway custom domain + OAuth redirect update (pending domain registration)

---

## Watch For

- Seed DB sync: any future `m0XX` that uses `UPDATE` must also be applied to `seeds/ies_seed.db` explicitly (the migration runner only tracks `data/*.db`)
- `_run_content_migrations()` adds ~100ms to app cold start — acceptable for now; if startup time becomes an issue, add a filesystem-level lock check
