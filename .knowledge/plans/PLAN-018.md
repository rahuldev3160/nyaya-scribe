# PLAN-018 — UPSC Essay Paper Module (Adaptive Architecture)
**Date:** 2026-06-21 (Session 43)
**Status:** PLANNING — awaiting research agent output before Phase 1

---

## Design Mandate

1. **No hardcoding** — essay count, year, framework assignments, hook types are all data, not code.
2. **Annual refresh** — adding next year's 15-20 essays = running 2 parameterized scripts. Zero code change.
3. **Post-exam PYQ ingestion** — actual Nov 2026 questions ingested after the exam; model answers generated same pipeline.
4. **Absorb any volume** — UI queries `SELECT * FROM essay_questions WHERE generation_year = ?`; adding 100 essays requires no template changes.

---

## Architecture Overview

```
ANNUAL CYCLE (data operations only, no code changes):

[April] CA Ingestion
  → admin adds to ca_events table (or /admin/ca/add route)

[May] Topic Inference
  → python scripts/essay/infer_topics.py --fy 2026 --count 25
  → writes essay_topic_proposals (status='pending')

[May] Human Review
  → admin reviews proposals at /admin/essay/proposals
  → marks status='approved' | 'rejected' | 'needs_edit'

[June] Batch Generation
  → python scripts/essay/generate_answers.py --batch-id B2026 --generation-year 2026
  → reads approved proposals → writes essay_questions + essay_model_answers

[Oct] Hot-flag
  → python scripts/essay/hotflag.py --year 2026 --min-prob 0.75
  → sets is_high_probability=1 on top topics

[Nov] Post-exam Ingestion
  → python scripts/essay/ingest_pyq.py --year 2026 --section A --q "..." --q "..."
  → inserts with content_type='pyq', year_appeared=2026

[Dec] Post-exam Model Answers
  → python scripts/essay/generate_answers.py --batch-id B2026_PYQ --pyq-year 2026
  → generates model answers for actual PYQ questions
```

---

## UI Structure — 3 subsections inside /upsc/essay

```
/upsc/essay                     → landing: 3-tab layout
  ├── tab: Practice Bank        → 20 generated questions (generation_year=2026)
  ├── tab: Solved Past Years    → 2024 + 2025 PYQ model answers (content_type='pyq')
  └── tab: Pattern Synthesis    → theme frequency map + backing for each topic choice

/upsc/essay/<essay_id>          → detail page (same template for all 3 types)
/upsc/essay/<essay_id>/submit   → attempt store + AI score
/upsc/essay/<essay_id>/model    → full model answer (freemium gate)
/upsc/essay/framework-guide     → static: PART A/B/C formula with examples
```

Navigation: UPSC tab toggle → "Eco Optional | GS Mains | Essay Paper"

---

## DB: upsc_gs.db (new tables via m039–m043)

### m039 — essay_theme_analysis (Pattern Synthesis backing data)

```sql
CREATE TABLE essay_theme_analysis (
    theme_tag           TEXT PRIMARY KEY,   -- 'values_ethics', 'technology', 'gender_justice', etc.
    theme_label         TEXT NOT NULL,      -- display: "Philosophy of Values & Ethics"
    frequency_count     INTEGER NOT NULL,   -- appearances 2014–2024
    typical_section     TEXT,              -- 'A', 'B', 'both'
    year_appearances    TEXT,              -- JSON: [2014, 2017, 2019, 2022, 2024]
    example_questions   TEXT,              -- JSON: [{"year":2024,"section":"A","prompt":"..."}]
    fy26_ca_hook        TEXT,              -- why this theme is hot in 2026 (1-2 sentences)
    trend               TEXT CHECK(trend IN ('rising','stable','declining')),
    probability_2026    TEXT CHECK(probability_2026 IN ('high','medium','low')),
    last_updated        TEXT DEFAULT (datetime('now'))
);
```

This table drives the "Pattern Synthesis" tab. Seeded from research findings. Updatable each year by running `scripts/essay/update_theme_analysis.py --year 2025`.

### m039 — essay_frameworks (registry, no hardcoding)

```sql
CREATE TABLE essay_frameworks (
    framework_id    TEXT PRIMARY KEY,   -- 'PESTLE', 'SPIDER', 'IDEA', 'PPF', 'CUSTOM'
    framework_name  TEXT NOT NULL,
    slots_json      TEXT NOT NULL,      -- JSON: [{"slot":"P","label":"Political","description":"..."}]
    best_for_themes TEXT,               -- JSON: ["governance","economy","technology"]
    typical_sections TEXT,             -- JSON: ["A","B"] or ["A"]
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

Seed on first run. Adding a new framework in 2027 = inserting one row. No code change.

### m039 — essay_hook_types (registry)

```sql
CREATE TABLE essay_hook_types (
    hook_type_id        TEXT PRIMARY KEY,  -- 'QUOTE','DATA','HISTORICAL_FACT','CONTEMPORARY','LITERARY','RHETORICAL_Q'
    label               TEXT NOT NULL,
    description         TEXT,
    example_template    TEXT,              -- e.g., "As [THINKER] once said, '[QUOTE]'"
    best_for_themes     TEXT,              -- JSON array of theme tags
    is_active           INTEGER DEFAULT 1
);
```

### m039 — essay_quotes (thinker/quote bank for hook generation)

```sql
CREATE TABLE essay_quotes (
    quote_id                TEXT PRIMARY KEY,
    thinker                 TEXT NOT NULL,
    quote_text              TEXT NOT NULL,
    context                 TEXT,
    theme_tags              TEXT,           -- JSON array: ["governance","integrity","society"]
    language                TEXT DEFAULT 'en',
    upsc_suitability_score  REAL DEFAULT 1.0,
    source                  TEXT
);
```

NOTE: `gs4_thinkers` already exists in upsc_gs.db and has `most_cited_quote`. Quote bank seeds from gs4_thinkers + additional non-ethics quotes. No duplication — essay_quotes is the lookup table for generation; gs4_thinkers is the GS4 study resource.

### m040 — essay_topic_proposals (annual inference queue)

```sql
CREATE TABLE essay_topic_proposals (
    proposal_id         TEXT PRIMARY KEY,
    proposed_prompt     TEXT NOT NULL,
    theme_tag           TEXT,
    section_guess       TEXT CHECK(section_guess IN ('A','B','unknown')),
    framework_suggestion TEXT REFERENCES essay_frameworks(framework_id),
    hook_suggestion     TEXT REFERENCES essay_hook_types(hook_type_id),
    probability_score   REAL,              -- 0.0–1.0, Claude-inferred
    ca_event_ids        TEXT,              -- JSON: ["ca_2025_...", "ca_2026_..."]
    generation_year     INTEGER NOT NULL,  -- which exam year this proposal targets
    inferred_by         TEXT DEFAULT 'claude-haiku-4-5-20251001',
    status              TEXT DEFAULT 'pending'
        CHECK(status IN ('pending','approved','rejected','needs_edit')),
    reviewer_notes      TEXT,
    reviewed_at         TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);
```

### m041 — essay_questions (finalized prompts)

```sql
CREATE TABLE essay_questions (
    essay_id            TEXT PRIMARY KEY,
    prompt              TEXT NOT NULL,
    section             TEXT CHECK(section IN ('A','B','unknown')),
    theme_tag           TEXT REFERENCES essay_theme_analysis(theme_tag),
    hook_type_id        TEXT REFERENCES essay_hook_types(hook_type_id),
    framework_id        TEXT REFERENCES essay_frameworks(framework_id),
    word_limit          INTEGER DEFAULT 1200,
    marks               INTEGER DEFAULT 125,
    year_appeared       INTEGER,           -- NULL = generated; non-NULL = actual PYQ year
    content_type        TEXT NOT NULL DEFAULT 'practice'
        CHECK(content_type IN ('practice','pyq','ca_generated')),
    generation_year     INTEGER NOT NULL,  -- which exam cycle (2026, 2027, 2028…)
    difficulty          TEXT CHECK(difficulty IN ('easy','medium','hard')),
    is_high_probability INTEGER DEFAULT 0, -- 1 = hotflagged pre-exam
    backing_note        TEXT,              -- shown in UI: "Chosen because [CA hook + frequency]"
    source_proposal_id  TEXT REFERENCES essay_topic_proposals(proposal_id),
    created_at          TEXT DEFAULT (datetime('now'))
);

-- normalized M:M: essay ↔ CA event
CREATE TABLE essay_ca_links (
    link_id         TEXT PRIMARY KEY,
    essay_id        TEXT NOT NULL REFERENCES essay_questions(essay_id) ON DELETE CASCADE,
    event_id        TEXT NOT NULL REFERENCES ca_events(event_id) ON DELETE CASCADE,
    relevance_score REAL DEFAULT 1.0,
    hook_usage      TEXT CHECK(hook_usage IN ('hook','evidence','both','context')),
    UNIQUE(essay_id, event_id)
);
```

### m042 — essay_model_answers (structured, indexed sub-parts)

```sql
CREATE TABLE essay_model_answers (
    answer_id           TEXT PRIMARY KEY,
    essay_id            TEXT NOT NULL REFERENCES essay_questions(essay_id),

    -- PART A: Introduction (4 indexed sub-parts)
    intro_hook          TEXT NOT NULL,     -- A1: opening line (quote/data/fact/etc.)
    intro_hook_type     TEXT NOT NULL,     -- which hook type was used
    intro_context       TEXT NOT NULL,     -- A2: context bridge (2-3 sentences)
    intro_thesis        TEXT NOT NULL,     -- A3: central argument (1 sentence)
    intro_signpost      TEXT NOT NULL,     -- A4: dimensions preview (1-2 sentences)

    -- PART B: Body (JSON for variable dimension count)
    body_dimensions_json TEXT NOT NULL,
    -- Schema of each element in the array:
    -- {
    --   "slot": "P",              -- framework slot letter/code
    --   "label": "Political",     -- display label
    --   "claim": "...",           -- B[D]1: one-sentence claim
    --   "evidence": "...",        -- B[D]2: data/case/scheme/CA event
    --   "analysis": "...",        -- B[D]3: implication / so-what
    --   "counter": "...",         -- B[D]4: opposing view
    --   "rebuttal": "..."         -- B[D]5: response to counter
    -- }
    body_challenges     TEXT NOT NULL,     -- dedicated challenges block
    body_solutions      TEXT NOT NULL,     -- dedicated solutions block
    body_synthesis_para TEXT,              -- optional balance paragraph

    -- PART C: Conclusion (4 indexed sub-parts)
    concl_synthesis     TEXT NOT NULL,     -- C1: thesis restated, deepened
    concl_way_forward   TEXT NOT NULL,     -- C2: 2-3 specific action steps
    concl_philosophical TEXT NOT NULL,     -- C3: universal/aspirational remark
    concl_closing_line  TEXT NOT NULL,     -- C4: memorable last line

    -- Metadata
    total_word_count    INTEGER,
    framework_id        TEXT REFERENCES essay_frameworks(framework_id),
    generation_model    TEXT DEFAULT 'claude-sonnet-4-6',
    batch_id            TEXT REFERENCES essay_generation_batches(batch_id),
    human_reviewed      INTEGER DEFAULT 0,
    reviewer_notes      TEXT,
    reviewed_at         TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);
```

### m042 — essay_generation_batches (run tracker)

```sql
CREATE TABLE essay_generation_batches (
    batch_id        TEXT PRIMARY KEY,  -- 'B2026_PRACTICE', 'B2026_PYQ', 'B2027_PRACTICE'
    batch_type      TEXT CHECK(batch_type IN ('practice','pyq','ca_refresh')),
    generation_year INTEGER NOT NULL,
    essay_count     INTEGER,
    model_used      TEXT,
    estimated_cost  REAL,
    status          TEXT DEFAULT 'pending'
        CHECK(status IN ('pending','running','complete','failed')),
    started_at      TEXT,
    completed_at    TEXT,
    notes           TEXT
);
```

### m043 — essay_attempts (user practice)

```sql
CREATE TABLE essay_attempts (
    attempt_id      TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    essay_id        TEXT NOT NULL REFERENCES essay_questions(essay_id),
    intro_text      TEXT,
    body_text       TEXT,
    conclusion_text TEXT,
    full_text       TEXT,
    word_count      INTEGER,
    ai_score_json   TEXT,              -- {intro_score,body_score,concl_score,overall,feedback}
    ai_score_overall REAL,
    attempt_type    TEXT DEFAULT 'timed'
        CHECK(attempt_type IN ('timed','open','post_exam')),
    submitted_at    TEXT DEFAULT (datetime('now'))
);
```

---

## Essay Framework: PART A / B / C Formula

### PART A — Introduction (150–180 words)

| Index | Sub-part | What goes here |
|-------|----------|----------------|
| A1 | Hook | ONE of: QUOTE / DATA / HISTORICAL_FACT / CONTEMPORARY / LITERARY / RHETORICAL_Q |
| A2 | Context bridge | 2–3 sentences: why this theme matters right now |
| A3 | Thesis | 1 sentence: your essay's central argument / position |
| A4 | Signpost | 1–2 sentences: dimensions you will cover |

### PART B — Body (650–750 words)

Each dimension block = 5 micro-moves:
| Move | Code | Content |
|------|------|---------|
| B[D]1 | CLAIM | One sentence: what this dimension reveals |
| B[D]2 | EVIDENCE | Data point / CA event / scheme / judgment / case |
| B[D]3 | ANALYSIS | "This means..." — the implication / so-what |
| B[D]4 | COUNTER | Opposing view: "Critics argue…" |
| B[D]5 | REBUTTAL | Response: "Yet…" / "However, this critique ignores…" |

Mandatory additional blocks (always present, separate from dimension slots):
| Block | Label | Content |
|-------|-------|---------|
| B-CH | CHALLENGES | Implementation gaps, structural barriers, political economy |
| B-SL | SOLUTIONS | Policy levers, institutional reforms, citizen agency — specific |
| B-SY | SYNTHESIS_PARA | Optional: holds the tension ("not X vs. Y, but…") |

### PART C — Conclusion (120–150 words)

| Index | Sub-part | What goes here |
|-------|----------|----------------|
| C1 | Synthesis | Thesis restated and deepened by body's evidence |
| C2 | Way forward | 2–3 concrete, specific action steps |
| C3 | Philosophical remark | Universal elevation: India's democratic journey / human civilization |
| C4 | Closing line | Memorable final line — quote echo from A1 OR original thought |

### Seeded Frameworks (essay_frameworks table)

| framework_id | Slots | Best for |
|---|---|---|
| PESTLE | P·E·S·T·L·E | Governance, economy, tech policy |
| SPIDER | S·P·I·D·E·R | Development, rights, society |
| IDEA | I·D·E·A | Philosophy, values, abstract essays |
| PPF | PAST·PRESENT·FUTURE | Historical continuity, heritage |
| INDIVIDUAL_SOCIETY | I·S | Ethics, character, governance essays |
| CUSTOM | (user-defined slots) | Any essay — admin sets slots via DB |

---

## Consolidated Batch Generation Plan

All model answers — practice questions + PYQ 2024 + PYQ 2025 — go in ONE Anthropic Batch API call.
This is the cheapest path: batch API gives 50% discount, and one large batch beats many small ones.

### Batch composition

| Group | Count | Source | content_type |
|---|---|---|---|
| Practice Bank (2026) | 20 | Curated question list (Phase 0 done) | `practice` |
| Solved 2024 | 8 | Research agent output (all 8 confirmed) | `pyq` |
| Solved 2025 | 8 | PYQ research agent (running) | `pyq` |
| **Total** | **36** | | |

### Prompt structure per call

Each batch item sends:
1. **System**: Essay framework spec (PART A/B/C formula, dimension block rules, word targets)
2. **User**: Essay prompt + assigned framework + assigned hook type + theme tag + CA event context (if any)
3. **Tool schema**: Structured JSON output enforcing exact field names matching `essay_model_answers` columns

Output JSON per call:
```json
{
  "intro_hook": "...",
  "intro_hook_type": "QUOTE",
  "intro_context": "...",
  "intro_thesis": "...",
  "intro_signpost": "...",
  "body_dimensions": [
    {"slot":"P","label":"Political","claim":"...","evidence":"...","analysis":"...","counter":"...","rebuttal":"..."},
    ...
  ],
  "body_challenges": "...",
  "body_solutions": "...",
  "body_synthesis_para": "...",
  "concl_synthesis": "...",
  "concl_way_forward": "...",
  "concl_philosophical": "...",
  "concl_closing_line": "..."
}
```

### PYQ model answers — framework assignment

PYQ questions (2024 + 2025) don't have pre-assigned frameworks — the script assigns them at batch-prep time based on theme_tag lookup in `essay_frameworks`. For Section A questions, default to IDEA or PPF. For Section B, default to PESTLE+ or SPIDER. Override is possible per-question via a seed file.

### Cost estimate

| Item | Input tokens | Output tokens | Cost (batch 50%) |
|---|---|---|---|
| Per call: system prompt + question prompt | ~1,200 | — | — |
| Per call: structured answer output | — | ~2,500 | — |
| 36 calls total | 36 × 1,200 = 43,200 | 36 × 2,500 = 90,000 | — |
| Sonnet 4.6 batch: $1.50/M in, $7.50/M out | $0.065 | $0.675 | **~$0.74 total** |
| With 2× safety buffer | | | **~$1.50** |

### Test-mode gate

`generate_answers.py --test-mode --count 2` runs 2 calls synchronously (not batch) before submitting the full 36. Validates output JSON shape. Only proceed to batch if test passes.

---

## Scripts (all parameterized)

```
scripts/essay/
├── seed_frameworks.py          # one-time: seeds essay_frameworks, essay_hook_types, essay_quotes,
│                               #           essay_theme_analysis (Pattern Synthesis data)
├── seed_questions.py           # inserts curated practice + PYQ questions from a JSONL seed file
│                               # --input data/essay_questions_seed.jsonl
│                               # (PYQ 2024 + 2025 + 20 practice all in one seed file)
├── generate_answers.py         # CONSOLIDATED batch: reads essay_questions with no model answer yet
│                               # --batch-id B2026_ALL --test-mode (runs 2 calls first, then full 36)
│                               # Handles practice + pyq in one call; framework assigned per question
├── infer_topics.py             # --fy 2027 --count 25 → reads ca_events → essay_topic_proposals
├── ingest_pyq.py               # post-exam: --year 2026 --section A --q "..." → pyq rows
├── hotflag.py                  # --year 2026 --min-prob 0.75 → sets is_high_probability=1
├── update_theme_analysis.py    # --year 2025 → updates essay_theme_analysis frequency counts
└── refresh_ca_links.py         # re-scores essay_ca_links after new ca_events rows added
```

### Seed file format (data/essay_questions_seed.jsonl)
One JSON object per line. Script inserts into `essay_questions` + `essay_ca_links`:
```jsonl
{"essay_id":"pyq_2024_a1","prompt":"Forest precedes civilization...","section":"A","theme_tag":"environment_civilization","content_type":"pyq","year_appeared":2024,"generation_year":2024,"framework_id":"PPF","hook_type_id":"LITERARY_REF","backing_note":null}
{"essay_id":"pyq_2024_b1","prompt":"Social media is triggering...","section":"B","theme_tag":"technology_society","content_type":"pyq","year_appeared":2024,"generation_year":2024,"framework_id":"PESTLE","hook_type_id":"DATA","backing_note":null}
{"essay_id":"prac_2026_01","prompt":"Power reveals character...","section":"A","theme_tag":"values_ethics","content_type":"practice","year_appeared":null,"generation_year":2026,"framework_id":"IDEA","hook_type_id":"QUOTE","is_high_probability":0,"backing_note":"Values+power theme has appeared 12 times in 10 years. Appears in both sections. The 2024 paper itself used a variant of this Lincoln quote in Section B — expect it to return in Section A in philosophical framing."}
```

All scripts share a common `--dry-run` flag. No script hardcodes year, count, or model.

---

## Blueprint + Routes

**File:** `web/blueprints/essay_bp.py`
**Registration:** `web/app.py` (same pattern as all existing blueprints)
**Connection:** uses `g.upsc_gs_conn` (already open in before_request for UPSC routes)

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/upsc/essay` | Landing: question bank browser (filter: year, section, theme, difficulty, type) |
| GET | `/upsc/essay/<essay_id>` | Detail: prompt + framework scaffold + collapsible model answer per sub-part |
| POST | `/upsc/essay/<essay_id>/submit` | Store attempt; gate: `can_use_feature(user_id, "essay_eval")` |
| GET | `/upsc/essay/<essay_id>/model` | Full model answer (freemium gate: recent years free) |
| GET | `/upsc/essay/pyq` | Actual past year questions: filter by year |
| GET | `/upsc/essay/framework-guide` | Static reference: PART A/B/C formula with examples |

**Navigation:** UPSC tab toggle becomes three options:
`Eco Optional | GS Mains | Essay Paper`
(Still CSS-MOB-001 compliant — toggle is within the tab page, not a 5th nav tab)

---

## AI Scoring Rubric (essay_eval feature gate)

| Dimension | Max pts | What is evaluated |
|-----------|---------|-------------------|
| Introduction quality | 20 | Hook effectiveness, thesis clarity, signposting |
| Body dimensions | 40 | Coverage, evidence quality, analytical depth, counter-argument handling |
| Challenges + Solutions | 20 | Specificity, feasibility, policy grounding |
| Conclusion | 20 | Synthesis quality, way forward actionability, memorable close |

Scoring function: `_score_essay()` in `essay_bp.py` — separate from `_score_answer()` in `ies_quiz_bp.py` because essay rubric is structurally different (section-based, not dimension-based).

---

## Freemium Gates

| Content | Free | Premium |
|---------|------|---------|
| Essay prompts (all years) | ✅ | ✅ |
| Framework guide (PART A/B/C) | ✅ | ✅ |
| Model answers — current year (generation_year = current) | ✅ Collapsed preview (intro only) | ✅ Full |
| Model answers — PYQ (year_appeared ≤ 2024) | ✅ Full | ✅ Full |
| AI scoring of attempts | ❌ (15 free/month via essay_eval gate) | ✅ Unlimited |
| Attempt history + scores | ✅ | ✅ |

---

## Phased Implementation

### Phase 0 — Research Complete ✅ (S43)
- [x] Paper format confirmed: 2 essays × 125 marks = 250 total, 3 hrs, Section A+B
- [x] 10-year PYQ list collected (2014–2024); theme frequency map built
- [x] FY25/FY26 CA → probable topic hooks mapped
- [x] 20 practice questions curated with framework + hook + backing_note assignments
- [x] 2024 essay paper (8 questions) confirmed from research agent 1
- [x] 2025 essay paper (8 questions) confirmed from official UPSC PDF (upsc.gov.in/ESSAY-QP-CSM-25-010925.pdf)

### 2024 Essay Paper Questions
**Section A:** (1) "Forest precedes civilization and the desert follows them." (2) "The empires of the future will be the empires of the mind." (3) "There is no path to happiness; happiness is the path." (4) "The doubter is a true man of science."
**Section B:** (1) Social media is triggering the 'Fear of Missing Out' amongst the youth, causing depression and loneliness. (2) Nearly all men can stand adversity, but to test a man's character, give him power. (3) "All ideas having large consequences are always simple." (4) The cost of being wrong is less than the cost of doing nothing.

### 2025 Essay Paper Questions (Source: official UPSC PDF — authoritative, no coaching site intermediary)
**Section A:** (1) Truth knows no color. (2) The supreme art of war is to subdue the enemy without fighting. (3) Thought finds a world and creates one also. (4) Best lessons are learnt through bitter experiences.
**Section B:** (1) Muddy water is best cleared by leaving it alone. (2) The years teach much which the days never know. (3) It is best to see life as a journey, not as a destination. (4) Contentment is natural wealth; luxury is artificial poverty.

**PATTERN ANOMALY — 2025:** All 8 questions were aphoristic/philosophical. Section B did NOT follow the usual contemporary/governance pattern. This is a departure from 2014–2024 norms. Implication: Section B is NOT reliably "contemporary" — the exam setter can go fully philosophical any year. Framework assignments for all 2025 PYQs default to IDEA/PPF, NOT PESTLE. Record this in `essay_theme_analysis.fy26_ca_hook` for the Section A/B distinction note.

### Framework assignments for 2025 PYQs
| Question | Framework | Hook type |
|---|---|---|
| A1: "Truth knows no color" | IDEA | HISTORICAL_FACT (civil rights, Satyagraha) |
| A2: "Supreme art of war — subdue without fighting" | IDEA | QUOTE (Sun Tzu, Chanakya) |
| A3: "Thought finds a world and creates one also" | PPF | LITERARY_REF (philosophy of idealism) |
| A4: "Best lessons from bitter experiences" | INDIVIDUAL_SOCIETY | HISTORICAL_FACT |
| B5: "Muddy water best cleared by leaving alone" | IDEA | LITERARY_REF (Taoism, ecological metaphor) |
| B6: "Years teach what days never know" | PPF | QUOTE (Emerson) |
| B7: "Life as journey, not destination" | IDEA | LITERARY_REF (Buddhist/Upanishad) |
| B8: "Contentment is natural wealth; luxury is artificial poverty" | PESTLE+ | QUOTE (Socrates + Gandhi) |

### Phase 1 — Schema + Seed (1 session)

**Migrations (upsc_gs.db, m039–m043):**
- [ ] `m039`: `essay_theme_analysis` + `essay_frameworks` + `essay_hook_types` + `essay_quotes`
- [ ] `m040`: `essay_topic_proposals`
- [ ] `m041`: `essay_questions` + `essay_ca_links`
- [ ] `m042`: `essay_model_answers` + `essay_generation_batches`
- [ ] `m043`: `essay_attempts`

**Seed data files:**
- [ ] `scripts/essay/seed_frameworks.py` — seeds 5 frameworks + 6 hook types + ~30 quotes (from gs4_thinkers) + 7 theme_analysis rows (from research)
- [ ] `data/essay_questions_seed.jsonl` — 36 questions total:
  - 8 PYQ 2024 (confirmed from research agent 1)
  - 8 PYQ 2025 (from research agent 2, pending)
  - 20 Practice 2026 (curated in Phase 0)
- [ ] `scripts/essay/seed_questions.py` — reads JSONL → inserts essay_questions rows
- [ ] Run all migrations + seeds locally; verify: `SELECT content_type, COUNT(*) FROM essay_questions GROUP BY content_type;` → 8 pyq 2024 + 8 pyq 2025 + 20 practice

### Phase 2 — Consolidated Batch Generation (1 session)

ONE Anthropic Batch API call for all 36 model answers (~$0.74, ~$1.50 with buffer):

- [ ] `scripts/essay/generate_answers.py` — build and validate
- [ ] Run `--test-mode --count 2` first: validate JSON output shape matches `essay_model_answers` columns
- [ ] Submit full batch: `--batch-id B2026_ALL` — 36 calls, all content types in one batch
- [ ] Poll for batch completion; insert results into `essay_model_answers`
- [ ] Spot-check: 1 Section A practice + 1 Section B practice + 1 PYQ 2024 + 1 PYQ 2025
- [ ] Mark `human_reviewed=1` on spot-checked rows; set `batch_status='complete'` in `essay_generation_batches`

### Phase 3 — Blueprint + Routes (1 session)
- [ ] `web/blueprints/essay_bp.py` — 6 routes (landing, detail, submit, model, pyq, framework-guide)
- [ ] Register in `web/app.py`; add `"essay_eval"` gate to feature_gates seed in m039 or separate migration
- [ ] UPSC tab: 3rd toggle state "Essay Paper" → `/upsc/essay` in `upsc_dashboard.html`
- [ ] `web/templates/essay_landing.html` — 3-tab layout:
  - Tab 1 "Practice Bank": filterable card grid (theme, section, difficulty, HIGH probability flag)
  - Tab 2 "Solved Past Years": year selector → 2024 | 2025; Section A/B split; all 8 questions per year
  - Tab 3 "Pattern Synthesis": theme frequency table + CA hooks + per-topic backing notes
- [ ] `web/templates/essay_detail.html` — prompt + PART A/B/C scaffold (framework guide as collapsible) + attempt editor + word count bar
- [ ] `web/templates/essay_model.html` — model answer with labeled sub-parts (A1/A2/A3/A4, B-P/B-E/B-S…, B-CH/B-SL, C1/C2/C3/C4) + color-coded by section

### Phase 4 — AI Scoring (1 session)
- [ ] `_score_essay()` in `essay_bp.py` — 4-part rubric (intro:20 + body:40 + challenges+solutions:20 + concl:20)
- [ ] Gate: `can_use_feature(user_id, "essay_eval")`
- [ ] Store: `essay_attempts.ai_score_json` + `ai_score_overall`
- [ ] Post-submit: score breakdown card (one row per dimension, color bar)

### Phase 5 — Admin + Annual Pipeline (future)
- [ ] `/admin/essay/proposals` — review queue for `essay_topic_proposals`
- [ ] `scripts/essay/infer_topics.py` — CA → proposals (for 2027 cycle)
- [ ] `scripts/essay/ingest_pyq.py` — post-exam CLI (for Nov 2026 actual paper)
- [ ] `scripts/essay/update_theme_analysis.py --year 2025` — update frequency counts after new PYQ added
- [ ] Document annual refresh runbook

---

## Indexing Layer (added S43 — enables multi-dimensional lookup)

All questions and answers are indexed so they can be located by: year · section · theme · thinker · CA event · content type · generation year · difficulty · probability flag.

### Junction tables (normalized M:M — replaces JSON blobs for tags)

```sql
-- essay_questions ↔ gs4_thinkers (thinker cited in essay prompt or model answer)
CREATE TABLE essay_thinker_links (
    link_id     TEXT PRIMARY KEY,
    essay_id    TEXT NOT NULL REFERENCES essay_questions(essay_id) ON DELETE CASCADE,
    thinker_id  TEXT NOT NULL REFERENCES gs4_thinkers(thinker_id),
    usage_type  TEXT CHECK(usage_type IN ('hook','body','conclusion','quote')),
    UNIQUE(essay_id, thinker_id)
);
-- (essay_ca_links already exists — essay_questions ↔ ca_events)
```

### SQLite indexes on essay_questions

```sql
CREATE INDEX idx_essay_year    ON essay_questions(year_appeared);
CREATE INDEX idx_essay_section ON essay_questions(section);
CREATE INDEX idx_essay_theme   ON essay_questions(theme_tag);
CREATE INDEX idx_essay_type    ON essay_questions(content_type, generation_year);
CREATE INDEX idx_essay_hot     ON essay_questions(is_high_probability, section);
CREATE INDEX idx_essay_diff    ON essay_questions(difficulty);
```

### FTS5 for full-text search

```sql
CREATE VIRTUAL TABLE essay_fts USING fts5(
    essay_id UNINDEXED,
    prompt,
    backing_note,
    content='essay_questions', content_rowid='rowid'
);
CREATE VIRTUAL TABLE essay_answer_fts USING fts5(
    answer_id UNINDEXED,
    intro_hook, intro_thesis, body_challenges, body_solutions, concl_closing_line,
    content='essay_model_answers', content_rowid='rowid'
);
```

### Blueprint query helpers (essay_bp.py)

```python
# Lookup by theme (e.g., all "technology" essays)
SELECT eq.* FROM essay_questions eq WHERE eq.theme_tag = ? ORDER BY year_appeared DESC

# Lookup by year (e.g., all 2024 PYQs)
SELECT eq.* FROM essay_questions eq WHERE eq.year_appeared = ? ORDER BY section, essay_id

# Lookup by thinker (e.g., all essays that cite Gandhi)
SELECT eq.* FROM essay_questions eq
JOIN essay_thinker_links etl ON etl.essay_id = eq.essay_id
WHERE etl.thinker_id = ? ORDER BY year_appeared DESC

# Lookup by CA event (e.g., all essays hooked to "Operation Sindoor")
SELECT eq.* FROM essay_questions eq
JOIN essay_ca_links ecl ON ecl.essay_id = eq.essay_id
WHERE ecl.event_id = ?

# Full-text search (e.g., "artificial intelligence")
SELECT eq.* FROM essay_questions eq
JOIN essay_fts ON essay_fts.essay_id = eq.essay_id
WHERE essay_fts MATCH ?

# High-probability filter (pre-exam mode)
SELECT * FROM essay_questions WHERE is_high_probability=1 ORDER BY section, theme_tag

# Annual cohort (e.g., all 2026 practice questions)
SELECT * FROM essay_questions WHERE content_type='practice' AND generation_year=2026
```

All indexes and junction tables added in **m041** (alongside essay_questions). FTS tables in **m042** (alongside model answers — built after answer text is populated).

## Key Constraints (Change Impact Map)

| Constraint | Rule |
|---|---|
| SYNC-001 | `essay_bp` uses `g.upsc_gs_conn` — opened in before_request alongside `g.upsc_conn`. No new connection key needed. |
| JINJA2-001 | No template variable named `items`, `keys`, `values`, `get`. Use `essay_rows`, `dimension_entries`, `proposal_entries`. |
| CSS-MOB-001 | Essay Paper = 3rd toggle state WITHIN the UPSC tab, not a 5th bottom nav tab. 4-tab mobile grid stays intact. |
| feature_gates | `essay_eval` gate added to `m035_feature_gates.py` seed (or a new `m039` adds it to the existing feature_gates table). |
| Cross-DB joins | `essay_attempts` stores `user_id` text — lookup against `nyaya.db users` table uses Python-merge pattern (same as feedback_bp.py). |

---

## Research Findings (S43 — agent a40764f8231f65169)

### Paper Format — CONFIRMED
- 2 essays, 3 hours, 250 marks total, 125 per essay
- 4 choices per section; write 1 from Section A + 1 from Section B
- Section A: philosophical/abstract/values; Section B: contemporary/society/governance
- ~1000–1200 words per essay (no hard cap in official notification; consistent across 2014–2024)
- Format unchanged since the Section A/B split was introduced circa 2013–2014

### Theme Frequency (2014–2024)
| Theme | Count | Section |
|---|---|---|
| Philosophy of values / ethics / good life | 12 | A dominant |
| Technology: promise, peril, displacement | 9 | Both |
| Gender justice, women empowerment, patriarchy | 7 | B dominant |
| Education: purpose, reform, values | 6 | Both |
| Economy: growth, inequality, inclusion | 6 | B |
| Governance: federalism, institutions | 5 | B |
| Nature, environment, civilization | 5 | Both |

### Curated Question List (20 questions — Phase 0 complete)

| # | Prompt (abbreviated) | Section | Theme | Framework | Hook |
|---|---|---|---|---|---|
| Q01 | "Power reveals character — examine through democratic institutions, bureaucracy, leadership" | A/B | Values+governance | IDEA | QUOTE (embedded in prompt) |
| Q02 | "Best for individual ≠ best for society — where does virtue end and responsibility begin?" | A | Ethics+social contract | INDIVIDUAL_SOCIETY | HISTORICAL_FACT |
| Q03 | "Technology has not replaced our search for meaning — it has outsourced it" | A | Tech+values | PESTLE+ | DATA |
| Q04 | "When we lose a forest, we lose the grammar of civilization" | A | Environment+philosophy | PPF | LITERARY_REF |
| Q05 | "In an age of algorithms, the doubter is the last free man" | A | Truth+epistemic freedom | IDEA | RHETORICAL_Q |
| Q06 | "Wantlessness is Utopian; materialism a chimera — the sustainable life lies between" | A | Economic philosophy+ethics | PESTLE+ | QUOTE (Gandhi) |
| Q07 | "Women's Reservation Act gives women seats — but does it give them power?" | B | Gender+political rep | SPIDER | DATA |
| Q08 | "Can India become Viksit Bharat 2047 while 300 million remain in poverty?" | B | Development+inequality | PESTLE+ | DATA |
| Q09 | "AI is democracy's greatest promise and most dangerous threat — simultaneously" | B | AI+democracy+governance | PESTLE+ | CONTEMPORARY |
| Q10 | "Climate change is not an environmental problem — it is a civilizational test" | A/B | Climate justice+equity | SPIDER | DATA |
| Q11 | "Cooperative federalism is India's constitutional grammar — competitive politics is the language spoken" | B | Federalism+governance | PESTLE+ | HISTORICAL_FACT |
| Q12 | "In a world of tariff walls, economic self-reliance is not protectionism — it is survival" | B | Trade+sovereignty | PESTLE+ | CONTEMPORARY |
| Q13 | "A nation's right to protect its citizens can never fully justify the violence it unleashes in their name" | A/B | Security+ethics of force | IDEA | HISTORICAL_FACT |
| Q14 | "An institution that loses its integrity cannot restore it by reforming its rankings" | B | Education+accountability | IDEA | CONTEMPORARY |
| Q15 | "In a post-truth world, a free press is not a luxury of democracy — it is its precondition" | B | Media+democracy | SPIDER | QUOTE (Jefferson) |
| Q16 | "Space exploration is not a flight from earthly problems — it is a civilized state's highest ambition" | A | Science+national aspiration | PPF | CONTEMPORARY |
| Q17 | "A society that has more justice is a society that needs less charity" | B | Social justice+welfare | SPIDER | QUOTE (MLK) |
| Q18 | "The digital economy promised to be the great leveller — the divide it created is deeper than the one it closed" | B | Digital+inequality | PESTLE+ | DATA |
| Q19 | "India's Non-Alignment was born of one world order — today's multipolar chaos demands a new strategic doctrine" | B | Geopolitics+strategic autonomy | PESTLE+ | HISTORICAL_FACT |
| Q20 | "Simplicity is the ultimate sophistication — but who still dares to choose less in the age of AI?" | A | Values+modernity | IDEA | QUOTE (da Vinci) |

High-probability for Nov 2026 (CA-hooked, HIGH): Q7, Q8, Q9, Q10, Q11, Q12, Q13

## Dangerous Assumptions (Rule 3)

1. ~~**"UPSC essay paper is 2 essays × 125 marks, 3 hours"**~~ — **CONFIRMED** by research agent (CivilServiceIndia, IASBaba). Safe to seed `marks=125, total=250`.
2. **"PESTLE is appropriate for Section A philosophy essays"** — RESOLVED by using IDEA/INDIVIDUAL_SOCIETY/PPF for Section A questions (Q01, Q02, Q04, Q05, Q06, Q13, Q16, Q20). PESTLE assigned only to Section B and dual-section questions. Framework assignment is per-question data — fixable without code change.
3. **"Sonnet generates 1000-word structured essays reliably in JSON tool-use format"** — Still unverified. Add `--test-mode --count 2` flag to `generate_answers.py`; validate output shape before full batch.

---

## Status
- [x] Phase 0: Research complete (S43) — paper format confirmed; 2024 + 2025 PYQs verified (16 questions); 20 practice questions curated; all 36 assigned frameworks + hooks; 2025 pattern anomaly documented
- [x] Phase 1: Schema + seed complete (S44) — m039–m043 applied; 36 questions seeded
- [x] Phase 2: Content generation complete (S45) — 36/36 model answers in DB via Batch API
- [x] Phase 3: Blueprint + templates complete (S45) — essay_bp.py (5 routes) + essay_landing.html, essay_detail.html, essay_framework.html; UPSC 4-item toggle wired
- [ ] Phase 4: AI scoring — _score_essay() + essay_eval gate (15 free/month)
- [ ] Phase 5: Admin + annual pipeline
