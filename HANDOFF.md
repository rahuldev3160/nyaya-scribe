# Handoff — Nyaya Scribe (Descriptive Exams)
**Session:** S49 → S50 | 2026-09-16 | Branch: `feature/attempt-flow-gs-eco` (not merged to main)

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
