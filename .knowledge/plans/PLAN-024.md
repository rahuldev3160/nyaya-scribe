---
id: PLAN-024
type: plan
project: descriptive-exams
date: 2026-09-02
status: PROPOSED — architecture for personal-use build, awaiting topper-copy sourcing decision
---

# PLAN-024: Personal-first build — Topper-Grounded Compare Loop + native canvas, full exam portfolio

## Reframe
Supersedes PLAN-023's "optimize for the 95 signups" framing for this build. Primary and only
target user for this work is Rahul, using it for his own live prep, on his own devices (Galaxy
S26 Ultra — S Pen, iPad — Apple Pencil). Applies across the full portfolio he's actively working:
GS Mains (GS1–4), Essay, Ethics, IES, RBI, Eco-Optional. One mechanic, built once, mounted
everywhere — not six separate features.

## Attempt-table audit (verified against actual migrations, not assumed)

| Exam | DB | Table | Has attempt-context flag? | Notes |
|---|---|---|---|---|
| IES | `ies.db` | `descriptive_attempts` | No | `attempt_id` PK, no unique constraint on (user,question) — already supports unlimited attempts over time |
| Eco-Optional | `upsc_eco_opt.db` | `descriptive_attempts` | No | Same shape as IES's copy |
| GS Mains (GS1–4) | `upsc_gs.db` | `descriptive_attempts` | No | Same shape again |
| Essay | `upsc_gs.db` | `essay_attempts` | No | Has `attempt_type` (`timed`/`open`/`post_exam`) — a different axis, not model-reveal |
| Ethics (GS4) | `upsc_gs.db` | `ethics_attempts` | **Yes — `model_revealed` INTEGER + `revealed_at`** | Already the exact field this whole plan needs. Standardize the name across every other table. |
| RBI (English descriptive) | `rbi.db` | `rbi_english_sim_attempts` | No | Different shape entirely — a single 90-min timed simulator row across Essay+Précis+RC, not per-question drilling. See flag below. |
| English | `english.db` | `english_attempts` | No | Keyword-scored, not AI-graded like the others |

All descriptive-attempt tables (except RBI's simulator) are already append-only per
(user_id, question_id) with no uniqueness constraint — the backend already supports the
"attempt this question again weeks later" pattern with zero core redesign. This is additive
work, not a rebuild.

## Architecture

**A. Standardize attempt-context tracking**
Add `model_revealed INTEGER DEFAULT 0` + `revealed_at TEXT` (matching Ethics's existing pattern)
and a new `input_mode TEXT DEFAULT 'typed'` (`typed`/`photo`/`canvas`) to: `descriptive_attempts`
(×3 DBs), `essay_attempts`. Five small additive migrations, same pattern each time, no ALTER on
data that changes meaning of existing rows.

**B. Native canvas — one shared component**
HTML5 `<canvas>` + Pointer Events API captures stroke position, pressure, and tilt natively for
both S Pen (Chrome/Android, `pointerType:'pen'`) and Apple Pencil (Safari/iPadOS, supported since
iOS 13.4). No native app needed — Scribe is already a responsive Flask web app on Railway,
reachable from both devices' browsers. Build this as one reusable JS module mounted into every
exam's answer-attempt template, not six bespoke implementations. Needs: undo/clear, multi-page
support (real Mains answers run several physical pages — one canvas "page" per image export).

**C. Unify the submit path**
UI-REDESIGN-001's already-spec'd `POST /practice/submit-photo` (PIL compress → Claude Vision
OCR+eval) becomes the single backend target for both a camera photo AND a canvas export
(rasterized to PNG client-side) — same downstream pipeline, generalized to accept an `input_mode`
param instead of assuming "photo." Canvas doesn't need its own eval logic; it needs its own
capture UI in front of the same eval call. This also means building canvas effectively builds
Phase 2b photo-upload at the same time — the two were never separable wins, confirming PLAN-023's
earlier read even under the personal-use reframe.

**D. Topper-grounded model answers — gated, see open item below**
`model_answers.critique_json` already exists as a slot — extend it (or add `why_annotations`) to
hold structural/stylistic reasoning extracted from real topper copies, fed into the
model-answer-generation prompt so answers are grounded in what actually scores well, not just
generically well-formatted.

**E. Spaced-repetition surfacing — reuse, don't rebuild**
The existing `inferred_state` machine (UNVISITED/FLAGGED/IN_STUDY/VERIFIED/DECAYING, from
BUG-026/027) already tracks staleness per topic. A DECAYING question is functionally "due for
reattempt" — wire the compare-loop's "come back to this one" surfacing through that existing
state machine rather than inventing separate scheduling logic.

**F. RBI flagged separately, not folded in identically**
`rbi_english_sim_attempts` is a single 90-minute timed full-mock (Essay+Précis+RC together), not
a per-question drill table like the others. The blind→reveal→reattempt loop doesn't map onto a
timed simulator format the same way. If RBI needs this pattern, it likely needs its own
untimed per-prompt practice mode distinct from the simulator — a smaller follow-on decision, not
assumed here.

## Build sequence
1. **Schema** — 5 additive migrations (model_revealed/revealed_at/input_mode, matching Ethics's
   existing pattern) + attempt-history timeline UI (per-question view of every past attempt,
   score, and whether the model answer had been seen).
   **Migrations DONE 2026-09-16** (`migrations/m066`-`m070`): `descriptive_attempts` on
   ies/upsc_eco_opt/upsc_gs, `essay_attempts` on upsc_gs, and `input_mode` added to
   `ethics_attempts` (which already had `model_revealed`/`revealed_at` from m046). Verified via
   `scripts/migrate.py` + `PRAGMA table_info` on all 5 tables. The "5 migrations" count wasn't
   explicit anywhere before this — it resolves to 4 full 3-column migrations + 1 partial
   (ethics_attempts). **Attempt-history timeline UI not yet built** — no route/layout/component
   spec exists anywhere in this plan; needs a decision before building (dedicated page vs. mounted
   on existing per-exam detail templates; one shared component vs. per-exam, matching the "one
   shared mechanic" principle used for canvas below).
2. **Canvas + unified submit + vision eval** — delivers native S Pen/Apple Pencil input and
   photo-upload together, since they share one pipeline.
3. **Topper-grounded generation** — gated on sourcing (see below).
4. **GS Mains gs1–3** joins once BUG-035's decided cleanup (drop 128 junk rows, re-source) is
   executed — PLAN-022/BUG-035, unchanged by this plan.
5. **RBI** — separate decision once 1–3 are working elsewhere; not blocking them.

## Decision (2026-09-02)
Topper-copy sourcing deferred. Phases 1–2 (schema + attempt-history UI, canvas + unified submit +
vision eval) proceed without it. Phase 3 (topper-grounded generation) stays blocked until Rahul
either supplies source material or asks for acquisition research — not scheduled yet.
