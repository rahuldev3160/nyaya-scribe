# Descriptive Exams — Session Handoff

## Last Updated
2026-06-03 (Session 6)

---

## Project Status

### IES 2026 — COMPLETE
Backend: 1219 PYQs + rubrics + model answers + 150 MCQs. Web app live on :8501.

### UPSC Economics Optional — DATA PIPELINE COMPLETE ✅ | Web app pending
908/908 PYQs + rubrics + model answers in `data/upsc.db`.

### RBI DEPR 2026 — MCQ BANK BUILT ✅ | UI rebuilt ✅
New `data/rbi.db` with 303 questions. `6_RBI_Prep.py` fully rewritten. See below.

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
/Users/rahulsingh/Library/Python/3.9/bin/streamlit run web/app.py
```
Opens at http://localhost:8501

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
