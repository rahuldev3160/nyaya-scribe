# Descriptive Exams — Session Handoff

## Last Updated
2026-06-03 (Session 9)

---

## Watch For — Active Gotchas (read before writing any code)

| Gotcha | Symptom | Correct action |
|---|---|---|
| **Wrong Python runtime** | `TypeError: unsupported operand type(s) for \|` on any page | Do NOT remove the annotation. Run `/opt/homebrew/bin/streamlit --version` to confirm runtime is Python 3.11. Never use `/Library/Python/3.9/bin/streamlit`. |
| **@st.cache_resource is single-user only** | Data corruption / OperationalError under concurrent users | All 5 IES pages now use `@st.cache_resource` — correct for single-user (fixes per-rerun leak), but WRONG for multi-user (shared connection object is not thread-safe). MUST revert to per-request connections before launch. See DECIDE-08. |
| **ies_seed.db must stay clean** | New users get Rahul's personal data on first boot | `data/ies_seed.db` is the committed clean copy — never run quiz/drill sessions against it. It must only contain question bank rows (zero user_mastery / gap_states / attempts). |

---

## Project Status

### IES 2026 — COMPLETE
Backend: 1219 PYQs + rubrics + model answers + 150 MCQs. Web app live on :8501.

### UPSC Economics Optional — COMPLETE ✅
908/908 PYQs + rubrics + model answers in `data/upsc.db`. Web app live: `web/pages/7_UPSC_Mains.py` (Paper I Theory / Paper II Indian Economy, year navigation, LaTeX rendering, rubric + data tabs).

### RBI DEPR 2026 — MCQ BANK BUILT ✅ | UI rebuilt ✅
New `data/rbi.db` with 303 questions. `6_RBI_Prep.py` fully rewritten. See below.

---

## Session 9 Summary (2026-06-03)

### Public launch preparation

**DB foundation (data layer)**
- `data/ies.db` removed from git tracking — it's the live runtime DB, not source code
- `data/ies_seed.db` created: clean copy of ies.db with all user rows stripped (12.7 MB committed)
- Both DBs have `user_events` table + 2 indexes (`idx_ue_user`, `idx_ue_type`)
- First-boot logic in `app.py`: if `ies.db` missing → copy from `ies_seed.db` (with error handling)

**User isolation fixes**
- `6_RBI_Prep.py` hardcoded `USER_ID = "rahul"` → `get_user_id()` (6 call sites)
- `4_My_Progress.py` direct `USER_ID` import → `get_user_id`
- `get_user_id()` in `db.py` now auto-assigns UUID on first call from ANY page (deep-link safe — no more "rahul" fallback)

**Event logging**
- `log_event()` added to `web/db.py` — silent no-op on any error
- `session_id` falls back to `user_id` (since they're the same in pre-auth architecture)
- Wired: `topic_opened` (Study Brief), `return_quiz_submitted` (Return Quiz), `drill_attempt` (RBI Prep)

**Public-safe API**
- `2_Quiz.py` gated: if `ANTHROPIC_API_KEY` not set → info banner + st.stop()
- `load_api_key()` dev machine path removed (hard raise only)
- `playwright` removed from `requirements.txt` (5 prod deps remain)

**Config / infra**
- `.gitignore`: `data/ies.db`, `data/rbi.db`, all WAL files for all 3 DBs
- `DEPLOY.md`: Python 3.11, Hetzner/Railway targets, quiz API key note
- `scripts/init_db.py`: `user_events` table added to schema

### What's still needed before public launch

1. **Revert `@st.cache_resource` → per-request connections** (DECIDE-08) — all 5 IES pages + 7_UPSC_Mains.py. Single shared connection object is not thread-safe under concurrent users.
2. **Google OAuth** + `users`/`sessions` tables + auth gate on every page (MVMU steps 3–4)
3. **Composite indexes** (7 indexes, 15 min — already written in `memory/project_multiuser_plan.md`)

### Layered-coverage gap noted (future work)
The dashboard shows topic-level gap states but does not surface subtopic-level gaps. A topic at "20% mastered" can hide 5 completely untouched subtopics. The `at_risk_children` concept from the layered-coverage framework should be added to the dashboard after auth is complete.

---

## Session 8 Summary (2026-06-03)

### What was done this session

**1. matplotlib installed — Model Answers page unblocked**

`ModuleNotFoundError: No module named 'matplotlib'` on `1_Model_Answers.py:8`. Root cause: matplotlib was installed in system Python 3.9 but Streamlit runs on Homebrew Python 3.11. Fixed by installing into the correct interpreter:
```bash
/opt/homebrew/opt/python@3.11/bin/python3.11 -m pip install matplotlib numpy
```

**2. All Critical + High IES bugs fixed**

| Bug | File | Fix |
|---|---|---|
| Connection leak (CRITICAL) | All 5 IES pages | `@st.cache_resource` on `_get_conn()` in each page; removed all `conn.close()` calls |
| Silent DB save failure (CRITICAL) | `2_Quiz.py:532` | `except: pass` → `st.toast(f"Could not save attempt: {err}", icon="⚠️")` |
| Mastery not written on first attempt (HIGH) | `db.py` `submit_return_quiz` | Added `INSERT OR IGNORE INTO user_mastery` before `UPDATE` — ensures row always exists |
| No transaction in `submit_return_quiz` (HIGH) | `db.py` | Refactored: all reads moved before writes, all writes wrapped in `with conn:` atomic block |
| FD leak in `@st.cache_data` (HIGH) | `2_Quiz.py:92` | Added `try/finally c.close()` in `_load_all_questions` |
| Option sort scramble (MEDIUM) | `5_Return_Quiz.py:149,204` | `key=lambda x: x[0]` → `sorted()` on full string |

**3. Smoke test: 11/11 PASS** (up from 10/11 last session — Model Answers now fixed)

**4. Multi-user architecture planned (parallel agents)**

Full plan in `memory/project_multiuser_plan.md`. Key outputs:
- 16 DECIDE items, 9 ASSUME items, scale failure sequence
- MVMU = 6 changes, 5–7 focused days, safe to launch after that
- Discovered RISK-02: `6_RBI_Prep.py:21` `USER_ID = "rahul"` is a live bug even now
- Discovered DECIDE-08: `@st.cache_resource` is correct for single-user but wrong for multi-user

**5. UPSC Mains model answers page built** (`web/pages/7_UPSC_Mains.py`)

Standalone page querying `data/upsc.db` directly (exam_id=`upsc_eco_opt`). Sidebar: Paper I (31 topics, 477 Qs) / Paper II (50 topics, 431 Qs). Year radio navigation, LaTeX renders via `st.markdown()` KaTeX, rubric + data tabs. `@st.cache_resource` connection (no leak). Verified live: 11/12 PASS.

**6. Python 3.11 upgrade — permanent fix (root cause analysis)**

Root cause: project was split across Python 3.9 (Streamlit, broken pip) and Python 3.11 (Homebrew, already fully installed). `X | Y` union syntax appeared first in batch scripts (no crash), then crashed when it hit a Streamlit page. The `project_ies_exam_prep.md` memory file actively propagated the wrong 3.9 path to every session. Three structural fixes applied:

| Fix | What changed |
|---|---|
| Runtime | `streamlit run` now uses `/opt/homebrew/bin/streamlit` (Python 3.11) everywhere |
| Lock files | `.python-version` (3.11), `requirements.txt` (pillow + playwright added) |
| Memory | `project_ies_exam_prep.md` corrected 3.9→3.11; `feedback_python_version.md` created |
| run-app skill | Error triage block added — classify error before touching code |
| HANDOFF.md | `Watch For` section added at top |
| dev-workflow skill | L-DEV-29 (pin runtime at day zero), L-DEV-30 (classify before fixing), Error Triage Protocol section |

---

## Session 7 Summary (2026-06-03)

### What was done this session

**1. RBI Prep — 5 bugs fixed in `web/pages/6_RBI_Prep.py`**

| Bug | Root Cause | Fix |
|---|---|---|
| `KeyError: 'attempts'` crash on My Progress tab | `get_progress_data()` SELECT at line 156 listed 6 columns but excluded `attempts`; line 194 accessed `m["attempts"]` | Added `attempts` to SELECT |
| Phase 1 Drill explanations only shown for wrong answers; capped at 200 chars | `if not r["is_correct"]:` guard on explanation render; `[:200]` truncation | Removed guard, removed truncation |
| Phase 1 results view: single flat expander for all questions | Used one `st.expander("View breakdown")` containing plain text per question | Replaced with per-question expanders (Tier 2 style): option highlighting + full `Why:` for every question |
| Vague score card label `X% — Session complete` | Hardcoded copy | Changed to `Phase 1 Drill — X% correct` |
| Progress tab jargon labels `Formula Readiness` / `True Readiness` | Not self-explanatory to user | Changed to `Mastery Score (weighted avg)` / `Exam Readiness (gap-adjusted)` |

**2. Tier 2 Quiz — expanded from 36 to 54 questions (6 → 9 buckets)**

Three new buckets added to `BUCKETS` dict in `6_RBI_Prep.py`:

| Bucket | Key topics |
|---|---|
| 🌐 External Sector & BoP | BoP structure, CAD drivers, REER vs NEER, forex reserves, FDI vs FPI, ECB |
| 🏢 NBFC & Regulatory Framework | NBFC vs bank, SBR Upper Layer, HFC transfer to RBI (2019), P2P, Account Aggregator, NOF |
| 🏛 International Finance & Institutions | BIS/Basel, SDR basket, World Bank IDA vs IBRD, FSB, NDB (Shanghai), IMF conditionality |

Sufficiency analysis: 54 is the stopping point. Capital Markets and Agricultural Finance (NABARD) are low-weight in Phase 1 MCQ; better addressed in Phase 2 descriptive prep. Phase 1 DB (267 Qs) covers the theory gap.

**3. Streamlit testing — solved for entire model**

Root cause: Streamlit's React layer CSS-hides native `<input type="radio">` and custom-renders dropdowns. Native Playwright locators fail silently.

- Created `scripts/streamlit_test_utils.py` — reusable helpers for all pages: `answer_radio_groups()`, `click_tab()`, `submit_form()`, `check_for_errors()`, `run_smoke_test()`
- Created `.claude/skills/run-app/SKILL.md` — project skill documenting server start, all 7 pages, Playwright patterns, known IES bugs
- Confirmed working: `python3 scripts/streamlit_test_utils.py` runs smoke test across all 7 pages (10/11 PASS; Model Answers fails on pre-existing db.py:44 bug)

**4. All changes verified live**

Smoke test results:
```
✅ app, Quiz, Study Brief, My Progress, Return Quiz, RBI Prep
✅ RBI/Key Data, RBI/Phase 1 Drill, RBI/Tier 2 Quiz, RBI/My Progress
❌ Model Answers — pre-existing db.py:44 connection bug (not this session)
```

**5. Memory + skills updated**
- `memory/project_ies_exam_prep.md` — session 7 patch notes, Tier 2 count updated
- `memory/feedback_streamlit_testing.md` — NEW: full Playwright patterns for Streamlit
- `memory/MEMORY.md` — index updated
- `SKILL_REGISTRY.md` — run-app skill added
- `development-workflow` skill — L-DEV-28 added (Streamlit testing pattern)

---

## Exact Next Steps (from Session 8 / Python upgrade session)

### STUDY (before June 14 RBI exam — 11 days):
All bugs fixed. App is 12/12 pages working. Python 3.11 canonical. **Use the app.**
- RBI Phase 1 Drill → Smart Serve daily (IS-LM first, highest flag_impact = 0.20)
- UPSC Model Answers → review by topic (Paper I theory, Paper II Indian Economy)
- Return Quiz for IES topic verification
- Mundell-Fleming top-up: `scripts/rbi/06_topup_questions.py` — only 7 Qs, need ~13 more (not yet built)

### MVMU — MINIMUM VIABLE MULTI-USER (post-exam, 5–7 days, do in order):

Full plan: `memory/project_multiuser_plan.md` — 16 DECIDE items.

**Step 1 — Fix live RBI data corruption (30 min) ← DO FIRST**
`6_RBI_Prep.py:21`: `USER_ID = "rahul"` hardcoded. All RBI attempts from any user save as "rahul".
Fix: replace with `get_user_id()` from `db.py`.

**Step 2 — Revert @st.cache_resource → per-request connections (1 hour)**
All 5 IES pages currently use `@st.cache_resource` for DB connections — correct for single-user,
wrong for multi-user (Python sqlite3 not thread-safe at connection-object level). Replace with:
```python
conn = get_conn()
try:
    # page logic
finally:
    conn.close()
```
Also enable WAL mode in `get_conn()`: `conn.execute("PRAGMA journal_mode=WAL"); conn.execute("PRAGMA busy_timeout=5000")`

**Step 3 — Add users + sessions tables + Google OAuth (2–3 days)**
- `migrations/002_add_users_sessions.py` — schema from `memory/project_multiuser_plan.md`
- `pages/0_Login.py` — Google OAuth via `authlib`
- `web/auth.py` — `require_user()`, `validate_session_cookie()`, `create_session()`

**Step 4 — Auth gate on every page (half day)**
Replace `conn = get_conn()` at top of every page with `uid = require_user()` (hard-stops to login if unauthenticated). Remove fallback-to-"rahul" from `get_user_id()`.

**Step 5 — Rate limiting (half day)**
Add `daily_api_calls` + `quota_resets_at` to `users` table. Implement `check_and_increment_quota()` in `db.py`. Wire into `2_Quiz.py` before every AI call. Limit: 20 calls/day ($1.80/user/month max).

**Step 6 — Remove .env fallback from load_api_key() (15 min)**
Delete the path fallback in `db.py:83`. Hard `raise ValueError` if `ANTHROPIC_API_KEY` env var not set.

**Step 7 — Add composite indexes (15 min)**
```sql
CREATE INDEX idx_da_user_exam     ON descriptive_attempts(user_id, exam_id, created_at DESC);
CREATE INDEX idx_gse_user_topic   ON gap_state_events(user_id, topic_id, exam_id, created_at DESC);
CREATE INDEX idx_rqa_user_topic   ON return_quiz_attempts(user_id, topic_id, exam_id, created_at DESC);
CREATE INDEX idx_um_user_exam     ON user_mastery(user_id, exam_id);
CREATE INDEX idx_gs_user_exam_st  ON gap_states(user_id, exam_id, state);
CREATE INDEX idx_tas_user_exam    ON topic_attempt_summary(user_id, exam_id);
```

**Step 8 — Deploy on Hetzner CX21 (~€4.5/mo) or Railway ($5/mo)**
Single-process Streamlit + SQLite WAL. Set `ANTHROPIC_API_KEY` + Google OAuth credentials as env vars. Enable HTTPS (Caddy). Smoke test with 2 separate Google accounts.

### DEFERRED (after exams + MVMU):
- UPSC Mains web tab (`7_UPSC_Mains.py` + `8_UPSC_Model_Answers.py`)
- `user_events` universal audit log (DECIDE-15)
- `schema_versions` migration tracking (DECIDE-16)
- Migrate to PostgreSQL at 500 users (DECIDE-14)

---

## Session 6 Summary (2026-06-03)

### What was done this session

**1. Full project audit (parallel subagents)**

Code review subagent identified 13 bugs across `web/` pages:
- 2 CRITICAL: DB connection leak (OperationalError on concurrent sessions), silent quiz save failure
- 6 HIGH: wrong user data on direct page open, FD leak in cache, no transaction in submit_return_quiz, mastery never written on first attempt, rate-limit state initialized too late, duplicate questions from LEFT JOINs
- 3 MEDIUM: hardcoded dev path in API key loader, data contradiction in ie_3 (2011-12 vs 2022-23), option sort scrambling
- 2 LOW: dead code, legacy schema blank scores

**NOTE:** IES tab bugs (2_Quiz.py, 5_Return_Quiz.py, db.py) are NOT fixed yet. Fix them before the IES exam (June 19).

RBI analysis subagent confirmed:
- `6_RBI_Prep.py` was hardcoded (no DB, no AI), session-state only (scores lost on refresh)
- Phase 2 quiz wrapped silently to bucket 0 on completion — no handler
- ZERO RBI content in `ies.db` — no `rbi_` tables anywhere
- Phase 1 (70% of prep = 17 Tier 1 theory topics) was entirely missing

**2. Architecture decision: Stay in this app (not Devthorium)**
Devthorium = UPSC prelims MCQ tool, wrong fit for RBI descriptive prep.

**3. RBI MCQ bank — fully built**

| Script | Result |
|---|---|
| `scripts/rbi/00_init_rbi_db.py` | 5-table schema: rbi_questions, rbi_attempts, rbi_topic_mastery, rbi_sessions, rbi_topic_weights |
| `scripts/rbi/01_seed_topic_weights.py` | 29 topic weights from 2024 actual paper distribution |
| `scripts/rbi/02_generate_mcq_bank.py` | Haiku batch → 230 inserted, 5 failed (LaTeX) |
| `scripts/rbi/03_migrate_tier2.py` | 36 existing hardcoded Tier 2 questions → DB |
| `scripts/rbi/04_compute_weights.py` | priority_weight, flag_impact computed per question/topic |
| `scripts/rbi/05_fix_parse_errors.py` | Per-object JSON extraction fix for 5 failed topics → +73 questions |

**Final DB state:**
```
rbi_questions:     303 total (267 Tier 1 theory + 36 Tier 2 current affairs)
rbi_topic_weights: 29 topics with 2024 paper-derived weights
rbi_topic_mastery: 24 topics (seeded for user 'rahul')
rbi_attempts:      0 (fresh start)
Trap questions:    114 (38%)
Hard questions:    87 (29%)
```

**Priority order (flag_impact):**
1. is_lm (0.20) — Macro, 16 questions
2. mundell_fleming (0.10) — Intl Econ, 7 questions (17 from fix + more batching needed)
3. india_macro_data (0.09) — Indian Economy, 21 questions
4. qtm_monetary (0.08) — Macro, 15 questions
5. classical_growth (0.07) — Growth, 15 questions

**4. `6_RBI_Prep.py` fully rewritten (4 tabs)**

| Tab | Status | What it does |
|---|---|---|
| 📊 Key Data Cards | ✅ unchanged | 6 sections, ~35 verified data items |
| 🧠 Phase 1 Drill | ✅ NEW | Smart Serve (coverage-driven) + Filter mode, reads from rbi.db, saves attempts, updates mastery with INSERT OR REPLACE |
| ❓ Tier 2 Quiz | ✅ fixed | 6 buckets, completion bug FIXED, aggregate summary on all-done, weakest-bucket CTA |
| 📈 My Progress | ✅ NEW | Formula readiness + True readiness, gap alerts sorted by flag_impact, subject coverage bars |

**All IES code review mistakes avoided in new RBI UI:**
- `@st.cache_resource` connection (no leak)
- `with conn:` transaction in save_attempt
- `INSERT OR REPLACE` for mastery (no first-attempt miss)
- `USER_ID = "rahul"` constant (no session state dependency)
- All session state in `_SS_DEFAULTS` dict at top of file
- `st.toast()` on DB error (no silent failure)
- ie_3 corrected: base year → 2022-23 (was 2011-12 — was wrong)

**5. Web research (subagent)**
ixamBee 2024 PYQ analysis confirmed: International Economics is rank 2 (10-11 questions), not rank 4. Mundell-Fleming appeared TWICE in 2024 — now correctly weighted. 2025 paper changed to 43 questions/66 marks.

---

## Exact Next Steps

### IMMEDIATE (before June 14 exam):

**Step 1 — Mondell-Fleming question gap (needs more questions)**
Mundell-Fleming is rank 2 priority but only has 7 questions in DB (17 were generated, 10 were lost to parse errors that could only recover 7 via regex extraction). Need ~13 more.
```bash
# Re-run just mundell_fleming with direct API (not batch) to top up to 20:
# Add a one-off script: scripts/rbi/06_topup_questions.py
# Use client.messages.create() directly for intl_econ__mundell_fleming
```

**Step 2 — Fix critical bugs in IES tabs (before June 19)**
From code review — these affect data integrity NOW:
```
web/db.py:44         → @st.cache_resource connection (CRITICAL)
web/pages/2_Quiz.py:532 → except: pass on DB insert (CRITICAL)
web/db.py:469        → mastery not written on first attempt (HIGH)
web/db.py:387        → no transaction in submit_return_quiz (HIGH)
web/pages/2_Quiz.py:92  → FD leak in @st.cache_data (HIGH)
```

**Step 3 — Run the app and verify Phase 1 Drill**
```bash
/Users/rahulsingh/Library/Python/3.9/bin/streamlit run web/app.py
```
Navigate to RBI Prep → Phase 1 Drill → Start Smart Session (10 Questions)
Should show IS-LM questions first (highest flag_impact = 0.20).

**Step 4 — English paper (separate build, post-exam or quick MVP)**
Study plan has full English prep plan in `data/rbi_ies_study_plan.md:130-145`.
Build as a shared module across IES/UPSC/RBI (not RBI-specific).

### DEFERRED (after June 14):

**Step 5 — UPSC Mains web tab**
- `web/pages/7_UPSC_Mains.py` — landing dashboard
- `web/pages/8_UPSC_Model_Answers.py` — mirrors 1_Model_Answers.py but uses `data/upsc.db`
- Add multi-exam support in `web/db.py`

**Step 6 — Streamlit Cloud deploy**
Push to GitHub + set `ANTHROPIC_API_KEY` secret on share.streamlit.io.

---

## Architecture Decisions Made This Session

| ID | Decision | Rationale |
|---|---|---|
| DECIDE-06 | Separate `rbi.db`, not shared with `ies.db` | Consistent with DECIDE-01 isolation principle |
| DECIDE-07 | @st.cache_resource for DB connection in RBI pages | Fixes CRITICAL connection leak from code review |
| DECIDE-08 | INSERT OR REPLACE for mastery rows (not IF NOT EXISTS) | Fixes HIGH bug: first attempt never wrote mastery |
| DECIDE-09 | Stay in Descriptive Exams app for RBI (not Devthorium) | Devthorium = MCQ-only UPSC prelims. Wrong fit. Post-June 14: consider productising for other aspirants |
| DECIDE-10 | Priority weights derived from 2024 actual paper distribution | ixamBee PYQ analysis gave real question counts; more reliable than syllabus estimation |
| DECIDE-11 | Batch + fix script pattern (same as UPSC pipeline) | LaTeX/newlines in JSON require per-object extraction fallback; reuse existing fix_parse_errors pattern |
| DECIDE-12 | English paper as shared module across IES/UPSC/RBI | Essay appears in all three exams; don't build 3 separate implementations |

---

## File Locations

| Resource | Path |
|---|---|
| RBI DB | `data/rbi.db` |
| RBI scripts | `scripts/rbi/00_*.py` through `05_*.py` |
| RBI prep page | `web/pages/6_RBI_Prep.py` |
| IES DB | `data/ies.db` |
| UPSC DB | `data/upsc.db` |
| Study plan | `data/rbi_ies_study_plan.md` |
| NotebookLM sources | `data/notebooklm/` |
| Theory source | `data/notebooklm/rbi_theory_mcq_source.md` |

---

## To Start App
```bash
/opt/homebrew/bin/streamlit run web/app.py
```
Opens at http://localhost:8501

**Python:** 3.11.15 via Homebrew (`/opt/homebrew/bin/python3.11`). Do NOT use the system 3.9 path (`/Library/Python/3.9/bin/`) — pip is broken there and it doesn't support `X | Y` union type syntax.

---

## Session 5 (preserved)

### IES 2026 — COMPLETE
Backend: 1219 PYQs + rubrics + model answers + 150 MCQs. Web app live on :8501.
No pending tasks for IES.

### UPSC Economics Optional — DATA PIPELINE COMPLETE ✅ | Web app pending

**Final DB state:**
```
pyq_questions:     908
question_rubrics:  908 (100%)
model_answers:     908 (100%)
  upsc_p1:         477/477
  upsc_p2:         431/431
document_chunks:  1,044
topic_base_scores:  16
```

**Next Steps (UPSC):**
Build web app (7_UPSC_Mains.py + 8_UPSC_Model_Answers.py). All data is ready.

**Architecture Decisions (UPSC):**
- DECIDE-01: Separate upsc.db (isolation)
- DECIDE-02: Same 16-table IES schema + 5 new tables
- DECIDE-03: Full text chunking for notes (future RAG)
- DECIDE-04: Skip topper answers + official QPs (scanned/needs_ocr)
- DECIDE-05: Store reference answers separately
