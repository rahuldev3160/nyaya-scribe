---
id: PLAN-023
type: plan
project: descriptive-exams
date: 2026-09-02
status: PROPOSED — supersedes PLAN-022's phasing after market research; awaiting Rahul's build call
---

# PLAN-023: Scribe feature cut — market-validated, "few but significant"

## Method
PLAN-022 broke Rahul's handwritten notes into 10 feature clusters. Per Rahul's instruction —
"less is better... few features, but each should add significantly" — 6 parallel research forks
went and found the best real-world counterpart for each cluster, mapped its actual architecture,
and separately audited Scribe's *already-live* features against what serious aspirants report
actually needing. This doc applies that evidence to cut the list hard. Full per-cluster findings
are condensed below; nothing here is speculation — every verdict traces to a cited competitor or
a cited evidence source (see each fork's sources, summarized inline).

## Existing-feature audit (fork 6)
**Diagnosis on AUDIT-007 (95 signups, ~0 engagement) revised:** not primarily an onboarding/UX
problem — S39–41 already spent a full redesign pass on exactly that (hero strips, stat pills,
readiness states) and engagement stayed at zero afterward. The evidence now points to "built
things aspirants don't fully want."

- **Keep:** typed answer + dimensional AI scoring (IES/Essay/Ethics/Eco-Optional). Necessary
  baseline — but AI mains-evaluation is now a *commodity* (PrepAiro, Dalvoy, upsc.ai, Acme AI,
  IntelGrader all ship near-identical "instant AI feedback"). Keep it running; stop treating it as
  a differentiator.
- **Keep, low priority:** PYQ browsing by exam/topic — required scaffolding, not a value driver
  on its own.
- **Stop investing:** dashboards/progress tracking (hero strips, stat pills, readiness states) —
  already tested against real users with zero engagement lift. Polishing this further is solving
  a problem that isn't the bottleneck.
- **Reconsider:** the 15-free-evals/month quota. Serious aspirants target **300–500 practice
  answers over a prep cycle**, starting at 2–3/day (SuperKalam's own aspirant-facing strategy
  content, aimed at this exact audience). A 15/month ceiling actively works against the volume
  the market says matters — worth revisiting the gate's placement, independent of the feature
  work below.
- **Not an engagement question:** GS Mains is broken (BUG-035) — a data-integrity fix, already
  decided.
- **What's actually missing**, per aspirant-facing evidence: comparison against real topper
  copies to understand *why* an answer scores well (not just a number), and a peer/mentor
  accountability loop. Neither exists in the current build. This is the gap the recommendation
  below targets directly.

## Per-cluster market findings → verdict

| Cluster (PLAN-022 #) | Best market counterpart(s) | Architecture found | Verdict |
|---|---|---|---|
| Model-answer format (#4, format half) | Prayas AI, SuperKalam, PrepBaba, UPSC.AI | Intro/Body/Conclusion, AI-graded on 15+ structure/content/clarity parameters, <60s–20min turnaround | **Table stakes.** Everyone does this. Scribe already has it for IES/Essay/Ethics. No differentiation available here — don't over-invest in format polish. |
| Pre-attempt→feedback→model-answer (#5, first half) | PrepBaba, UPSC Answer Check, UPSC.AI, EduBolt | Write blind → AI score → shown model answer, benchmarked against topper-level responses | **Table stakes**, already standard mid-tier-competitor behavior. |
| **Re-attempt-after-seeing-model-answer + compare** (#5, second half) | *None found.* Every competitor stops at attempt→feedback→model-answer. | — | **Genuinely differentiated.** No competitor surfaces a second write-and-compare step. This is real whitespace. |
| **Topper-copy-grounded model answers** (#4, sourcing half) | deepmentor (only real precedent found) | Corpus of "annotated topper copies" feeds both the evaluator and answer generation | **Genuinely differentiated**, and independently confirmed by fork 6 as the specific thing aspirants say is missing ("why does this score well," not just a score). Only one weak competitor precedent exists — real whitespace. |
| Handwriting input: photo-upload (#3) | SuperKalam (200K+ users, market leader), Prayas AI | Write on paper → photograph/scan → vision-model OCR+eval, 20–60s | **Validated, ship it.** Matches the market leader's proven approach *and* matches real exam conditions (paper + pen). This is Scribe's already-deferred Phase 2b — the research says prioritize it, not skip it. |
| Handwriting input: native stylus canvas (#3) | *None found among UPSC competitors.* GoodNotes/Notability do native ink but have zero AI-eval loop. | Native canvas needs a whole stroke-capture/rendering subsystem *in addition to* the same downstream vision-eval call photo-upload already needs — pure added cost, no removed step | **Cut.** No competitor precedent, no evidence aspirants want to write 200–250-word Mains answers with a stylus in-app rather than on paper (which is what they do on exam day anyway). Redundant with photo-upload. |
| Engagement/nudge engine (#9) | Anki heatmap, Duolingo streaks, Habitica | Streaks/gamification measurably improve outcomes (g≈0.5–0.8) — **but only when layered onto behavior users already do.** "Streak creep" research: for users with no prior habit, streak mechanics backfire — streak-break causes abandonment rather than restart. | **Cut, and flagged as actively risky.** Scribe's 95 users have never formed the underlying behavior (confirmed activation failure, not content scarcity). Bolting on streaks now manufactures a new failure mode on top of an unsolved one. Revisit only *after* the core loop below is proven with a real cohort. |
| Trend analysis / 80:20 topics + Fact Sheet (#7) | Vision IAS VAM, Legacy IAS, Lukmaan IAS | Static subject-wise fact PDFs and topic-frequency writeups, freely available and mirrored across 6+ sites | **Cut as scoped.** Fully commoditized — every serious aspirant already has these bookmarked. Only defensible version is a *dynamic, personalized* layer keyed to a user's own weak topics/attempt history — a materially different and harder feature, not worth building now. |
| Deep PYQ indexing — subtopic/marks/interlinkage (#1, #8) | Notion/Obsidian DIY aspirant setups, PYQKosh, Anantam IAS, LotusArise | Real aspirant tagging tops out at Year/Paper/Topic/Difficulty/Status — topic is the deepest granularity anyone actually productizes or uses day-to-day | **Cut for now.** Topic+Year+Exam covers ~90%+ of real filtering behavior. Defer subtopic/marks/interlinkage until usage data shows the simple filter's ceiling. |
| Personal derived views / notes-in-place (#6, #8) | Notion views, Obsidian backlinks | Non-destructive filtered/sorted views over one shared dataset — exactly what Rahul's notes describe — already solved, off-the-shelf, widely adopted by aspirants who build this themselves | **Cut as a Scribe feature.** Aspirants already have Notion/Obsidian for this; it's not Scribe's fight to win. |
| Terminology/concepts sub-boxes (#6) | — (not independently researched; small, low-evidence ask) | — | **Fold in, don't build separately.** If kept at all, make it a section inside the model-answer display, not a new subsystem. |
| Framework/approach box, e.g. PESTLE (#10) | — (no market validation found) | — | **Cut.** No evidence found either way; smallest, least-justified item on the original list. |

## Recommendation: one flagship feature, not ten

Collapsing clusters #3 (photo input), #4 (topper-grounded generation), and #5 (re-attempt +
compare) into a single integrated loop — because the market research shows they're not separable
wins on their own, they're three parts of the one mechanic that's actually differentiated:

**"Topper-Grounded Compare Loop"**
1. User attempts a question blind — typed today, **photo-upload of a handwritten answer** once
   Phase 2b ships (validated path, not native canvas).
2. Existing AI scoring engine grades it (already built — keep, don't rebuild).
3. User sees a model answer explicitly **grounded in real topper-copy patterns**, annotated with
   *why* specific structural/content choices score well — not just "here's the model answer."
4. User re-attempts the **same question** after seeing it.
5. Both attempts shown side-by-side so the user sees their own before/after — the specific step
   no competitor offers.

This is the only item on the whole list that is simultaneously (a) confirmed as real market
whitespace, (b) independently confirmed by the self-audit as the specific thing aspirants say is
missing, and (c) buildable without new indexing depth, gamification, or a community system.

**What it requires that isn't yet built:**
- Photo-upload handwritten input (UI-REDESIGN-001 Phase 2b — deferred, now validated as worth
  prioritizing)
- Real topper-copy ingestion (PLAN-022 Phase C data-sourcing track — genuinely new pipeline, no
  shortcut around it)
- BUG-035 resolved for GS Mains specifically (already decided: drop junk rows, re-source) — the
  loop is worthless on questions that aren't real

**Explicitly not building right now:** native stylus canvas, nudge/streak engine, generic trend
analysis + fact sheets, deep PYQ indexing, standalone personal-notes box, framework/approach box,
further dashboard investment.

**Flagged, not a feature decision:** the 15/month eval quota may be undermining the exact
practice-volume the market says matters (300–500 answers/cycle). Worth Rahul's separate call.

## Supersedes
PLAN-022's Phase A/B/C/D structure is replaced by this single-loop recommendation for what to
build next; PLAN-022 remains the source record for the original 10-cluster breakdown and BUG-035
decision log.
