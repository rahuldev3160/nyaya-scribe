---
id: PLAN-022
type: plan
project: descriptive-exams
date: 2026-09-02
status: PROPOSED — synthesis of Rahul's handwritten notes, not yet approved/sequenced
---

# PLAN-022: Scribe Feature Roadmap — synthesis of Rahul's handwritten notes

## Source
`~/Downloads/SCRIBE - NYAYA_260902_203138.pdf` — 14-page handwritten note, transcribed and
organized 2026-09-02. Original is a stream-of-consciousness feature brainstorm across UI,
AI-generation, and data-sourcing. This doc groups it into 10 clusters and cross-checks each
against current build state (`HANDOFF.md`, `.knowledge/INDEX.md`, `PLAN-021`) so nothing gets
re-planned that already exists, and BUG-035 (open since S47) isn't silently re-triggered.

## Feature Clusters

### 1. PYQ retrieval & filtering — PARTIAL
Notes ask: filter/retract PYQs by year, subject, topic, subtopic, marks, exam ("plus more if I
missed something"). Exam-id/paper/topic filtering exists across ies/upsc/essay/ethics blueprints
today. Marks-wise and subtopic-wise filtering not confirmed uniform. Cross-exam (State PCS)
filtering is new. Same underlying need as cluster 8.

### 2. Practice question sources — PARTIAL, gated by BUG-035
Notes ask: UPSC PYQs, State PCS PYQs, other UPSC-similar exams (IES/RBI already covered),
AI-generated (tagged). IES/Essay/Ethics/Eco-Optional are real and sourced. **GS Mains gs1–gs3
(128/221 rows) are scraped blog-comment junk — BUG-035, OPEN since 2026-07-06, re-confirmed
2026-08-30, still no decision from Rahul.** State PCS PYQs aren't sourced anywhere — net-new
ingestion. The provenance enum (`official_pyq`/`ai_generated`/`coaching_derived`/`self_notes`)
already exists in schema (PLAN-021) — "AI-generated (tagged)" is already representable at the
data layer, just needs a UI filter surfaced.

### 3. Answer input modalities — PARTIAL
Typed = live. Photo upload of a handwritten answer = UI-REDESIGN-001 Phase 2b, deferred
(DECIDE-32/33 open since June). A true in-browser drawing canvas (Apple Pencil / S-Pen native
strokes, not a photo) is a materially bigger ask than photo-eval — new scope, not a rename of
the deferred item.

### 4. Model-answer generation engine — PARTIAL, gated by BUG-035 + new sources
Notes ask: Intro/Body/Way-forward/Conclusion format, precise language, current-affairs
integration, base-material grounding, topper-copy-informed style (bullets, diagrams, flowcharts,
examples to substantiate). `_score_answer`/`_score_essay` already do forced-tool-use Haiku 4.5
scoring for IES/Essay. GS Mains has 0 model answers — correctly blocked by BUG-035. "Topper's
copies" as a source has no ingestion pipeline anywhere in the 5-project stack (confirmed against
the Nyaya Ledger audit) — entirely new.

### 5. Pre/post-attempt compare box — **NEW, no blockers**
"For every model answer/PYQ: a section to attempt the question before reading the model answer,
and again after" — writable via pencil/pen/typed/photo either way. Nothing equivalent exists
today. This is the most concrete, self-contained, immediately-buildable item in the whole note —
works against any exam that already has real model answers (IES, Essay, Ethics, GS4), doesn't
touch BUG-035 at all.

### 6. Solution box restructure — PARTIAL
Notes ask: full exam-style solution + a separate box for important terminology + a box for
important concepts asked/used (brief explanation + definition) + the practice box from #5 + the
box doubles as the user's personal note-taking space. `essay_detail.html` already has a
score-breakdown card and per-exam model-answer display; terminology/concepts sub-boxes and
inline personal notes are new UI layered on existing pages.

### 7. FYI box & Fact Sheet — **NEW**
FYI = trend analysis (frequently-asked topics, 80:20 rule) + current events (PIB / other public
source, tagged static-vs-dynamic) + official govt communications mapped to the UPSC syllabus
breakdown. Fact Sheet = subject-wise crucial facts (constitutional provisions, economic data,
historical facts, geography/technical data). Nothing built. Frequency analysis is computable
today from existing PYQ year/topic columns for the exams with clean data; meaningless for
GS1–3 until BUG-035 is resolved. Fact Sheet's closest existing analogue is `upsc_eco_opt`'s
`economic_data_points` table (129 rows) — same pattern generalizes.

### 8. Data labelling / indexing architecture — validates existing direction, one new requirement
Index by year/exam/subject/topic/subtopic/marks/interlinkages; user can retrieve & manipulate a
**derived view without altering the original data**; new questions/papers integrate easily. This
is the same direction as PLAN-021's provenance taxonomy and the cross-project "Nyaya Ledger" goal
already in memory (`project_nyaya_universal_data_layer`) — no new decision needed on the indexing
side. The one genuinely new requirement: a personal, non-destructive derived/filtered question
set per user (closest existing analogue is #6's personal-notes idea, but not the same thing).

### 9. Engagement / nudge engine — **NEW, high strategic relevance**
Track days on platform, hours spent, questions attempted, % syllabus complete; motivational nudge
quotes (e.g. "1 question a day, 10 minutes = 365 in a year"). `nyaya.db` already logs
`user_events` (page_view etc.) — the tracking substrate exists. AUDIT-007 (2026-06-13, still the
last word on this) found the real crisis is engagement, not content: 95 signed-up users, ~0
engagement. This cluster is a direct, purpose-built response to that still-open finding — higher
leverage than most content work right now.

### 10. General approach / framework box — **NEW, small**
Generic problem-solving frameworks (e.g. PESTLE) explained briefly with examples — teaching
approach, not just supplying answer content. Small, self-contained, no data dependency.

## Dependency map
Clusters 2 and 4 — real GS Mains PYQs + model answers, State PCS ingestion, topper-copy
ingestion, current-affairs pipeline, and the "80:20 topics" half of #7 — all sit behind the same
unresolved blocker: **BUG-035, open 2 months, with an explicit decision request to Rahul that has
never been answered** (re-scrape gs1–3 from a real UPSC PYQ source, or drop the 128 contaminated
rows and re-source). Clusters 5, 6, 9, 10, and the Fact-Sheet half of #7 do **not** depend on it
and can ship today against clean content (IES, Essay, Ethics, GS4).

## Proposed phasing (draft — sequencing is Rahul's call)

**Phase A — ships today, no new data needed**
- #5 Pre/post-attempt compare box (highest leverage : scope ratio)
- #9 Nudge/engagement engine (answers the still-open AUDIT-007 finding directly)
- #6 Solution-box restructure (terminology + concepts sub-boxes, inline personal notes)
- #10 Framework/approach box

**Phase B — needs BUG-035 resolved first**
- #2/#4 real GS Mains PYQs + model answers
- #7 FYI trend box (80:20 frequency analysis is meaningless on junk data)

**Phase C — new multi-session data-sourcing pipelines**
- State PCS PYQ ingestion
- Topper's-copy ingestion + style inference
- Current-affairs (PIB/RBI/Parliament) structured ingestion
- Fact Sheet content build (subject-wise)

**Phase D — bigger engineering lift**
- Native Apple Pencil / S-Pen drawing canvas (distinct from, and larger than, the already-deferred
  photo-eval item)

## Decisions
1. **BUG-035 (2026-09-02):** drop the 128 contaminated gs1/gs2/gs3 rows now; re-source real
   gs1–3 content separately (Phase C, alongside State PCS + topper's-copy ingestion). Not yet
   executed — deleting from a live production DB with real users needs its own implementation
   pass (FK/cascade check on any attempts referencing these rows), not done inline in this
   planning session. See `bugs/BUG-035.md`.
2. Phase A (compare box, nudge engine, solution box, framework box) has no dependency on the
   above and can start immediately, in parallel with the BUG-035 cleanup.
