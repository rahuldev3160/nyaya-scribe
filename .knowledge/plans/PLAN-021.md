---
id: PLAN-021
type: plan
project: descriptive-exams
date: 2026-08-30
status: PROPOSED — research/proposal only, nothing built, nothing run, nothing migrated
---

# PLAN-021: 2027 retarget, real Mains practice loop, RBI English timed-writing, provenance Phase 1 (Scribe half)

**Scope note.** Pure research and proposal. No code, migration, or paid API content-generation
call was executed to produce this. Companion document: Devthorium's
`.knowledge/plans/PLAN-011.md` covers Recall's half (areas 1, 2, 5, and Recall's half of area 6).
Read both together — area 6 only makes sense as one cross-repo taxonomy.

**Constraints respected:** Scribe is live with ~95 real paying users on Railway. Every schema
change proposed below is additive (new nullable column / new table), never destructive, and
every `ALTER TABLE` on an existing live table is explicitly flagged as needing Rahul's approval
per this project's own CLAUDE.md gate rule. Rahul is doing CLC DU 1st semester concurrently with
2027 prep — sizes below are set against that bandwidth, not unlimited dev time.

---

## Area 1 — Exam-year retargeting

### External verification (web search, 2026-08-30 — not assumed)

No structural pattern change confirmed for RBI Grade B or IES for the 2027 cycle (see PLAN-011
for the same finding on UPSC, shared context). RBI Grade B Phase 2 English Descriptive paper
confirmed as **100 marks total, 90 minutes, three components: Essay + Précis Writing + Reading
Comprehension** — no office-note/business-letter component exists (corrects an assumption in the
original research brief). **The exact per-section mark split is unconfirmed** — a prior pass on
this research asserted Essay(40)/Précis(30)/RC(30), a since-suggested "correction" asserted
RC(40)/Essay(30)/Précis(30), and neither is actually backed by an official source: rechecking
against RBI's own notification language plus Oliveboard's and Adda247's exam-pattern pages found
only the 100-mark/90-minute aggregate, no official component-level breakdown. Coaching blogs
disagree with each other on the split. Treat it as unresolved rather than pin Area 4's design to
either unverified number.

### Concrete hardcodes found (grep, current repo state)

| Location | Issue |
|---|---|
| `web/blueprints/rbi_prep_bp.py:20`, `web/blueprints/rbi_dashboard_bp.py:18` | Both independently hardcode `RBI_DATE = "2026-06-14"`, feeding the exam countdown shown on both the prep and dashboard pages. Needs the real 2027 Phase 1 date once notified, and ideally consolidated to one source instead of two independently-hardcoded copies. |
| `web/blueprints/essay_bp.py:185` | `where_clauses.append("q.generation_year = 2026")` — hardcodes which cycle's 20 practice essays are shown. This directly contradicts DECIDE-25's own stated design intent ("annual refresh must be a data operation... adding 2027 essays = 2 script runs, zero code change") — the WHERE clause itself is the code-level hardcode that breaks that promise. Needs to read the active cycle from config, not a literal year. |
| `data/essay_questions_seed.jsonl` / `scripts/essay/seed_questions.py` | The 20 practice essays are tagged to the 2026 cycle — a fresh 2027 practice batch is a data operation (per DECIDE-25), not a code change, once the `essay_bp.py:185` hardcode above is fixed. |

No hardcoded IES or UPSC-GS-Mains exam dates were found (`setup_bp.py`'s plan generator takes
`days_to_exam` as a parameter, not a constant).

### Recommendation

**Small.** Fix the two `RBI_DATE` constants (consolidate to one, e.g. a shared config value
rather than two independent literals — this is the kind of drift DECIDE-24 already warns about
for schema columns, and the same discipline applies to constants), fix `essay_bp.py:185` to read
the active cycle instead of a literal year, then run a 2027 essay-seed batch once that's fixed.
No approval gate — none of this touches existing user data.

**DONE 2026-08-30 (partial, by design).** Consolidated both `RBI_DATE` literals into a new
`web/exam_dates.py` — worth noting the *old* hardcoded date (2026-06-14) was already showing a
negative countdown to live users today, independent of the 2027 push, since that date is now in
the past. Set to a provisional `2027-06-15` estimate (flagged in-file as pending RBI's real
notification) rather than leaving the stale/past value live. `essay_bp.py`'s `generation_year`
filter now reads `ACTIVE_PRACTICE_ESSAY_CYCLE` (env var, defaults to 2026) instead of a literal —
but **intentionally left at 2026 for now**: flipping it to 2027 before any 2027-tagged practice
essays exist would show zero essays to today's live users. The "run a 2027 essay-seed batch"
step above is the actual trigger to bump this env var — treat them as one paired change, not two
independent ones.

---

## Area 3 — UPSC Mains build-out: what's actually built vs. planned

### Verified against real code and real DB content (not docs, which the brief warned may be stale)

**Routes ARE live and wired**, contrary to what "Phase 3 pending" might suggest in isolation:
- `/upsc/mains` (`web/blueprints/upsc_bp.py`) — GS1–4 PYQ browse with self-compare.
- `/upsc/essay`, `/upsc/essay/pyq`, `/upsc/essay/<id>`, `/upsc/essay/<id>/submit`
  (`essay_bp.py`, 446 lines, includes real AI scoring via `_score_essay`).
- `/upsc/ethics`, `/upsc/ethics/<paper_id>`, `/upsc/ethics/<paper_id>/q/<question_id>`
  (`ethics_paper_bp.py`, 262 lines, self-compare only, matching DECIDE-28's design).
- `g.upsc_gs_conn` is wired into `web/app.py`'s before_request/teardown (the "PENDING" status in
  an old HANDOFF snapshot is stale — this is done).

Note: PLAN-017 originally specced separate `gs_dashboard_bp`/`gs_quiz_bp`/`gs4_ethics_bp` files;
in the actual implementation this was folded into `upsc_bp.py`/`upsc_dashboard_bp.py`/
`essay_bp.py`/`ethics_paper_bp.py` instead. That's a simplification, not a gap — just means the
docs' filenames are stale, not the functionality.

**Content, by real row count (`data/upsc_gs.db`):**

| Table | Count | Note |
|---|---|---|
| `pyq_questions` (GS1–4) | 221 (gs1:62, gs2:29, gs3:37, gs4:93) | RISK-01's flagged gap vs. ~800 expected, still open |
| `model_answers` (for those 221) | **0** | Self-compare has nothing to compare against for any GS1–4 PYQ |
| `essay_questions` / `essay_model_answers` | 36 / 36 | Fully paired, matches DECIDE-27/31 |
| `ethics_questions` / `ethics_model_answers` | 93 / 75 | 18 questions short an answer |
| `topics` | 163 | gs1:51, gs2:41, gs3:42, gs4:29 |

**Usage — the real headline finding:** `descriptive_attempts`, `gap_states`, `user_mastery`,
`essay_attempts`, `ethics_attempts` are **all 0** in `upsc_gs.db`. Zero recorded practice
activity anywhere in this module since it shipped. This is not "half-built" — it's "built enough
to click through, essentially never actually used."

### Recommendation: turn idle plumbing into a real, connected loop

**Medium.** In priority order:

1. **Generate `model_answers` for the 221 existing GS1–3 PYQs.** This is the single highest-
   leverage fix — the content-generation pipeline and batch pattern already exist (same one used
   for essay/ethics, DECIDE-27) and self-compare is structurally useless without it. This is a
   paid API content-generation call and needs Rahul's go-ahead on cost/timing (not a schema
   approval gate, just a spend decision) before it's actually run.
2. **A small cross-repo continuity signal, not a merged database.** Recall (Prelims) and Scribe
   (Mains) have three deliberately disjoint identity spaces (Arena's DECIDE-02, this project's
   own AUDIT-008 DECIDE-32 still pending) — don't reopen that. The cheap, real fix: Recall's
   dashboard gets one small read-only card ("Mains: N GS-Mains questions attempted this month")
   via a tiny internal-API call to Scribe, reusing the exact `X-Internal-Api-Key` pattern Arena
   already established (PLAN-008/PLAN-011's Area 6). This keeps Rahul's Prelims-mode dashboard
   from silently letting Mains readiness go to zero, without merging user models or reopening
   DECIDE-32/33.
3. **Backfill the GS1–3 PYQ coverage gap** (221 → closer to ~800) from official upsc.gov.in
   PDFs, per RISK-01's own already-stated mitigation — mechanical sourcing work, not a design
   problem.
4. **Defer:** RISK-02's topic_id L1-fallback refinement (178/221 questions on fallback tagging)
   — a navigation/discoverability quality issue, not a blocker for a first working loop.

No new blueprints, no new schema — the infrastructure exists and is idle. This is a content and
connection problem, not an engineering one.

---

## Area 4 — RBI Grade B English paper: timed-writing feature

### Verified real paper structure (web search, corrects an assumption in the original brief)

Phase II English Descriptive: **100 marks total, 90 minutes, three components — Essay, Précis
Writing, and Reading Comprehension.** There is no separate office-note/business-letter section.
The exact per-section mark split is unconfirmed (see Area 1) — official sources give only the
aggregate. The defining difficulty isn't any one section — it's three distinct writing/reading
tasks sharing a single hard 90-minute budget, which matches Rahul's actual 2026 failure exactly:
could not complete in time, not a content gap.

### What exists today to build on

Nothing. `grep` for `setInterval`/`countdown`/`Timer` across `web/static/` returns zero results
— Scribe has no client-side timer infrastructure anywhere. This is a genuinely new build, not an
extension of an existing feature (Recall's exam-sim timer, in the sibling repo, is a pattern
worth referencing but is not reusable code across the two codebases).

### Recommendation

**Medium.** A new `rbi_english_sim` mode:

1. **Fixed real structure, single 90-minute master countdown** plus a visible per-section
   sub-budget. Since the official per-section mark split isn't confirmed (Area 1), don't hard-code
   a weighting derived from a disputed number — default to an even-ish split (e.g. 30/30/30 across
   the three sections) and make it editable, or better, let Rahul set his own split once from
   direct experience with a real past paper. The timer visually flags when a section runs over
   budget without necessarily force-cutting it, since
   the training goal is to make the cost visible, not just to replicate the exam's hard stop.
   (Worth a direct one-line question to Rahul at build time: should it hard-cut per section like
   the real exam, or just warn? Either is small to build; it's a training-philosophy choice, not
   an engineering one.)
2. **Typing-pace measurement — the actual missing signal.** Sample word count client-side every
   ~15s, show a live words/min readout, and produce a post-submission pacing report (e.g. "you
   started your Essay conclusion with 2 minutes left"). This directly targets the confirmed
   failure mode (completion-under-time-pressure), kept **visually and numerically separate** from
   Scribe's existing content-quality AI scoring (DECIDE-21's 5-dimension rubric) — Rahul's real
   gap was time, not quality, and blending the two signals would hide that.
3. **Reuse `_score_essay`'s scoring pipeline** (DECIDE-37's precedent: the scoring function is
   already exam-agnostic in structure) for an optional, separate quality pass on the essay
   portion — not required to use the timer/pacing feature.

Scope: new client-side JS (genuinely new) + one new small table for session/section timings,
additive only. No changes to any existing `rbi.db` MCQ table — no approval gate needed for this
feature on its own.

---

## Area 6 — Content provenance taxonomy (Scribe's half)

### What exists today, verified column-by-column

No DB has an explicit `source_type`/provenance column. What looks like one on inspection turns
out to mean something else: `rbi_attempts.source` = `'local'` vs `'recall'` — a **routing flag**
(which backend served the question, per PLAN-008's cutover flag), not content provenance.
Typing today is purely implicit by table name: `pyq_questions` = official-ish PYQ,
`model_answers` = AI-generated — with no explicit column, and **no self-notes/coaching-material
distinction anywhere** (Scribe has no user-authored-notes feature at all, unlike Recall's
`session_user_notes`).

### Recommendation

**Medium** (higher than Recall's side, because it requires a real schema change on live tables).

1. Add one new nullable `source_type TEXT` column, additively, to `pyq_questions` and
   `model_answers` in each of the five exam DBs (`ies.db`, `rbi.db`, `upsc_eco_opt.db`,
   `upsc_gs.db`, `english.db`), using the same 4-category enum as Recall's Phase 1
   (`official_pyq` | `ai_generated` | `coaching_derived` | `self_notes`) — deliberately the same
   vocabulary as PLAN-011's Recall side, not a separate taxonomy, so a future cross-product view
   (if Rahul ever revisits DECIDE-32) doesn't have to reconcile two different enums.
2. Backfill sensibly on migration: `pyq_questions` rows → `official_pyq` by default (already
   sourced from official PDFs per DECIDE-05/38's sourcing discipline), `model_answers` rows →
   `ai_generated` by default (all currently AI-batch-generated, per DECIDE-27).
3. **This is an `ALTER TABLE` across five live production databases with real user data — flag
   to Rahul explicitly for approval before running, batched as one migration set (one ask, not
   five), per this project's CLAUDE.md gate rule.** Purely additive (new nullable column,
   sensible default backfill) — no existing column type, constraint, or data is touched.

### Earlier feasibility-study trace (see PLAN-011 for the full cross-repo version)

No document named exactly "unified cross-product database feasibility study" was found. The
closest real prior art is this project's own `AUDIT-008` (2026-06-21), which already surveyed
all 6 DBs' schema conventions and flagged **DECIDE-32** (should "Monetary Policy" in IES/RBI
point to a canonical `master_topics` entity in `nyaya.db`?) as pending — still unanswered.
Nyaya-Arena's `DECIDE-02`/`DECIDE-09` independently concluded Recall/Scribe/Arena have three
deliberately disjoint identity spaces, and any shared table needs cross-product identity linking
solved first — explicitly out of scope here. **This provenance taxonomy does not touch that
question at all** — it's the same column shape replicated into each product's own database, not
a merged database or a shared identity space. It's explicitly Phase 1 of the larger idea, and the
immediate payoff is Recall's Area 2 mock mode being able to report an honest PYQ-vs-AI split —
Scribe's own dashboards could eventually show the same "how much of what you practiced was
verified vs. AI-approximated" signal, but that's a follow-on, not part of this Phase 1 ask.

---

## Suggested build order — combined across both repos

Given Rahul's bandwidth (law school + 2027 prep simultaneously), here is the full 7-step order
across both PLAN-011 and PLAN-021, sequenced by (a) cheapness, (b) how much lead time a fix
needs before its exam, and (c) what actually cost him something in 2026:

1. **Area 1, both repos** (small) — one sitting, fix all hardcoded years/dates first so nothing
   else gets built against a stale baseline.
2. **Area 5** (small, Recall-filed) — IES dashboard usage-nudge; near-zero cost, directly targets
   a confirmed real failure (non-use, not content).
3. **Area 6, Recall half** (small) — run the already-designed backfill on Recall's own DB.
4. **Area 3** (medium, this file) — generate GS1–3 model answers + the Recall↔Scribe readiness
   card. Start early: this is 2026's biggest strategic gap (zero Mains prep at all), and content
   generation + habit-building both need lead time before Mains (Aug 2027).
5. **Area 2** (medium, PLAN-011) — Recall's Full Mock mode, sequenced after step 3 so it can
   honestly report its PYQ-vs-AI fraction from day one. The core fix for Prelims (May 2027).
6. **Area 4** (medium, this file) — RBI English timed-writing simulation. Plenty of runway before
   RBI Grade B 2027 Phase 2 (~July 2027); sequenced after Prelims/Mains work since those exams
   come first chronologically.
7. **Area 6, Scribe half** (medium) — the five-DB `ALTER TABLE` batch. Deferred last: highest
   friction (one approval ask across five live DBs) and lowest urgency; bundle it with whichever
   other Scribe migration is already in flight at that point (e.g. area 3's or area 4's own
   migrations) to minimize the number of separate approval asks Rahul has to review.

No Docker migration is proposed as urgent for Scribe — it's already live and healthy on Railway
(per HANDOFF S39); the existing `Dockerfile`/portability package stays readiness-only, referenced
by PLAN-011 as the pattern Recall could mirror later, not something this plan asks Scribe itself
to redo.
