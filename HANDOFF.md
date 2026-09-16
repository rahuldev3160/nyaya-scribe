# Handoff — Nyaya Scribe (Descriptive Exams)
**Session:** S51 → S52 | 2026-09-17 | Branch: `feature/repair-eco-optional-gaps` (not merged to main, branched off `main`)

## 2026-09-17 (S52) — Eco-Optional PYQ gap repair: 135 real sub-parts recovered, 2021-2025

A same-day read-only audit found `upsc_eco_opt.db`'s `pyq_questions` was ~48% incomplete for
every checkable year (2021-2025) against the real 28-lettered-sub-part exam structure (Q1/Q5
compulsory, 5 sub-parts a-e each @ 10m; Q2/Q3/Q4/Q6/Q7/Q8, 3 sub-parts a/b/c each). This
session filled the gap from real source material only — **no fabricated question was
inserted.**

**Method (per Rahul's verify-before-building rule):** OCR'd all 10 official scanned booklets
at `~/Desktop/UPSC/Mains/Optional/Economics/PYQs_paper{1,2}/{2021..2025}.pdf` via
`pdftoppm -r 400` → `tesseract --psm 6` (both already on the machine; OCR quality on the
English half of every bilingual paper was excellent — only the Hindi column, never used, OCR'd
poorly). For every one of the 10 paper-years, independently transcribed the full Q1-Q8 (all
lettered sub-parts) from the OCR text, then cross-matched **by question content, not just
count** against the DB's existing rows to derive the exact missing list myself — did not
blindly trust the audit's summary numbers. All 10 derivations matched the audit's per-year
totals; the itemized missing lists for 2024 (both papers) matched the audit's own provided
list exactly.

**Exact before → after counts** (all rows verified present in DB after insert):

| Paper | Year | Before | Missing (recovered) | After |
|---|---|---|---|---|
| P1 | 2021 | 24 | 4 | 28 |
| P1 | 2022 | 6 | 22 | 28 |
| P1 | 2023 | 12 | 16 | 28 |
| P1 | 2024 | 16 | 12 | 28 |
| P1 | 2025 | 6 | 23 | 29* |
| P2 | 2021 | 24 | 4 | 28 |
| P2 | 2022 | 15 | 13 | 28 |
| P2 | 2023 | 22 | 6 | 28 |
| P2 | 2024 | 17 | 11 | 28 |
| P2 | 2025 | 4 | 24 | 28 |

*P1 2025 lands at 29, not 28 — a pre-existing row-granularity quirk (Q4(b)'s two numbered
sub-items were already split across 2 existing rows before this session; not touched, not
duplicated). All 28 distinct lettered sub-parts are now covered across those 29 rows.

**Total: 135 real recovered sub-parts inserted** (audit's original estimate was ~134 —
the 1 extra is that same P1-2025 row-splitting artifact, already flagged as a separate,
out-of-scope systemic issue). **0 unrecoverable** — OCR quality on every English question was
clean enough to transcribe with confidence; nothing was skipped for illegibility.

**Real surprise (worth flagging):** P2 2022's Q7(a) ("Critically examine the various poverty
alleviation programmes in India since 1970's") had **no clean year=2022 row** — but its exact
text was already sitting in the DB, silently concatenated onto the front of an existing
year=2021 row (`upsc_p2_0137`), a leftover parsing artifact from the original ecoholics
ingestion (visible as a stray `(2022)` marker mid-string in that row's text). Left `0137`
untouched (out of scope, pre-existing, not a 2021-2025 *insert* target) and added a clean
new year=2022 row for the same real text.

**New rows:** `upsc_p1_0503`–`upsc_p1_0579` (77 rows) and `upsc_p2_0438`–`upsc_p2_0495`
(58 rows), continuing the existing sequential id convention (same approach as
`scripts/upsc/03_ingest_pyq_ecoholics.py`'s `ingest_paper()`). Schema fields: `marks`,
`answer_length`, `key_concepts`, `subtopic_id` left NULL (matches the existing
majority-NULL convention — fixing that systemic gap is explicitly out of scope this
session). `topic_id` assigned to the best-fit existing **top-level** topic per paper (never
invented; cross-checked against `topics WHERE topic_level='topic'`), following the same
subject-matter judgment the original ecoholics topic-PDF split used. `question_hash` =
sha256 of whitespace-normalized lowercase text, verified zero collisions against the full
908+135=1043-row table.

**Backup:** pre-repair snapshot of all 146 existing 2021-2025 rows (both papers) recorded via
`~/.claude/backups/backup_tool.py` — **backup id #7**,
`~/.claude/backups/data/Descriptive-exams/20260916_223824__eco_optional_2021_2025_pre_repair.json`.
Diffed all 146 rows post-insert against this backup: **0 changed, 0 missing** — confirmed
purely additive.

**Tests:** `tests/test_eco_optional_repair_2021_2025.py` (7 new) — exact per-year totals,
135-row count split correctly 77/58 by paper, sample new rows queryable by exact text, all
new `topic_id`s are valid top-level topics, zero duplicate `question_hash` table-wide, a
newly-inserted row actually renders through the live `/upsc/eco/<topic_id>` and
`/upsc/eco/<topic_id>/q/<question_id>` routes (regression guard for a BUG-036-style silent
unreachability), and a scope guard confirming `upsc_eco_opt.db`'s `pyq_questions` holds only
`upsc_eco_opt` rows (gs1-4 untouched, different DB entirely). Full suite:
**26/26 passing** (19 pre-existing + 7 new), up from 19/19 before this session.

**Explicitly NOT fixed this session (flagged, out of scope per brief):**
- 93% of all 1043 `pyq_questions` rows still have NULL `marks` (systemic, pre-existing,
  affects gs/ies/rbi too — separate task).
- 55 rows in `upsc_p2` still have `year=0` (pre-existing, separate task).
- Row-granularity inconsistency (some multi-part answers split across 2 DB rows for one
  printed letter, e.g. P1 2025 Q4(b)) — not normalized, not touched on existing rows.
- `upsc_p2_0137`'s garbled 2021/2022 text concatenation — pre-existing, not touched (see
  surprise above).
- Nothing pushed to Railway, `.env`/git config untouched, no changes to gs1-4 or
  nyaya-core/Devthorium.

### Exact next step (S52/S53 start here)
This branch (`feature/repair-eco-optional-gaps`) needs Rahul's review/approval before
merging to main (same pending-PR pattern as `feature/attempt-flow-gs-eco` and
`feature/ingest-gs2-pyqs`, both still separately unmerged from S50/S51 — this branch does
not touch either of those areas). After that: the NULL-marks and year=0 systemic issues
flagged above are natural next targets if Rahul wants them fixed; otherwise resume wherever
S51 left off (gs1/gs3 re-sourcing or canvas/vision-eval, PLAN-024 step 2).

## 2026-09-17 (S51) — GS2 PYQ re-ingestion: 200 real questions, 2016-2025 (BUG-035 gs2 re-sourcing)

BUG-035 (S50) left gs1/gs2/gs3 empty after deleting 140 scraper-junk rows. A same-day discovery
pass found a real, already-transcribed compilation for gs2 specifically:
`~/Downloads/upsc-gs2-pyq-compilation.docx` — this session ingested it. gs1/gs3 remain empty
(no source found yet, still tracked separately, not touched this session).

**Source verification (done before writing any parser, no python-docx available anywhere
locally — read via stdlib `zipfile` + `xml.etree`):** the docx is 100% table-based, 10 Word
tables (one per year, 2025→2016 in document order), each with a header row + 20 question rows
(Q. No. / question text / marks / word limit). Spot-checked word-for-word against the real
scanned UPSC papers at `~/Desktop/UPSC/Mains/GS2/PYQs/UPSC_GS2_*.pdf`: **2016 all 20/20
questions, 2025 Q1-14, 2020 Q1-4 — all matched exactly**, including 2016's outlier marking
scheme (12.5 marks × 20, 200-word limit, vs. 2017-2025's 10/15-mark × 20, 150/250-word
pattern) — confirms the docx is a faithful, complete transcription, no fabrication risk.

**Ingested:** `scripts/ingest_gs2_pyqs_docx.py` (new, additive-only, refuses to run if gs2
already has rows) — 200 rows, exactly 20 per year 2016-2025, all `source_type='official_pyq'`,
`exam_id='upsc_gs_mains'`, `paper_id='gs2'`, `question_id` following gs4's existing
`gs2_<year>_q<NN>` convention. marks/answer_length taken verbatim from the source cell, never
guessed (2016's `12.5`/`'200 words'` preserved exactly, not normalized to the later years'
pattern).

**Topic assignment — real surprise, judgment call flagged for Rahul:** GS2's `topics` table
was already fully seeded (7 top-level topics + subtopics, pre-existing). Started from the
shared `scripts/seed_upsc_gs_pyqs.py`'s `KEYWORD_TOPIC_MAP` (same one already used for gs4's
81 rows) — but it alone left 96/200 (48%) of real GS2 questions unmatched, all dumped into a
single fallback bucket (`gs2_constitution`), because UPSC's actual phrasing often doesn't hit
the shared map's keywords verbatim (e.g. "Comptroller and Auditor General" without "(CAG)",
"Non-Governmental Organizations" not containing the substring "ngo", "Article 356" not
matching "art 356"). Added a GS2-specific supplementary keyword layer (`GS2_SUPPLEMENT` /
`GS2_SUPPLEMENT_TOKENS` in the new script, applied only when the shared map returns nothing,
manually derived by reading all 96 originally-unmatched questions) that cut the true fallback
rate to 3/200 (1.5%) — and those 3 are themselves a reasonable constitution-topic fit
(Financial Emergency/Art 360, Right of Movement/Art 19, one genuinely generic
governance-discourse question). Final distribution: constitution 34, governance 41, ir 40,
social_justice 33, parliament_exec 27, judiciary 12, federalism 13 — all 7 are pre-existing
top-level `topics` rows, no new topic_id invented.

**Bug found and fixed during ingestion (not yet filed as a numbered BUG — flagging here):**
the *shared* `KEYWORD_TOPIC_MAP` itself (not just this session's supplement) targets a
subtopic id, `gs2_fed_panchayati` (`topic_level='subtopic'`), for panchayat/ULB keywords. But
`upsc_bp.py`'s `_get_topics()` only lists `topic_level='topic'` rows in the `/upsc/mains`
browse dropdown — so any question left tagged with a subtopic id would be real data but
unreachable from the normal UI flow. This was never caught before because gs2 had zero real
rows prior to this session (gs1-3 were scraper junk since inception). Added a normalization
step in the new script (`build_rows()`) that resolves any subtopic-level assignment up to its
parent top-level topic_id, regardless of which map produced it — 4 of the 200 rows needed
this. Worth fixing in the shared script too if gs1/gs3 are ever re-sourced with real data.

**Tests:** `tests/test_gs2_pyq_ingestion.py` (8 new tests) — exact per-year counts, no
fabricated marks/word-limit, 2016's outlier marking scheme preserved, all topic_ids
dropdown-reachable (regression test for the bug above), sample-row text matches the
hand-verified source exactly, gs1/gs3/gs4 untouched, and the existing `/upsc/mains?paper=gs2`
+ `/upsc/mains/q/<id>` routes actually surface and render the new rows — no code changes were
needed in `upsc_bp.py` itself. Full suite: **19/19 passing** (11 pre-existing + 8 new).

**Not done, deliberately (out of scope per this session's brief):** gs1/gs3 re-sourcing (no
real source found yet — separate task), gs4 untouched, no model answers/rubrics generated for
the new gs2 rows (separate task, same backlog item BUG-035 already noted for gs4), nothing
pushed to Railway or committed to main — local-only, on `feature/ingest-gs2-pyqs`.

### Exact next step (S52 start here)
Either: (a) merge `feature/ingest-gs2-pyqs` after Rahul's review, or (b) find/verify a real
source for gs1/gs3 the same way this session did for gs2, or (c) generate model answers for
gs2's 200 real PYQs (same pipeline already used for gs4). `feature/attempt-flow-gs-eco`
(S50) is still separately unmerged and unrelated to this branch.

## 2026-09-16 (S50, continued) — BUG-035 executed: 128 junk GS Mains rows deleted

Rahul approved deletion explicitly. Re-verified all 128 gs1/gs2/gs3 rows (`source_type IS
NULL`, untagged since PLAN-021) were still exactly as documented and still genuine junk before
touching anything; checked all plausible dependent tables (model_answers, descriptive_attempts,
question_rubrics, context_packages) — zero references, no orphan risk. Backed up all 128 rows
(full columns) to the **new cross-project backup registry** at `~/.claude/backups/` (backup
id #2) before deleting — see that tool's own docstring for query usage. Deleted; verified only
gs4's 93 clean rows remain. Full detail: `.knowledge/bugs/BUG-035.md`.

**Addendum (same session):** Rahul then approved clearing the 12 gs4 rows too (same junk
pattern, from the 2026-08-30 audit, never part of the original BUG-035 decision text). Same
process: verified via `sqlite3` CLI, checked dependents (0), backed up (registry id #3),
deleted. `upsc_gs_mains` now holds exactly 81 rows — all real, all gs4, all `official_pyq`.
gs1/gs2/gs3 are empty pending real re-sourcing (separate, not-yet-scoped task).

**New reusable infra, cross-project (not specific to this repo):** `~/.claude/backups/` now
holds a small stdlib-only SQLite-backed backup registry (`backup_tool.py`) any project can call
before a destructive operation — `record` to back up + tag data with project/data_type/reason/
context, `query`/`list`/`show` to find it again later. Use this for any future destructive
change in any project, not just this one.

## 2026-09-16 (S50) — RISK-12 closed: attempt-submission flow for GS1-4 + Eco-Optional

Extended PLAN-024 Phase 1's attempt-history pattern (S49) to the two surfaces it couldn't
reach: GS Mains and Eco-Optional. Both had zero attempt-submission route before this session
— verified first, not assumed (per RISK-12).

**Real surprise, changed the approach:** `descriptive_attempts` in `upsc_gs.db` and
`upsc_eco_opt.db` already exist with the *exact* IES-shape schema, including
`model_revealed`/`revealed_at`/`input_mode` from S49's own m067/m068 migrations — 0 rows in
either table, completely dormant. **No new migration was needed at all.** Also found
Eco-Optional already has a full 908-row `question_rubrics` table (rubric_points + key_terms,
same shape IES uses) — so `_score_answer`-style scoring worked directly, no new rubric
design required. GS Mains' own `question_rubrics` table exists but is empty for all 4
papers (including gs4) — scoring degrades gracefully to "No rubric provided," same as IES
already handles.

**Built:**
- `web/blueprints/upsc_bp.py` — added `/upsc/mains/q/<question_id>` (GET, detail + timeline)
  and `/upsc/mains/q/<question_id>/submit` (POST) + `_score_gs_answer()` (copy of
  `ies_quiz_bp._score_answer`'s forced-tool-use pattern, GS-flavored system prompt). Linked
  from `upsc_mains.html`'s existing question cards ("Attempt this question →").
- `web/blueprints/upsc_eco_bp.py` (new blueprint, registered in `app.py`) — `/upsc/eco/<topic_id>`
  (question list per topic, was completely missing before — Eco-Optional only had a
  topic-level dashboard) + `/upsc/eco/<topic_id>/q/<question_id>` (+`/submit`), same pattern.
  New templates `upsc_eco_topic.html`, `upsc_eco_question.html`, `upsc_mains_question.html`.
- Both use the existing `ai_scoring` feature gate (same one IES already shares) — did not add
  a per-exam gate like Essay's `essay_eval`.
- Neither has an explicit "reveal" button — matched IES/Essay's pattern (model answer always
  shown), not Ethics's outlier explicit-reveal flow. `model_revealed`/`revealed_at` stay at
  schema defaults (0/null); only `input_mode` (`'typed'`, matching IES/Essay's current live
  behavior — photo-upload isn't wired into any submit route yet anywhere in this repo) is
  meaningfully in play today.
- **Bug found + fixed in passing (BUG-036):** `upsc_dashboard.html`'s Study/Write buttons and
  `upsc_topic_state()`'s redirect pointed at `/upsc/mains` (GS Mains — wrong exam, wrong DB)
  for Eco-Optional topics, a dead leftover from S46's exam_id fix. Now point at the new
  `/upsc/eco/<topic_id>`. Without this fix the new Eco-Optional routes would have been
  unreachable from the dashboard.
- **BUG-035 handling:** gs1-3's PYQ bank is still scraper junk (unfixed, not this session's
  job). Only `gs4_2025_q01` (gs4, real PYQ + real model answer) was used as the GS Mains test
  fixture — gs1-3 rows were deliberately not used to validate the new route, so contamination
  never silently passed as "tested."
- Tests: `tests/conftest.py` (throwaway user/session + additive-only cleanup fixtures),
  `tests/test_gs_mains_attempts.py`, `tests/test_eco_opt_attempts.py` — 11 tests, all against
  real seeded rows (`gs4_2025_q01`, `upsc_p1_0001`) via Flask `test_client`. No test suite
  existed before this session (0 → 11 passing). Run: `/opt/homebrew/bin/python3.11 -m pytest tests/ -v`.

Logged as DECIDE-50 and RISK-12 (now RESOLVED) in `MASTER_INDEX.md`; BUG-036 in
`.knowledge/INDEX.md`.

**Not done, deliberately (out of scope per this session's brief):** BUG-035's actual cleanup,
canvas/vision-eval (PLAN-024 step 2), any photo-upload wiring, any change to nyaya-core or
Devthorium.

### Exact next step (S51 start here)
Branch `feature/attempt-flow-gs-eco` is uncommitted-to-main, not pushed — needs Rahul's PR
review/approval before merging. After that: canvas + unified submit + vision eval (PLAN-024
step 2) is still the next unblocked step in PLAN-024's own sequencing.

---

## 2026-09-16 (S49) — PLAN-024 Phase 1 complete: migrations + attempt-history timeline UI

Resumed PLAN-024 (paused since S48). **Migrations** (`migrations/m066`-`m070`):
`model_revealed`/`revealed_at`/`input_mode` on `descriptive_attempts` (ies/upsc_eco_opt/
upsc_gs) and `essay_attempts` (upsc_gs); `input_mode` only on `ethics_attempts` (already had
the other two from m046). Applied via `scripts/migrate.py`, verified via `PRAGMA table_info`.

**Timeline UI** — Rahul's decision: mounted on existing question-detail pages, one shared
component. Built `web/templates/partials/attempt_timeline.html` (this repo's first
cross-blueprint reusable template) and mounted it on `essay_detail.html`,
`ethics_question.html`, `ies_quiz.html`. Each blueprint fetches full attempt history
(previously only the latest attempt was ever queried) and normalizes per-table score
differences (essay 0-100, IES 0-10 rescaled, ethics self-rated/no AI score) before handing a
consistent shape to the shared partial. Verified end-to-end via Flask `test_client` with
seeded attempt rows (200 responses, timeline block present and correctly populated, colour
thresholds correct post-rescale) — no automated test suite exists in this repo to run instead.

**Real gap surfaced, not fixed here:** GS1-4 and Eco-Optional have no live
attempt-submission route at all (verified by reading the actual blueprints, not assumed) —
GS Mains' `mains()` route only reads `pyq_questions`/`model_answers`, never writes/reads
`descriptive_attempts`; Eco-Optional has no per-question detail route, only a topic
dashboard. So neither could get a timeline mounted today. This is a separate, larger gap
(building the submission flow itself) than anything PLAN-024 Phase 1 scoped — flagged for a
future session, not silently dropped.

Full detail: `.knowledge/plans/PLAN-024.md`'s Build sequence section. Logged as DECIDE-49
(timeline UI shape) and RISK-12 (GS1-4/Eco-Optional gap) in `MASTER_INDEX.md`.

**PLAN-024 Phase 1 is now fully done.** Canvas/vision-eval (step 2) is unblocked
schema-wise (`input_mode` exists everywhere it needs to) and is next per PLAN-024's own
sequencing, ahead of BUG-035's cleanup (step 4) and topper-grounded generation (step 3,
still gated on sourcing).

### Exact next step (S50 start here)
Canvas + unified submit + vision eval (PLAN-024 step 2) — the next unblocked step in
PLAN-024's build sequence. Separately, decide whether to build GS1-4/Eco-Optional's missing
attempt-submission flow (see gap above) before or after canvas.

---

## 2026-09-02 (S48) — Personal-first pivot: planning only, nothing built yet

Rahul brought a 14-page handwritten feature brainstorm (`~/Downloads/SCRIBE - NYAYA_...pdf`).
Synthesized into 10 clusters (`PLAN-022`), ran 6 parallel research forks — market counterparts
per cluster + a self-audit of existing features against real aspirant needs — and cut it down to
one flagship mechanic (`PLAN-023`). Rahul then reframed the whole build: **optimize for his own
prep first, not the 95 existing signups** (DECIDE-42), kept the native S Pen/Apple Pencil canvas
in scope despite the research recommending against it (DECIDE-44 — he owns the exact hardware),
and scoped it across his full active exam portfolio. Full architecture in `PLAN-024`, including a
verified schema audit (no guessing) of all 6 attempt tables across 5 DBs.

**No code was written this session.** Everything below is architecture, not implementation.

**Read in order to resume:** `.knowledge/plans/PLAN-022.md` → `PLAN-023.md` → `PLAN-024.md`.
Decisions logged as DECIDE-41 through DECIDE-48 in `MASTER_INDEX.md`.

### Exact next step (S49 start here)
Implement PLAN-024 Phase 1: five additive migrations (`model_revealed`/`revealed_at`/
`input_mode` on `descriptive_attempts` ×3 DBs + `essay_attempts`; `ethics_attempts` already has
the first two) + an attempt-history timeline UI per question. Do NOT start on BUG-035's DB
cleanup or the canvas/vision-eval pipeline until Phase 1's migrations are confirmed working
locally — see PLAN-024's build sequence for why the order matters (canvas needs Phase 1's
`input_mode` column to exist first).

## 2026-08-30 — Cross-project data-provenance audit (read-only)

Audited as part of a 5-project data-sourcing audit (Recall/Scribe/Arena/law-model/content-pipeline)
toward Rahul's "one vetted, indexed data source across all Nyaya products" goal. No code changed
here. Full detail: `docs/audit/DATA_AUDIT_2026-08-30.md`. Cross-project synthesis + roadmap: memory
`project_nyaya_universal_data_layer.md`.

**Re-confirmed still open:** BUG-035 — 128/221 GS Mains PYQ rows (gs1-3) are scraped blog-comment
junk; gs4 (93 rows) is clean and is the only paper with model answers generated. No product anywhere
has a human-verification flag on AI-generated content — flagged as the real gap behind the
provenance-taxonomy work (`source_type` column, PLAN-011/021), not the access layer.

---

## 2026-08-29 — RBI cutover infrastructure merged (flag OFF, no live behavior change)

Devthorium/Recall became the canonical MCQ engine for RBI Grade B content (Nyaya Arena redesign — see Devthorium's `.knowledge/plans/PLAN-007/008/009.md`). This repo's RBI *content* (321 questions, 29 topic weights) was copied into Recall; `rbi_attempts`/`rbi_topic_mastery`/`rbi_key_data` all stay here, unchanged, under Scribe's own user identity — this app's live RBI feature is unaffected today.

**Merged (commit `73ff8ce`):** `RBI_CONTENT_SOURCE=local|recall` flag (defaulted `local` — zero behavior change while off), `migrations/m057_rbi_attempts_source_column.py` (additive, applies automatically via the app's normal migration runner on next start/deploy — not run manually against the live DB), `web/blueprints/_recall_client.py` (new thin HTTP client to Recall's internal API), `internal_api_bp.py` now proxies to Recall when the flag is `recall` (identical external shape, Arena needs zero changes).

**Not done, deliberately:** the flag has NOT been flipped to `recall` anywhere. That's a separate, later approval — needs local verification first per PLAN-008 §3's staged rollout, then an explicit decision from Rahul before touching live users.

**Blocking:** `INTERNAL_API_KEY_SCRIBE_RBI` — generate one value, put it in both this repo's and Devthorium's `.env`. Nothing calls Recall until this exists.

**Known gap, not a regression:** `get_filtered_questions`'s `is_trap`/`is_recent` filters have no equivalent in Recall's migrated schema yet — silently ignored in `recall` mode. Acceptable since the flag defaults off; revisit before ever flipping it.

## Active Work
UI-REDESIGN-001 Phase 2b — Photo eval (handwritten → Claude Vision scoring) ⏳ deferred
PLAN-017 Phase 2+ — GS Mains model answers (not yet generated; questions live on Railway now)

## Done This Session (S46)

### PLAN-018 Phase 4 — Essay AI Scoring ✅
- `web/blueprints/essay_bp.py` — added `_score_essay()` (claude-haiku-4-5, tool_use, 4-dim rubric: intro:20 + body:40 + ch_sol:20 + concl:20)
- `migrations/m051_essay_eval_gate.py` — adds `essay_eval` gate (15 free/month, unlimited pro)
- `essay_submit` route: gates on `essay_eval`, calls `_score_essay()`, stores `ai_score_json` + `ai_score_overall`, redirects with `attempt_id`
- `essay_detail` route: loads attempt scores when `attempt_id` in query
- `web/templates/essay_detail.html` — score breakdown card (overall badge + 4 color bars + feedback)
- Committed `77de724` + deployed to Railway

### BUG: upsc_gs.db content missing on Railway ✅ fixed (m052–m055)
- Root cause: ethics/essay/GS questions were seeded via scripts locally, never in migrations
- Railway had empty schema-only tables; all content was local-only
- `m052` — essay_frameworks, hook_types, theme_analysis, gs4_thinkers, 36 essay questions, 93 ethics questions
- `m053` — 36 essay model answers
- `m054` — 75 ethics model answers  
- `m055` — 221 GS Mains PYQ questions (gs1–gs4)
- All use `INSERT OR IGNORE` — idempotent
- Committed `db8f4bc` + `540172a`

### BUG: GS Mains showing Eco Optional content ✅ fixed
- `upsc_bp.py` (serves `/upsc/mains`) had `_EXAM_ID = "upsc_eco_opt"` + `g.upsc_conn` — completely wrong
- Fix: `_EXAM_ID = "upsc_gs_mains"`, `g.upsc_gs_conn`, paper defaults `gs1–gs4`
- Paper labels updated: GS Paper I–IV with subject labels
- `upsc_mains.html` title corrected

## Exact Next Step (S47 start here)

**Option A — UI Phase 2b: Photo eval**
- `POST /practice/submit-photo` — PIL compress → Claude Vision OCR + eval
- Template: add camera upload option to essay_detail.html or create separate route
- Spec: `.knowledge/plans/UI-REDESIGN-001.md` Phase 2b

**Option B — GS Mains model answers**
- 221 questions exist (gs1–gs4); 0 model answers
- Run batch generation script against upsc_gs.db (same pipeline as essay/ethics)
- See `scripts/generate_answers.py --exam upsc_gs_mains`

**Option C — AUDIT-008 index migrations**
- m047–m050 already committed (ies, eco_opt, english, rbi indexes)
- Verify Railway applied them; confirm with EXPLAIN QUERY PLAN

## Files Modified This Session (S46)
- `web/blueprints/essay_bp.py` — _score_essay() + gate wiring
- `web/blueprints/upsc_bp.py` — _EXAM_ID + conn fixed (GS Mains bug)
- `web/templates/essay_detail.html` — score breakdown card
- `web/templates/upsc_mains.html` — title fixed
- `migrations/m051_essay_eval_gate.py` — new
- `migrations/m052_seed_upsc_gs_questions.py` — new
- `migrations/m053_seed_essay_model_answers.py` — new
- `migrations/m054_seed_ethics_model_answers.py` — new
- `migrations/m055_seed_gs_mains_pyqs.py` — new
- `.knowledge/INDEX.md` — updated
- `.knowledge/plans/PLAN-018.md` — Phase 4 marked complete

## Pending Decisions
- DECIDE-32: Cross-DB topic linking (Y → master_topics; N → document only)
- DECIDE-33: rbi.db year column (Y → ALTER TABLE; N → keep is_recent_dev flag)

## Context Pointers
| Need | Read |
|---|---|
| Photo eval spec | .knowledge/plans/UI-REDESIGN-001.md Phase 2b |
| Essay scoring implementation | web/blueprints/essay_bp.py `_score_essay()` |
| Feature gate API | web/db.py `can_use_feature()` |
| GS Mains PYQ pipeline | .knowledge/plans/PLAN-017.md |
| Bug history | .knowledge/INDEX.md |
