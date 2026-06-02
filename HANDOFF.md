# Descriptive Exams — Session Handoff

## Last Updated
2026-06-03 (Session 2)

---

## Project Status

### IES 2026 — COMPLETE
Backend: 1219 PYQs + rubrics + model answers + 150 MCQs. Web app live on :8501.
No pending tasks for IES.

### UPSC Economics Optional — DATA PIPELINE COMPLETE ✅ | Web app pending

---

## UPSC Session Summary (2026-06-03, Session 2)

### What was completed this session

**Full data pipeline — 908/908 PYQs with rubrics + model answers.**

| Step | Script | Result |
|---|---|---|
| Source doc indexing | 05 | 111 docs (63 indexed, 48 needs_ocr) |
| Note chunking | 06 | 1,044 chunks, 42 docs, avg 558w |
| Topic base scores | 10 | 16 topics scored; top: growth_development |
| Rubrics (Haiku batch) | 08 | 908/908 (100%) — 3 retried via direct API |
| Model answers (Sonnet batch) | 09 | 908/908 (100%) — 10 fixed via fix_parse_errors.py |

**Bugs fixed:**
- Script 08: 3 rubrics failed JSON parse (markdown fence edge case) → retried synchronously
- Script 09: 10 answers failed JSON parse (LaTeX backslash escapes: `\alpha`, `\cdot` invalid in JSON) → `fix_parse_errors.py` created with regex fallback extractor
- Script 09 was originally run with `| head -5` pipe, which killed it after 5 lines; answer batch itself completed successfully; re-ran from local cache (no API cost)

**New file created:**
- `scripts/upsc/fix_parse_errors.py` — two-stage fixer: (1) backslash escape regex, (2) per-field regex fallback for malformed JSON

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

---

## UPSC Session Summary (2026-06-03)

### What was built this session

**DB schema:** `data/upsc.db` — 21 tables (16 IES tables + 5 new: users, source_documents, document_chunks, reference_answers, economic_data_points). Exam configured as `exam_id = 'upsc_eco_opt'`, exam_date `2026-09-15`.

**Topics seeded:** 16 topics + 65 subtopics across 2 papers:
- `upsc_p1`: advanced_micro, welfare_distribution, advanced_macro, money_banking_finance, international_economics, growth_development
- `upsc_p2`: indian_eco_pre1947, planning_development, growth_composition, industry_services, poverty_unemployment, agriculture, external_sector_bop, monetary_banking_india, public_finance_india, current_topics

**Data ingested (already in DB):**

| Table | Count | Source |
|---|---|---|
| pyq_questions | 908 | 763 Ecoholics topic-wise + 145 from PYQs/ folder |
| reference_answers | 24 | PYQs(Before1947).pdf — coaching Q+A pairs |
| economic_data_points | 129 | 28 RBI + 51 Economic Survey (2024-25, 2025-26) + 50 Budget |
| source_documents | 46+ | Script 05 was still running at session end |
| topics | 81 | 16 + 65 subtopics |
| users | 1 | 'rahul' seeded |

**Scripts written (all in `scripts/upsc/`):**

| Script | Status | Notes |
|---|---|---|
| 01_init_upsc_db.py | ✅ DONE | 21-table schema in data/upsc.db |
| 02_seed_topics_upsc.py | ✅ DONE | 16 topics, 65 subtopics |
| 03_ingest_pyq_ecoholics.py | ✅ DONE | 763 PYQs from Ecoholics PDFs |
| 04_ingest_pyq_solved.py | ✅ DONE | 145 PYQs + 24 reference answers |
| 05_index_source_docs.py | ⏳ RUNNING | Was still indexing 111 PDFs at session close |
| 06_chunk_notes.py | ⏳ PENDING | Needs 05 to complete first |
| 07_migrate_economic_data.py | ✅ DONE | 129 data points |
| 08_generate_rubrics_upsc.py | ⏳ PENDING | Haiku batch — ~$0.50 |
| 09_generate_answers_upsc.py | ⏳ PENDING | Sonnet batch — ~$5-8 |
| 10_compute_base_scores_upsc.py | ⏳ PENDING | No API cost |

---

## Exact Next Steps (in order)

### Step 0 — ALL DATA PIPELINE STEPS DONE ✅
Scripts 05, 06, 10, 08, 09 all complete. 908/908 rubrics + answers in upsc.db.

### Step 1 — Build web app (UPSC Mains tab)

### Step 1 — Verify script 05 completed
```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('data/upsc.db')
cnt = conn.execute(\"SELECT COUNT(*) FROM source_documents\").fetchone()[0]
print(f'source_documents: {cnt} (expected ~111)')
by_status = conn.execute(\"SELECT status, COUNT(*) FROM source_documents GROUP BY status\").fetchall()
for s, c in by_status: print(f'  {s}: {c}')
conn.close()
"
```
If count < 100, re-run: `python3 scripts/upsc/05_index_source_docs.py` (idempotent).

### Step 2 — Run script 06 (chunk notes — no API cost, ~5-10 min)
```bash
python3 scripts/upsc/06_chunk_notes.py
```
Expected: ~2,000–3,000 chunks from 73 extractable notes PDFs.

### Step 3 — Run script 10 (priority scores — no API cost)
```bash
python3 scripts/upsc/10_compute_base_scores_upsc.py
```

### Step 4 — Run script 08 (rubrics — Haiku batch, ~$0.50)
```bash
python3 scripts/upsc/08_generate_rubrics_upsc.py
```
Generates rubrics for 908 PYQs. Safe to restart (saves batch_id to `data/upsc_rubrics_batch.txt`).

### Step 5 — Run script 09 (model answers — Sonnet batch, ~$5-8)
```bash
python3 scripts/upsc/09_generate_answers_upsc.py
```
Generates intro/body/conclusion + diagram + data for 908 questions.
Safe to restart (saves batch_id to `data/upsc_answers_batch.txt`).

### Step 6 — Build web app (UPSC Mains tab)
Files to create:
- `web/pages/7_UPSC_Mains.py` — landing dashboard for UPSC Optional
- `web/pages/8_UPSC_Model_Answers.py` — Model answers browser (mirrors 1_Model_Answers.py but uses upsc.db)
- Update `web/db.py` — add multi-exam support (thin ExamConfig abstraction) OR create `web/upsc_db.py`

---

## Architecture Decisions Made This Session

| ID | Decision | Rationale |
|---|---|---|
| DECIDE-01 | Separate upsc.db, not shared with ies.db | Isolation — one exam's failure can't corrupt another |
| DECIDE-02 | Same 16-table IES schema + 5 new tables | Full reuse; no schema reinvention |
| DECIDE-03 | Full text chunking for notes (not just metadata) | Enables future RAG at scale |
| DECIDE-04 | Skip topper answers + official QPs (scanned) | Flagged as needs_ocr in source_documents |
| DECIDE-05 | Store reference answers separately (reference_answers table) | Compare coaching vs Claude answers; use as generation context |

---

## File Locations

| Resource | Path |
|---|---|
| DB | `data/upsc.db` |
| Topic config | `config/topics_upsc_eco.json` |
| All scripts | `scripts/upsc/01_*.py` through `10_*.py` |
| PYQ source PDFs | `/Users/rahulsingh/Desktop/UPSC/Mains/Optional/PYQ- paper 1/` + `PYQ- Paper 2/` |
| Notes source PDFs | `/Users/rahulsingh/Desktop/UPSC/Mains/Optional/Paper I/` + `Paper II/` |
| Economic Survey | `sources/ge_03/Economic Survey 2024-25.pdf`, `2025-26.pdf` |
| Budget | `sources/ge_04/Budget_Highlights_2026.pdf`, `Union_Budget_Analysis-2026-27.pdf` |

---

## To Start App (IES — still works)
```bash
/Users/rahulsingh/Library/Python/3.9/bin/streamlit run web/app.py
```
Opens at http://localhost:8501
