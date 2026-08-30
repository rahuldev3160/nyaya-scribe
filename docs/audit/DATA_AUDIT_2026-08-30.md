# Scribe Data Audit — 2026-08-30

## 1. Data inventory (real DB files, `data/`, verified via `.env`-free direct check — no DB_PATH override in `.env`)

| DB | Key tables | Counts |
|---|---|---|
| `ies.db` | pyq_questions / model_answers / mcqs | 1,219 / 1,219 / ~150 |
| `upsc_eco_opt.db` | pyq_questions / model_answers / topics / source_documents | 908 / 908 / 81 / ~111 |
| `upsc_gs.db` | pyq_questions (gs1:62,gs2:29,gs3:37,gs4:93=221) / model_answers | 221 / **81** (gs4 only) |
| `rbi.db` | rbi_questions, rbi_attempts, rbi_english_sim_attempts (new) | not row-counted (MCQ-shaped, no pyq_questions table) |
| `english.db` | english_questions, english_question_types | separate small DB |
| `nyaya.db` | canonical identity+event store | auth/users/events only |
| `data/notebooklm/` | 4 stale RBI source files (Jun 3) | manual-export snapshot, not live pipeline |
| `scripts/notebooklm_prompts/` | 36 topic-grouped `.txt` files (IES GE01-04 + RBI) | source material for manual NotebookLM upload |

Six `railway-backup-20260829/*.db` files exist (yesterday's prod backup) — not separately audited, mirror the above.

## 2. Provenance — major finding: Phase-1 provenance system already built TODAY (unprompted, same day as this audit)

A same-day, not-yet-fully-applied initiative (`PLAN-021` Area 6, companion to Recall's `PLAN-011`) added a `source_type TEXT` column (`official_pyq` / `ai_generated` / `coaching_derived` / `self_notes` — same enum Recall uses) to `pyq_questions`/`model_answers` in `ies.db`, `upsc_eco_opt.db`, `upsc_gs.db` via migrations m059–m063. **Verified applied to local dev copies** (not just proposed): `ies.db` → 1,219 `official_pyq`; `upsc_eco_opt.db` → 903 `official_pyq` + 5 `coaching_derived`; `upsc_gs.db` → 81 `official_pyq` (the clean gs4 rows) + **140 left NULL** (the BUG-035-contaminated gs1-3 rows + 12 additional gs4 junk rows found in a fuller re-scan — deliberately NOT backfilled as official). `rbi.db`/`english.db` migrations (m060, m063) exist but those DBs have no `pyq_questions` table by that name, so applicability there wasn't verified. Model answers are 100% `ai_generated` (Claude Sonnet 4-6 per PLAN-021, IES) — this is the correct AI-generation label but there's no separate "verified by Rahul" flag anywhere; verification status is not tracked at all today, anywhere in Scribe.

**BUG-035 re-verified, still fully OPEN, unchanged since 2026-07-06:** live-sampled `upsc_gs.db` gs1 rows today — literally scraper artifacts ("Topicwise Sorted Questions... without any mobile registration", "[Download] Topicwise UPSC GSM2..."), confirming the bug is real and current, not stale. A fuller re-scan (documented in PLAN-021, done today) also found 12 more junk rows inside the previously-"clean" gs4 set and excluded them before generating the 81 gs4 model answers — so today's work is corrective, not naive.

## 3. Indexing / schema health
No FTS5 full-text index anywhere (flagged, not built — AUDIT-008). Standard integer PKs + indexes exist per m047–m050 (missing-index fixes already landed). No open schema-drift bugs beyond BUG-035. 23 stale `.claude/worktrees/agent-*` git worktrees exist at repo root (untracked in git status but present on disk) — cosmetic clutter, not a data issue, worth `git worktree prune` at some point but out of scope here.

## 4. NotebookLM content pipeline — manual, not automated
`scripts/export_for_notebooklm.py` dumps IES PYQ+model-answers to plain-text files grouped by paper/topic (`scripts/notebooklm_prompts/*.txt`, 36 files, IES GE01–04 + RBI topics). This is a **one-shot manual export** — no scheduler, no trigger, no automated hand-off to NotebookLM or to the YouTube pipeline. Rahul (or a prior session) runs the script, then manually feeds the `.txt` files into NotebookLM's UI. `data/notebooklm/` (4 files, last touched Jun 3) is the leftover output of that manual process for RBI only — IES/UPSC-GS topic exports exist as prompt files but no corresponding NotebookLM output snapshot was found, suggesting the IES batch was prepared but not yet run through NotebookLM, or the output wasn't saved back to this repo.

## 5. Universal-data-source angle
- Same 4-value provenance enum as Recall (`official_pyq`/`ai_generated`/`coaching_derived`/`self_notes`) — intentionally shared vocabulary, confirmed in PLAN-021 text, so a future unified view doesn't need enum reconciliation.
- **No cross-product identity or content merge exists or is planned near-term.** Arena's `DECIDE-02`/`DECIDE-09` and this project's `AUDIT-008` `DECIDE-32` explicitly keep Recall/Scribe/Arena as three disjoint identity spaces; Arena reads Scribe via an internal API contract (`X-Internal-Api-Key` pattern), never raw DB access — but that API (`/internal/scores`) is **not yet built**, only named/planned (Arena's HANDOFF confirms nothing implemented).
- Overlap with Recall: none at the content level (Scribe=Mains descriptive, Recall=Prelims MCQ) beyond the shared provenance taxonomy and a proposed (not built) read-only "Mains attempted this month" card on Recall's dashboard calling into Scribe.
- `nyaya.db` is the one real piece of shared infrastructure today — canonical identity+events — but scoped to Scribe only, not shared across products.

## 6. Gap list
| Gap | Source needed |
|---|---|
| GS1-3 PYQs (128 rows) are scraper junk (BUG-035) | Re-scrape from real upsc.gov.in Mains PYQ PDFs — official source, not AI |
| GS1-3 model answers (0 rows, blocked by above) | AI-generate only after BUG-035 fixed |
| GS1-4 PYQ coverage (221 of ~800 expected) | Official upsc.gov.in PDFs |
| Ethics 18 questions missing model answers | AI-generate (same pipeline as the 75 done) |
| No "Rahul-verified" flag on any AI-generated content | New schema field — decision needed, not sourcing |
| `/internal/scores` API for Arena | Build (deferred — this is implementation, not data) |
| NotebookLM export → posting pipeline has no automation | Build (deferred, Part B) |
| RBI/English `pyq_questions`-equivalent provenance tagging | Needs table-name mapping in a follow-up migration; not yet done |
