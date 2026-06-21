# PLAN-019 — UPSC Ethics Paper Module (GS4 Paper Simulation)
**Date:** 2026-06-21 (Session 43)
**Status:** PLANNING — research agents running (Section A + Section B parallel)

---

## Scope

This plan covers the **GS4 Ethics paper simulation layer** — past year solved papers + 2 practice papers + pattern synthesis. This is distinct from PLAN-017's GS4 topic-study system (concept browser, return quiz, thinker directory). These two layers are complementary:

| Layer | Plan | What it does |
|---|---|---|
| Study mode | PLAN-017 Phase 5 | Concept mastery, keyword index, return quiz tiers, thinker directory |
| Paper simulation | PLAN-019 (this) | Full-paper practice, past year model answers, pattern synthesis |

---

## GS4 Paper Structure (confirmed)

| Parameter | Value |
|---|---|
| Total marks | 250 |
| Time | 3 hours |
| Section A — Theory | ~125 marks (12–15 questions, mixed marks) |
| Section B — Case Studies | ~125 marks (3–4 cases, 20–25 marks each) |
| Section A question types | 2-mark (define), 5-mark (short), 10-mark (medium), 12.5/15-mark (analytical) |
| Section B question types | Case preamble + 2–3 sub-parts (a/b/c) per case |
| AI scoring | DISABLED — self-compare only (no objectively correct answer in ethics) |

---

## Two Answer Frameworks (the product's IP)

### Framework 1: IDEA-U (Section A — Theory Questions)

For questions like "What is emotional intelligence? How does it help civil servants?" (10 marks):

| Step | Code | What to write |
|---|---|---|
| Define | **I** — Introduce | One-sentence definition + thinker attribution (Aristotle on virtue, Goleman on EI, etc.) |
| Dimensions | **D** — Dimensions | 3–4 facets of the concept (individual / institutional / systemic / philosophical) |
| Evidence | **E** — Exemplify | One Indian governance example + one historical/global reference |
| Apply | **A** — Apply to civil service | How does this manifest in the role of a public servant? What does it demand of an IAS officer? |
| Upshot | **U** — Upshot | What goes wrong when this value is absent? What governance failure does it prevent? |

**Word targets by mark value:**
| Marks | Word target | Steps used |
|---|---|---|
| 2 | 30–50 | I only |
| 5 | 80–100 | I + D |
| 10 | 150–180 | Full IDEA-U |
| 12.5–15 | 200–250 | Full IDEA-U + counterargument + way forward |

### Framework 2: STAKE (Section B — Case Studies)

For case studies presenting a practical ethical dilemma faced by a civil servant:

| Step | Code | What to write |
|---|---|---|
| Stakeholders | **S** — Stakeholders | Map all parties + their interests, rights, vulnerabilities |
| Tension | **T** — Core tension | Name the fundamental ethical conflict (duty vs. compassion / rules vs. outcomes / loyalty vs. integrity) |
| Analysis | **A** — Apply frameworks | Run the case through 2–3 ethical lenses: Kantian duty → Utilitarian consequences → Virtue ethics → Constitutional values |
| Key decision | **K** — Recommended action | One clear, justified choice — the most constitutionally defensible option |
| Execution | **E** — Implementation + learning | Immediate steps (what to do NOW) + medium-term (follow-up, reporting, systemic fix) + institutional learning (what does this case demand of the system?) |

**STAKE sub-parts map to case study sub-questions:**
- Sub-part (a) "Identify ethical issues" → **S + T** steps
- Sub-part (b) "What would you do and why?" → **A + K** steps
- Sub-part (c) "What steps would you take?" → **E** step

This means even when sub-parts vary in phrasing, the student always applies the full STAKE framework and excerpts the right parts for each sub-part.

---

## DB Schema — new tables in upsc_gs.db (m044–m046)

### m044 — ethics_questions

```sql
CREATE TABLE ethics_questions (
    question_id     TEXT PRIMARY KEY,        -- 'ethics_pyq_2024_a01', 'ethics_prac_p1_a01'
    paper_year      INTEGER,                 -- 2024, 2025, NULL=practice
    paper_id        TEXT,                    -- 'ethics_pyq_2024', 'ethics_pyq_2025', 'ethics_prac_1', 'ethics_prac_2'
    section         TEXT NOT NULL CHECK(section IN ('A','B')),
    question_type   TEXT NOT NULL
        CHECK(question_type IN ('definition','short','medium','analytical','case_study')),
    question_text   TEXT NOT NULL,           -- For Section A: the question. For Section B: sub-part question.
    case_preamble   TEXT,                    -- Section B only: full scenario description
    sub_part        TEXT,                    -- 'a', 'b', 'c' or NULL for standalone
    marks           INTEGER NOT NULL,
    content_type    TEXT NOT NULL DEFAULT 'pyq'
        CHECK(content_type IN ('pyq','practice')),
    concept_tags    TEXT,                    -- JSON: ["integrity","emotional_intelligence"]
    thinker_tags    TEXT,                    -- JSON: ["aristotle","gandhi","goleman"]
    framework_hint  TEXT CHECK(framework_hint IN ('IDEA-U','STAKE','IDEA-U-extended')),
    sequence_order  INTEGER,                 -- display order within section
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### m044 — ethics_practice_papers

```sql
CREATE TABLE ethics_practice_papers (
    paper_id        TEXT PRIMARY KEY,        -- 'ethics_prac_1', 'ethics_prac_2'
    paper_title     TEXT NOT NULL,
    generation_year INTEGER NOT NULL,
    section_a_marks INTEGER DEFAULT 125,
    section_b_marks INTEGER DEFAULT 125,
    total_marks     INTEGER DEFAULT 250,
    time_minutes    INTEGER DEFAULT 180,
    difficulty      TEXT CHECK(difficulty IN ('easy','medium','hard')),
    theme_focus     TEXT,                    -- e.g., 'governance+probity', 'foundational_values+case_heavy'
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### m045 — ethics_model_answers

```sql
CREATE TABLE ethics_model_answers (
    answer_id       TEXT PRIMARY KEY,
    question_id     TEXT NOT NULL REFERENCES ethics_questions(question_id),

    -- Section A answers (IDEA-U framework)
    theory_intro    TEXT,                    -- I: definition + thinker
    theory_dimensions TEXT,                 -- D: 3-4 facets (JSON or structured text)
    theory_evidence TEXT,                   -- E: governance example + historical ref
    theory_apply    TEXT,                   -- A: civil service application
    theory_upshot   TEXT,                   -- U: governance failure prevented

    -- Section B answers (STAKE framework)
    stake_stakeholders TEXT,                -- S: who + their interests
    stake_tension   TEXT,                   -- T: core ethical conflict
    stake_analysis  TEXT,                   -- A: 3 ethical framework lenses
    stake_decision  TEXT,                   -- K: justified recommended action
    stake_execution TEXT,                   -- E: implementation + learning

    -- Full answer (flattened, ready for display)
    full_answer_text TEXT NOT NULL,
    word_count      INTEGER,
    thinkers_cited  TEXT,                   -- JSON: ["aristotle","gandhi"] — for UI display
    frameworks_used TEXT,                   -- JSON: ["kantian","utilitarian","virtue"]
    model_used      TEXT DEFAULT 'claude-sonnet-4-6',
    human_reviewed  INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### m046 — ethics_attempts

```sql
CREATE TABLE ethics_attempts (
    attempt_id      TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    question_id     TEXT NOT NULL REFERENCES ethics_questions(question_id),
    attempt_text    TEXT,
    word_count      INTEGER,
    -- Self-compare only — no AI scoring
    self_rating     TEXT CHECK(self_rating IN ('strong','partial','weak')),
    self_notes      TEXT,                   -- user's own notes after comparing to model answer
    model_revealed  INTEGER DEFAULT 0,      -- did user reveal the model answer?
    revealed_at     TEXT,
    submitted_at    TEXT DEFAULT (datetime('now'))
);
```

### Pattern Synthesis table

```sql
-- Reuses essay_theme_analysis pattern but for Ethics
CREATE TABLE ethics_concept_analysis (
    concept_tag         TEXT PRIMARY KEY,    -- 'integrity', 'emotional_intelligence', etc.
    concept_label       TEXT NOT NULL,
    frequency_count     INTEGER NOT NULL,    -- appearances 2014–2024
    section_preference  TEXT,               -- 'A', 'B', 'both'
    year_appearances    TEXT,               -- JSON: [2014, 2017, ...]
    typical_marks       TEXT,               -- JSON: [10, 12] — most common mark values
    linked_thinkers     TEXT,               -- JSON: ["aristotle","gandhi"]
    linked_frameworks   TEXT,               -- JSON: ["virtue_ethics","kantian"]
    example_question    TEXT,               -- one representative question
    fy26_probability    TEXT CHECK(fy26_probability IN ('high','medium','low')),
    trend               TEXT CHECK(trend IN ('rising','stable','declining')),
    last_updated        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE ethics_scenario_analysis (
    scenario_type       TEXT PRIMARY KEY,    -- 'hierarchical_pressure', 'whistleblowing', etc.
    scenario_label      TEXT NOT NULL,
    frequency_count     INTEGER NOT NULL,
    year_appearances    TEXT,               -- JSON: [2014, 2016, ...]
    typical_role        TEXT,               -- 'district_collector', 'police_officer', 'any_civil_servant'
    core_dilemma_type   TEXT,               -- 'duty_vs_compassion', 'rules_vs_outcomes', etc.
    recommended_framework TEXT,             -- which STAKE step is most critical for this type
    fy26_probability    TEXT CHECK(fy26_probability IN ('high','medium','low')),
    example_preamble    TEXT,               -- 1-2 sentence scenario sketch
    last_updated        TEXT DEFAULT (datetime('now'))
);
```

---

## UI Structure — 3 tabs inside /upsc/ethics

```
/upsc/ethics                        → landing: 3-tab layout
  ├── tab: Practice Papers          → 2 full practice papers (Paper 1, Paper 2)
  │     Each paper: Section A (12-15 Qs) + Section B (3-4 case studies)
  │     Timer optional (180 min)
  │     Self-compare: write → reveal model answer → rate yourself → save notes
  ├── tab: Solved Past Years        → year picker: 2014–2025
  │     Each year: Section A full + Section B full
  │     Same self-compare flow
  └── tab: Pattern Synthesis        → concept frequency + scenario type frequency
        Concept table (ethics_concept_analysis)
        Scenario type map (ethics_scenario_analysis)
        "Which concepts appear every year" callout
        "Which scenario types are due" callout

/upsc/ethics/<paper_id>             → full paper view (practice or PYQ year)
/upsc/ethics/<paper_id>/q/<qid>     → individual question: prompt + attempt editor + reveal button
/upsc/ethics/framework-guide        → static: IDEA-U + STAKE formula with worked examples
```

Navigation: UPSC tab toggle → "Eco Optional | GS Mains | Essay Paper | Ethics Paper"

**CSS-MOB-001 note:** This makes the toggle 4 items. Toggle is within the UPSC tab page (not the bottom nav), so CSS-MOB-001 (4-tab mobile grid constraint) is not violated. The toggle is a button group, not a nav item.

---

## Batch Generation Plan

**Scope decision (post-research):** Cover 2019–2025 (7 years). This is the most stable format period and most pedagogically relevant. Pre-2019 format varied significantly; those years can be added in a future batch.

All model answers in ONE Anthropic Batch API call (same run as Essay batch to save overhead).

| Group | Items | Notes |
|---|---|---|
| PYQ Section A (2019–2025) | 7 × ~13 = **91** | IDEA-U framework, 150 words each |
| PYQ Section B (2019–2025) | 7 × 6 cases × ~3 sub-parts = **126** | STAKE framework, 200-400 words per sub-part |
| Practice Paper 1 — Section A | **13** | Sonnet generates; concept mix: integrity, EI, governance, Chanakya, digital ethics |
| Practice Paper 1 — Section B | 6 cases × 3 sub-parts = **18** | Types: hierarchical, whistleblowing, duty vs. personal, rules vs. compassion, dev vs. env, gender |
| Practice Paper 2 — Section A | **13** | Concept mix: social media ethics, constitutional morality, Ambedkar angle, CSR, attitude |
| Practice Paper 2 — Section B | 6 cases × 3 sub-parts = **18** | Types: conflict of interest, disaster, private sector, international, corruption + career, border crisis |
| **Total (ethics)** | **~279** | |
| **Combined with Essay batch** | **~315** | Essay 36 + Ethics 279 → one Batch API call |

**Cost estimate (Batch API, Sonnet 4.6, 50% discount):**

| Batch | Items | Avg input | Avg output | Cost |
|---|---|---|---|---|
| Essay answers | 36 | 1,200 tok | 2,500 tok | ~$0.74 |
| Ethics Section A (IDEA-U) | 91+26 | 800 tok | 600 tok | ~$0.40 |
| Ethics Section B (STAKE) | 126+36 | 1,200 tok | 1,000 tok | ~$1.30 |
| **Combined total** | **315** | | | **~$2.44** |
| **With 2× buffer** | | | | **~$5** |

**Test-mode gate (mandatory before full batch):** `generate_answers.py --test-mode --count 4` — test 1 IDEA-U short (2-mark) + 1 IDEA-U medium (10-mark) + 1 STAKE 3-sub-part case + 1 essay. Validate all 4 JSON shapes before releasing 315-item batch.

## Practice Paper Design (2 papers, data-driven)

**Paper 1 — "Governance + Integrity" (most probable core)**
- Section A themes: Integrity (Q1), EI (Q2), Quote block: Gandhi + Vivekananda + Chanakya (Q3), Constitutional morality (Q4), Digital ethics / AI (Q5), Good governance + Mission Karmayogi (Q6)
- Section B cases: Hierarchical pressure + corrupt procurement (CS1) · Whistleblowing — toxic dumping (CS2) · Official duty vs. personal obligation — family crisis during field work (CS3) · Rules vs. compassion — welfare scheme eligibility (CS4) · Development vs. environment — displacement (CS5) · Gender discrimination — workplace harassment + institutional response (CS6)

**Paper 2 — "Contemporary Ethics" (new-age + philosophy angle)**
- Section A themes: Social media / cyberbullying ethics (Q1), Constitutional morality + Ambedkar (Q2), Quote block: Dalai Lama + Thiruvalluvar + William James (Q3), Attitude vs. aptitude in administration (Q4), CSR / private sector ethics (Q5), International ethics / climate obligations (Q6)
- Section B cases: Conflict of interest — dual pressure from family + superior (CS1) · Disaster resource allocation — medical triage (CS2) · Private sector dual quality standards (CS3) · Border humanitarian crisis + sovereignty (CS4) · MGNREGA-style fraud audit (CS5) · Rules vs. compassion — emergency blood transfusion + protocol (CS6)

---

## Self-Compare Flow (no AI scoring)

```
User opens question
  → Attempt editor (textarea + word count bar)
  → Submit attempt → stored in ethics_attempts
  → Model answer revealed (button: "Reveal Model Answer")
    → model_revealed=1, revealed_at=timestamp recorded
  → Self-rating: [Strong] [Partial] [Weak]
    → self_rating stored; self_notes (optional textarea)
  → Next question
```

Progress tracking: `SELECT COUNT(*) FROM ethics_attempts WHERE user_id=? AND model_revealed=1` — "X questions practiced"

---

## Scripts

```
scripts/ethics/
├── seed_concepts.py           # seeds ethics_concept_analysis + ethics_scenario_analysis
│                              # (from research agent output — manual after research completes)
├── seed_questions.py          # --input data/ethics_questions_pyq.jsonl → inserts ethics_questions
│                              # --input data/ethics_questions_practice.jsonl → inserts practice questions
├── generate_answers.py        # --batch-id E2026_ALL → all PYQ + practice answers in one batch
│                              # --test-mode --count 2 → validate IDEA-U and STAKE JSON shape first
├── ingest_pyq.py              # --year 2026 → post-exam ingestion (Nov 2026)
└── update_analysis.py         # --year 2025 → updates ethics_concept_analysis frequency counts
```

### Seed file format (data/ethics_questions_pyq.jsonl)
```jsonl
{"question_id":"ethics_pyq_2024_a01","paper_year":2024,"paper_id":"ethics_pyq_2024","section":"A","question_type":"medium","question_text":"What is meant by 'conflict of interest'? Illustrate with examples how it can be managed in public administration.","case_preamble":null,"sub_part":null,"marks":10,"content_type":"pyq","concept_tags":["conflict_of_interest","integrity","governance"],"thinker_tags":[],"framework_hint":"IDEA-U","sequence_order":3}
{"question_id":"ethics_pyq_2024_b01_a","paper_year":2024,"paper_id":"ethics_pyq_2024","section":"B","question_type":"case_study","question_text":"Identify the ethical issues in the above situation.","case_preamble":"You are a newly appointed District Collector...","sub_part":"a","marks":8,"content_type":"pyq","concept_tags":["hierarchical_pressure","integrity"],"thinker_tags":["kant"],"framework_hint":"STAKE","sequence_order":1}
```

---

## Phases

### Phase 0 — Research (S43, in progress)
- [ ] Section A research agent returns: concept frequency, question types, thinker frequency, 2025 Section A
- [ ] Section B research agent returns: scenario type frequency, sub-part patterns, 2025 Section B
- [ ] Synthesize: build ethics_concept_analysis seed data + ethics_scenario_analysis seed data
- [ ] Curate ethics_questions_pyq.jsonl (all available PYQ questions)
- [ ] Draft ethics_questions_practice.jsonl (2 practice paper question sets)

### Phase 1 — Schema + Seed (1 session)
- [ ] m044: ethics_questions + ethics_practice_papers
- [ ] m045: ethics_model_answers
- [ ] m046: ethics_attempts
- [ ] m044 also: ethics_concept_analysis + ethics_scenario_analysis
- [ ] scripts/ethics/seed_concepts.py — seeds analysis tables from research findings
- [ ] scripts/ethics/seed_questions.py — inserts from JSONL files

### Phase 2 — Batch Generation (shared session with Essay Phase 2, or separate)
- [ ] scripts/ethics/generate_answers.py --test-mode --count 2 (test IDEA-U + STAKE JSON output)
- [ ] Full batch: --batch-id E2026_ALL (~289 items, ~$1.44)
- [ ] Insert results into ethics_model_answers
- [ ] Spot-check: 1 definition answer + 1 medium theory + 1 case study sub-part

### Phase 3 — Blueprint + Templates (1 session)
- [ ] web/blueprints/ethics_paper_bp.py — routes: landing, paper view, question view, framework guide
- [ ] Register in web/app.py (uses g.upsc_gs_conn — same as essay_bp, no new connection)
- [ ] web/templates/ethics_landing.html — 3-tab layout
- [ ] web/templates/ethics_paper.html — full paper view: Section A list + Section B case studies
- [ ] web/templates/ethics_question.html — attempt editor + reveal button + self-rating
- [ ] web/templates/ethics_framework.html — IDEA-U + STAKE formula with worked examples
- [ ] UPSC toggle: add "Ethics Paper" as 4th toggle state

### Phase 4 — Post-exam + Annual (future)
- [ ] scripts/ethics/ingest_pyq.py --year 2026 (after Nov 2026 paper)
- [ ] scripts/ethics/update_analysis.py --year 2025

---

## Indexing Layer (added S43 — enables multi-dimensional lookup)

Questions and answers indexed by: year · section · question type · concept · thinker · scenario type · paper ID · content type · sub-part.

### Normalized junction tables (replaces JSON blobs)

```sql
-- ethics_questions ↔ ethics_concept_analysis (primary + secondary concepts)
CREATE TABLE ethics_concept_links (
    link_id      TEXT PRIMARY KEY,
    question_id  TEXT NOT NULL REFERENCES ethics_questions(question_id) ON DELETE CASCADE,
    concept_tag  TEXT NOT NULL REFERENCES ethics_concept_analysis(concept_tag),
    is_primary   INTEGER DEFAULT 1,
    UNIQUE(question_id, concept_tag)
);

-- ethics_questions ↔ gs4_thinkers (thinker cited or quoted)
CREATE TABLE ethics_thinker_links (
    link_id      TEXT PRIMARY KEY,
    question_id  TEXT NOT NULL REFERENCES ethics_questions(question_id) ON DELETE CASCADE,
    thinker_id   TEXT NOT NULL REFERENCES gs4_thinkers(thinker_id),
    usage_type   TEXT CHECK(usage_type IN ('cited','quoted','implicit')),
    UNIQUE(question_id, thinker_id)
);

-- ethics_questions ↔ ethics_scenario_analysis (case studies only; primary + secondary type)
CREATE TABLE ethics_scenario_links (
    link_id       TEXT PRIMARY KEY,
    question_id   TEXT NOT NULL REFERENCES ethics_questions(question_id) ON DELETE CASCADE,
    scenario_type TEXT NOT NULL REFERENCES ethics_scenario_analysis(scenario_type),
    is_primary    INTEGER DEFAULT 1,
    UNIQUE(question_id, scenario_type)
);
```

### SQLite indexes on ethics_questions

```sql
CREATE INDEX idx_ethics_year     ON ethics_questions(paper_year);
CREATE INDEX idx_ethics_section  ON ethics_questions(section);
CREATE INDEX idx_ethics_type     ON ethics_questions(question_type);
CREATE INDEX idx_ethics_paper    ON ethics_questions(paper_id, sequence_order);
CREATE INDEX idx_ethics_content  ON ethics_questions(content_type, paper_year);
CREATE INDEX idx_ethics_subpart  ON ethics_questions(paper_id, section, sub_part);
```

### FTS5 for full-text search

```sql
CREATE VIRTUAL TABLE ethics_fts USING fts5(
    question_id UNINDEXED,
    question_text,
    case_preamble,
    content='ethics_questions', content_rowid='rowid'
);
CREATE VIRTUAL TABLE ethics_answer_fts USING fts5(
    answer_id UNINDEXED,
    full_answer_text,
    thinkers_cited,
    content='ethics_model_answers', content_rowid='rowid'
);
```

### Blueprint query helpers (ethics_paper_bp.py)

```python
# By concept (e.g., "emotional_intelligence" — all questions across years)
SELECT eq.* FROM ethics_questions eq
JOIN ethics_concept_links ecl ON ecl.question_id = eq.question_id
WHERE ecl.concept_tag = ? ORDER BY eq.paper_year DESC, eq.section

# By thinker (e.g., all questions citing Gandhi)
SELECT eq.* FROM ethics_questions eq
JOIN ethics_thinker_links etl ON etl.question_id = eq.question_id
WHERE etl.thinker_id = ? ORDER BY eq.paper_year DESC

# By scenario type (case studies only, e.g., "whistleblowing")
SELECT eq.* FROM ethics_questions eq
JOIN ethics_scenario_links esl ON esl.question_id = eq.question_id
WHERE esl.scenario_type = ? AND eq.section = 'B' ORDER BY eq.paper_year DESC

# Full paper by year (section A + B in order)
SELECT eq.* FROM ethics_questions eq
WHERE eq.paper_id = 'ethics_pyq_2024'
ORDER BY eq.section, eq.sequence_order

# Full-text search across preambles (find all "sand mining" cases)
SELECT eq.* FROM ethics_questions eq
JOIN ethics_fts ON ethics_fts.question_id = eq.question_id
WHERE ethics_fts MATCH ? AND eq.section = 'B'

# Year-wise concept coverage (for Pattern Synthesis tab)
SELECT ecl.concept_tag, eq.paper_year, COUNT(*) as q_count
FROM ethics_concept_links ecl
JOIN ethics_questions eq ON eq.question_id = ecl.question_id
GROUP BY ecl.concept_tag, eq.paper_year
ORDER BY q_count DESC

# Thinker rotation tracker (ancient philosopher slot)
SELECT etl.thinker_id, eq.paper_year FROM ethics_thinker_links etl
JOIN ethics_questions eq ON eq.question_id = etl.question_id
JOIN gs4_thinkers gt ON gt.thinker_id = etl.thinker_id
WHERE gt.school_of_thought IN ('Indian_Classical','Jain','Sikh','Buddhist')
ORDER BY eq.paper_year DESC
```

Junction tables and indexes added in **m044** (alongside ethics_questions). FTS tables in **m045** (alongside model answers — built after answer text is populated).

## Key Constraints

| Constraint | Rule |
|---|---|
| No AI scoring | ethics_attempts has no ai_score_json. Self-rating only. No essay_eval gate needed. |
| SYNC-001 | ethics_paper_bp uses g.upsc_gs_conn — already opened. No new connection key. |
| JINJA2-001 | Template variables: question_rows, attempt_entries, concept_rows, scenario_rows. Never `items`. |
| CSS-MOB-001 | 4-item UPSC toggle is within the page, NOT a 5th bottom nav tab. Grid unaffected. |
| Reuse existing gs4_* | ethics_questions.concept_tags and thinker_tags reference gs4_concepts and gs4_thinkers by ID — no FK (cross-table tag matching via Python, same SYNC-001 pattern). |
| Vol of PYQ data | Section A alone: ~130 answers over 10 years. Don't seed what can't be verified. Only include confirmed questions from research agents — no fabrication. |

---

## Research Findings (S43)

### Section A — CONFIRMED (agent a4d09250a72571f76)

**Paper held:** August 24, 2025 (2025 Mains). All 13 years available (2013–2025).

**Structure (stabilized 2022 onward):** 12–13 questions × 10 marks each = ~125 marks. All Section A questions are 10 marks / 150 words. Earlier years (2013–2016) had definitional multi-sub-part questions in a single 10-mark slot.

**Concept Frequency Map (2013–2025):**
| Concept | Years | Priority |
|---|---|---|
| Integrity / Probity / Honesty | 11/13 | CERTAIN |
| Civil service values (accountability, transparency, dedication) | 10/13 | CERTAIN |
| Governance (good governance, ethical governance) | 9/13 | HIGH |
| Emotional Intelligence (EI/EQ) | 8/13 | HIGH |
| Corruption + anti-corruption measures | 8/13 | HIGH |
| Attitude and Aptitude | 7/13 | HIGH |
| Laws vs Ethics / Code of Ethics vs Code of Conduct | 5/13 | MEDIUM |
| Conscience (voice/crisis) | 5/13 | MEDIUM |
| Conflict of interest | 5/13 | MEDIUM |
| International Relations ethics | 5/13 | MEDIUM |
| Constitutional morality | 4/13 → rising | HIGH (was 2-mark, now 10-mark Q) |
| Gender equality / women | 4/13 | MEDIUM |
| Environmental ethics | 4/13 | MEDIUM |
| Digital/tech ethics (AI, social media) | 4/13, rising | HIGH |
| RTI / Whistleblowers / Transparency mechanisms | 5/13 | MEDIUM |

**Thinker Frequency:**
| Thinker | Count | Pattern |
|---|---|---|
| Gandhi | 9/13 | Near-certain; quotes on greed/integrity/anger/forgiveness |
| Vivekananda | 5/13 | Every 2-3 years; perseverance + service |
| Abdul Kalam | 5/13 | Character, righteousness, family/teachers |
| Socrates | 4/13 | Examined life, moral relativism |
| Dalai Lama | 3/13 | Inner peace, judging success |
| Lincoln | 3/13 | Power tests character; good vs evil |
| Thiruvalluvar | 3/13 | Ancient Indian slot; practical wisdom |
| **Ambedkar** | 0/13 | **ANOMALY** — constitutional morality asked 4× but Ambedkar never named → HIGH probability future question |
| Buddha | 2/13 | 2020 slot; rotating ancient Indian philosopher |
| Guru Nanak | 1/13 | 2023 ancient Indian slot |
| Mahavira | 1/13 | 2025 ancient Indian slot |
| Kautilya | 2/13 | Statecraft and corruption |

**"Ancient Indian Philosopher" slot (confirmed pattern, 2019–2025):** One thinker per year, rotating. Sequence: Gandhi/Vivekananda dominant → Buddha (2020) → Vivekananda (2021) → Abdul Kalam (2022) → Guru Nanak (2023) → [none named 2024] → Mahavira (2025). **Likely 2026 picks:** Chanakya, Ambedkar, Tagore, or Iqbal.

**2025 Section A themes signal:**
- Constitutional morality elevated to 10-mark full question (was 2-mark short note in 2022)
- Clausewitz first explicitly named Western military theorist
- Duty-ethics / Karma yoga language in Q5a (Bhagavad Gita echo)
- Digital ethics shifted from AI governance → social media ethics

**Critical insight for content generation:** Mark distribution is 10 marks per question universally. IDEA-U framework with 150-word target applies to every single Section A question. No variation needed.

### Section B — CONFIRMED (agent a2b5734b55d217989)

**Structure (stable 2013–2025):** 6 case studies per year × 20–25 marks each = ~125 marks. Each case: 1 preamble (scenario) + 2–4 sub-parts. Sub-part count per case rose from 2–3 (2013–2019) to 3–5 (2020–2022) to 3–4 deep (2023–2025).

**Scenario Type Frequency (2013–2025):**
| Scenario Type | Count | Priority | 2026 Bet |
|---|---|---|---|
| Hierarchical / political pressure | 18 | CERTAIN | HIGH |
| Corruption / misuse of office | 16 | CERTAIN | HIGH |
| Whistleblowing dilemma | 14 | CERTAIN | HIGH |
| Official duty vs. personal obligation | 10 | HIGH | HIGH |
| Rules vs. compassion | 9 | HIGH | HIGH |
| Gender discrimination / workplace harassment | 8 | HIGH | MEDIUM |
| Private sector ethics | 8 | HIGH | MEDIUM |
| Development vs. environment | 7 | HIGH | HIGH (heatwave + deforestation CA) |
| Disaster / emergency resource allocation | 7 | HIGH | MEDIUM |
| Conflict of interest | 4 | MEDIUM | HIGH (appeared 2023/24/25) |
| International / multi-stakeholder | 4 | MEDIUM | MEDIUM |
| Child labour / tribal exploitation | 3 | LOW | LOW |
| Law enforcement + socio-economic roots | 4 | MEDIUM | MEDIUM |

**Sub-part question type taxonomy (confirmed pattern across all 13 years):**
| Code | Sub-part type | Frequency | Maps to STAKE step |
|---|---|---|---|
| A | Options identification | 100% of cases | S+T (surface the landscape) |
| B | Ethical issue identification | 100% of cases | S+T (name values in conflict) |
| C | Critical evaluation of each option | 100% of cases | A (analysis) |
| D | Selection + justification | 100% of cases | K (key decision) |
| E | Policy/systemic recommendation | ~40% and rising | E (execution — systemic) |
| F | Compassion/empathy response | ~20% | K+E (qualities of officer) |

**STAKE framework validation:** The sub-part taxonomy confirms STAKE maps cleanly — every case study sub-part falls under one of S/T/A/K/E. A student who internalizes STAKE can handle any sub-part decomposition without re-learning for each case.

**Critical observation — 2025 Section B:** First explicit humanitarian border crisis (Q12), first MGNREGA fraud audit case (Q11), return of personal-vs-public duty in existential form (Q7). The deforestation-for-housing case (Q8) is the most philosophically demanding since Snowden (2018) — no objectively correct answer exists.

**2025 Section B — confirmed questions:**
| Case | Protagonist | Scenario | Type |
|---|---|---|---|
| Q7 | Vijay (Deputy Commissioner) | Mother dies during live disaster relief operation | Duty vs. personal obligation |
| Q8 | District Administration | Clear ecologically sensitive forest for housing homeless | Development vs. environment |
| Q9 | Subash (PWD Secretary) | Son + minister's nephew both pressure for land info from mega road project | Conflict of interest + political |
| Q10 | Rajesh (PSU Admin Officer) | Boss pressures irregular stationery procurement; promotion ACR at risk | Hierarchical + corruption |
| Q11 | District Administrator Incharge | MGNREGA fraud — ghost workers, phantom works, fund diversion | Corruption + welfare governance |
| Q12 | Ashok (Divisional Commissioner) | 200+ civilians + armed soldiers crossing border; HQ unreachable in storm | International + disaster + law vs. compassion |

### 2025 GS4 Section A Questions (for seed file):
13 questions confirmed — integrity/probity absent as named concept Q this year (instead: social media ethics, constitutional morality, Clausewitz, eco-sensitive compensation, Thiruvalluvar, William James, Vivekananda, civil servant objectivity, Mahavira, duty-devotion, civil servant as facilitator, workplace ethics culture, ethical frameworks for sustainable growth).

## Status
- [x] Phase 0: Section A research complete (S43) — 13 years of data, concept map, thinker frequency
- [x] Phase 0: Section B research complete (S43) — 13 years, scenario type map, sub-part taxonomy, 2025 confirmed
- [x] Phase 0: Practice paper design complete (2 papers, data-driven)
- [x] Phase 0: Combined batch plan finalized (315 items = essay 36 + ethics 279, ~$2.44)
- [ ] Phase 1: Schema + seed
- [ ] Phase 2: Batch generation
- [ ] Phase 3: Blueprint + templates
- [ ] Phase 4: Post-exam + annual
