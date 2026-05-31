# IES-Descriptive System — Foundation Specification

**Version:** 2026-05-29
**Status:** ✅ IMPLEMENTATION COMPLETE — system is built and running
**Scope:** IES 2026 first; designed to extend to UPSC Mains, RBI DEPR descriptive without schema rebuild

---

## Implementation Status (as of 2026-05-29)

### What was built (deviates from original spec in places — noted below)

| Phase | Status | Notes |
|-------|--------|-------|
| DB schema (16 tables) | ✅ Done | `data/ies.db` |
| Topic taxonomy (30 topics, 126 subtopics) | ✅ Done | GE-01 to GE-04 |
| PYQ ingestion | ✅ Done | 1219 questions, 2010–2025 |
| Rubric extraction (Haiku batch) | ✅ Done | 1219/1219 |
| Model answer generation (Sonnet batch) | ✅ Done | 1219/1219 — **spec deviation: see below** |
| Priority scores (w1+w2+w3+w5) | ✅ Done | w4, w6 not yet implemented |
| Web app (Streamlit, Gemini dark theme) | ✅ Done | 5 pages at `web/`, runs on :8501 |
| Return quiz MCQ pre-cache | ⏳ Pending | Run `python3 scripts/generate_return_quiz.py --all` |

### Key deviations from spec

1. **Model answers ARE generated** — The spec said "IS NOT: A content generation system." This was overridden deliberately. 1219 Sonnet-generated model answers (intro/body/conclusion + diagram) are the core study resource.

2. **Descriptive quiz uses LLM** — The spec said "No LLM calls during quiz sessions." This applies only to the MCQ return quiz (pre-cached). The *descriptive* quiz (`web/pages/2_Quiz.py`) uses Sonnet to evaluate written answers. These are two separate quiz modes.

3. **w4 (CA relevance) and w6 (graph centrality) not implemented** — Both columns exist in `topic_base_scores` but are 0. Priority runs on w1+w2+w3+w5 only.

4. **Web frontend built in Phase 1** — Spec put frontend as a "later" item. Built ahead of schedule using Streamlit.

5. **Ecoholics promo text fix** — PDFs from ecoholics.in contained promotional text injected mid-question at page breaks. `clean_q()` in `web/db.py` strips it with regex before display.

### How to start the app
```bash
cd "/Users/rahulsingh/Desktop/Claude Projects/Descriptive-exams"
/Users/rahulsingh/Library/Python/3.9/bin/streamlit run web/app.py
# Opens at http://localhost:8501
```

---

## 0. What This System Is and Is Not

**IS:**
- A diagnostic + priority + gap detection engine for descriptive exam preparation
- A study brief generator that tells users exactly what to ask an AI agent
- A return-quiz system that verifies whether AI agent study actually worked
- A session composer that tells users what to study today, in what order, and why

**IS NOT:**
- A content generation system (no explanations, no model answers generated internally)
- A teaching tool (that job belongs to the external AI agent — Claude.ai / Gemini)
- A question bank generator (questions are sourced from PYQs, not AI-generated)

**The split:** Model = intelligence layer. AI agent = content layer. Bridge = context package.

---

## 1. Core Architecture Decisions (Non-Negotiable)

These decisions, if wrong, require a full schema rebuild. They cannot be patched.

### Decision 1: exam_id in every primary key
Every table that stores exam-specific or user-specific data includes `exam_id` as part of its primary key. This is the IES system, but "ies_2026" is the first exam_id, not a hardcoded string in code. When UPSC Mains is added, it gets `exam_id = "upsc_mains_2027"` — no schema change required.

### Decision 2: gap_state is a first-class entity, not a column
Gap state is not a column on `mastery_states`. It has its own table with an immutable event log. Every transition is recorded. This is the foundation of the feedback loop. Without event history, you cannot debug why the system recommended a topic or understand a user's study pattern.

### Decision 3: Priority formula weights are data, not code
All 9 weights (w1–w9) live in `exam_configurations` table. Tuning weights = updating a row. No code deployment required. Different exams get different weight rows from day one.

### Decision 4: SQLite schema must be PostgreSQL-compatible
All data types, column names, and constraint patterns must work in PostgreSQL without modification. When we migrate to TALE's PostgreSQL infrastructure, the migration is a data copy, not a schema redesign. No SQLite-isms (no AUTOINCREMENT, use INTEGER PRIMARY KEY; no BOOLEAN, use INTEGER 0/1; timestamps as TEXT ISO-8601).

### Decision 5: No LLM calls during quiz sessions
The return quiz questions must be pre-generated and cached before any quiz session starts. Quiz session routes must not import the LLM client. This is enforced by project structure: `scripts/quiz_session.py` has no import of `anthropic`.

---

## 2. The Revised Priority Formula

### Base Formula (exam-level, user-agnostic)
```
base_priority(topic, exam) =
    w1 × pyq_recurrence_score(topic, exam)
  + w2 × pyq_recency_score(topic, exam)
  + w3 × concept_persistence_score(topic, exam)
  + w4 × ca_relevance_score(topic, exam)
  + w5 × syllabus_weight(topic, exam)
  + w6 × graph_centrality_score(topic, exam)
```

### Personal Priority (user-adjusted, changes per session)
```
personal_priority(topic, user, exam, date) =
    base_priority(topic, exam)
  - w7 × mastery_level(topic, user)
  - w8 × recency_quiz_only_discount(topic, user, date)
  - w9 × recency_full_loop_discount(topic, user, date)
```

### Component Definitions

**w1 — pyq_recurrence_score**: How many times topic appeared across all years.
`Σ(questions_that_year) / total_questions_all_years`  — normalized 0–1.

**w2 — pyq_recency_score**: Exponential decay weighting.
`Σ(decay_factor^(current_year - year) × questions_that_year)` — normalized 0–1.
Default `decay_factor = 0.9` for IES.

**w3 — concept_persistence_score**: How many distinct years the topic appeared (regardless of frequency per year). A topic in 7 of 10 years = 0.7. Rewards consistent presence over occasional bursts.
`distinct_years_appeared / total_years_in_corpus`

**w4 — ca_relevance_score**: Current affairs linkage to this topic.
`Σ(institutional_relevance × proximity_to_exam × concept_match_score)` per relevant CA event — normalized. Decays as exam date passes. Zero if exam date has passed.

**w5 — syllabus_weight**: Explicit IES syllabus weighting. Paper II topics get base weight 1.0. Paper III stats topics get 0.8. Paper I GS topics get 0.6 (lower because broader and harder to predict). Configurable per exam.

**w6 — graph_centrality_score**: How many other topics depend on or link to this topic. Fiscal deficit links to bond yields, inflation, monetary policy, crowding out — high centrality. Mastering it unlocks understanding of connected topics. Computed as normalized in-degree in concept graph. Zero until concept graph is built (Phase 3).

**w7 — mastery_level**: User's current mastery on this topic (0–1). Discounts priority if already known. Uses SAR-adjusted mastery: `effective_mastery = (quiz_score × (1-SAR)) + (claimed_level × SAR)`.

**w8 — recency_quiz_only_discount**: How recently user attempted a quiz on this topic WITHOUT completing the full study loop. Decays exponentially over 3 days. Prevents the system from immediately re-flagging a topic a user just quizzed on (even if they didn't fully study it).

**w9 — recency_full_loop_discount**: How recently user completed the FULL study loop (flagged → studied with AI agent → passed return quiz ≥80%). Strong discount, decays over 14 days (forgetting curve halflife). `w9 >> w8`.

### Default Weights for IES 2026

```
w1 = 0.22   # recurrence
w2 = 0.20   # recency
w3 = 0.10   # persistence
w4 = 0.08   # current affairs
w5 = 0.12   # syllabus weight
w6 = 0.08   # graph centrality (starts at 0 until graph built)
w7 = 0.20   # mastery discount (personal)
w8 = 0.05   # quiz-only discount (personal)
w9 = 0.15   # full-loop discount (personal)
```

Weights w1+w2+w3+w4+w5+w6 = 0.80 (base score max = 0.80 before personal discounts).
Personal discounts w7+w8+w9 = max reduction of 0.40 (a fully mastered, recently studied topic scores near zero).

### Urgency Multiplier (Gap State Override)

Certain gap states apply a multiplier to the final personal_priority score:

```
UNVISITED   × 1.0  (no modification)
FLAGGED     × 1.2  (already surfaced, user hasn't acted yet — escalate)
IN_STUDY    × 0.5  (user is currently studying it — deprioritize from list)
PARTIAL     × 1.5  (user studied but quiz showed partial understanding — urgent)
VERIFIED    × 0.3  (recently verified — suppress strongly)
DECAYING    × 1.1  (verified but forgetting curve says review soon)
```

### Flag Threshold
Topic enters FLAGGED state when:
`personal_priority_score × urgency_multiplier > flag_threshold`
Default `flag_threshold = 0.55` for IES 2026.

---

## 3. The Gap State Machine

### States

```
UNVISITED   → topic exists in system, never surfaced to user
FLAGGED     → priority threshold crossed, shown in user's study list
IN_STUDY    → user clicked "study this", context package opened
PARTIAL     → return quiz score 50–79% — understood but not solid
VERIFIED    → return quiz score ≥80% — topic mastered for now
DECAYING    → verified but forgetting curve halflife expired, needs review
```

### Transitions

```
UNVISITED   → FLAGGED    : priority × urgency_multiplier > flag_threshold
FLAGGED     → IN_STUDY   : user opens context package / clicks "study"
FLAGGED     → UNVISITED  : priority drops below threshold (topic de-prioritized by CA decay or new mastery data)
IN_STUDY    → VERIFIED   : return quiz score ≥ 0.80
IN_STUDY    → PARTIAL    : return quiz score 0.50–0.79
IN_STUDY    → FLAGGED    : return quiz score < 0.50 (back to flagged with urgency_multiplier += 0.3)
PARTIAL     → FLAGGED    : immediately (back on study list with elevated urgency)
PARTIAL     → VERIFIED   : user studies again + passes return quiz ≥ 0.80
VERIFIED    → DECAYING   : current_date ≥ next_review_at (based on halflife)
DECAYING    → FLAGGED    : if not addressed within 2 days of DECAYING
DECAYING    → VERIFIED   : user passes return quiz ≥ 0.80 during decay period
```

### Edge Cases in Transitions

**Urgency escalation on repeated failure:**
Each time a topic goes `IN_STUDY → FLAGGED` (quiz < 50%), `urgency_multiplier += 0.3`, capped at 2.0. This ensures a topic the user keeps failing on rises to the top of the priority list and stays there.

**Exam proximity compression:**
When `days_until_exam ≤ 7`, all `next_review_at` dates are overridden to `exam_date - 1`. Every decaying topic comes back immediately. The forgetting curve is overridden by the exam deadline.

**Stale IN_STUDY:**
If a topic stays IN_STUDY for > 48 hours without a return quiz being submitted, it reverts to FLAGGED. This handles the case where a user opened a context package but never actually studied.

---

## 4. Database Schema (SQLite, PostgreSQL-Compatible)

### Table: `exam_configurations`
```sql
CREATE TABLE exam_configurations (
    exam_id                   TEXT PRIMARY KEY,      -- 'ies_2026'
    exam_name                 TEXT NOT NULL,
    exam_date                 TEXT,                  -- ISO-8601 date
    pyq_decay_factor          REAL DEFAULT 0.9,
    flag_threshold            REAL DEFAULT 0.55,
    verified_quiz_threshold   REAL DEFAULT 0.80,
    partial_quiz_threshold    REAL DEFAULT 0.50,
    decay_halflife_days       INTEGER DEFAULT 14,
    exam_proximity_compress_days INTEGER DEFAULT 7,
    w1_pyq_recurrence         REAL DEFAULT 0.22,
    w2_pyq_recency            REAL DEFAULT 0.20,
    w3_concept_persistence    REAL DEFAULT 0.10,
    w4_ca_relevance           REAL DEFAULT 0.08,
    w5_syllabus_weight        REAL DEFAULT 0.12,
    w6_graph_centrality       REAL DEFAULT 0.08,
    w7_mastery_discount       REAL DEFAULT 0.20,
    w8_quiz_only_discount     REAL DEFAULT 0.05,
    w9_full_loop_discount     REAL DEFAULT 0.15,
    paper_ids                 TEXT,                  -- JSON: ["paper_ii","paper_iii","paper_iv"]
    created_at                TEXT DEFAULT (datetime('now'))
);
```

### Table: `topics`
```sql
CREATE TABLE topics (
    topic_id          TEXT NOT NULL,
    exam_id           TEXT NOT NULL,
    paper_id          TEXT NOT NULL,               -- 'paper_ii', 'paper_iii', 'paper_iv'
    topic_name        TEXT NOT NULL,
    subtopic_of       TEXT,                        -- parent topic_id for nesting
    topic_level       TEXT DEFAULT 'topic',        -- 'topic' | 'subtopic'
    syllabus_weight   REAL DEFAULT 1.0,            -- w5 raw value
    PRIMARY KEY (topic_id, exam_id),
    CHECK (topic_level IN ('topic', 'subtopic'))
);
-- Note: 'dimension' level is a separate table (dimensions).
-- Gap states and priority formula run at topic/subtopic level only.
```

### Table: `pyq_questions`
```sql
CREATE TABLE pyq_questions (
    question_id       TEXT NOT NULL,
    exam_id           TEXT NOT NULL,
    paper_id          TEXT NOT NULL,
    year              INTEGER NOT NULL,
    question_text     TEXT NOT NULL,
    topic_id          TEXT NOT NULL,
    subtopic_id       TEXT,
    marks             INTEGER DEFAULT 10,          -- IES marks per question
    answer_length     TEXT,                        -- 'short_150' | 'medium_250' | 'long_400'
    key_concepts      TEXT,                        -- JSON array
    question_hash     TEXT UNIQUE,                 -- SHA-256 dedup
    PRIMARY KEY (question_id, exam_id)
);
```

### Table: `topic_base_scores`
```sql
CREATE TABLE topic_base_scores (
    topic_id                  TEXT NOT NULL,
    exam_id                   TEXT NOT NULL,
    paper_id                  TEXT NOT NULL,
    pyq_count                 INTEGER DEFAULT 0,
    distinct_years            INTEGER DEFAULT 0,
    pyq_recurrence_score      REAL DEFAULT 0.0,
    pyq_recency_score         REAL DEFAULT 0.0,
    concept_persistence_score REAL DEFAULT 0.0,
    ca_relevance_score        REAL DEFAULT 0.0,
    graph_centrality_score    REAL DEFAULT 0.0,
    base_priority_score       REAL DEFAULT 0.0,
    computed_at               TEXT,
    PRIMARY KEY (topic_id, exam_id)
);
```

### Table: `user_mastery`
```sql
CREATE TABLE user_mastery (
    user_id               TEXT NOT NULL,
    topic_id              TEXT NOT NULL,
    exam_id               TEXT NOT NULL,
    mastery_level         REAL DEFAULT 0.0,        -- 0.0 to 1.0
    claimed_level         REAL DEFAULT 0.5,        -- user self-declaration
    sar_score             REAL DEFAULT 0.5,        -- self-assessment reliability
    last_quiz_score       REAL,
    quiz_attempt_count    INTEGER DEFAULT 0,
    last_tested_at        TEXT,
    PRIMARY KEY (user_id, topic_id, exam_id)
);
```

### Table: `gap_states`
```sql
CREATE TABLE gap_states (
    user_id               TEXT NOT NULL,
    topic_id              TEXT NOT NULL,
    exam_id               TEXT NOT NULL,
    paper_id              TEXT NOT NULL,
    state                 TEXT NOT NULL DEFAULT 'UNVISITED',
    urgency_multiplier    REAL DEFAULT 1.0,
    flagged_at            TEXT,
    study_started_at      TEXT,
    last_verified_at      TEXT,
    next_review_at        TEXT,
    last_return_quiz_score REAL,
    context_package_hash  TEXT,                    -- hash of last generated context package
    attempt_count         INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, topic_id, exam_id),
    CHECK (state IN ('UNVISITED','FLAGGED','IN_STUDY','PARTIAL','VERIFIED','DECAYING'))
);
```

### Table: `gap_state_events` (Immutable Event Log)
```sql
CREATE TABLE gap_state_events (
    event_id      INTEGER PRIMARY KEY,
    user_id       TEXT NOT NULL,
    topic_id      TEXT NOT NULL,
    exam_id       TEXT NOT NULL,
    from_state    TEXT,
    to_state      TEXT NOT NULL,
    trigger       TEXT NOT NULL,
    -- triggers: 'priority_threshold' | 'study_opened' | 'quiz_passed' |
    --           'quiz_partial' | 'quiz_failed' | 'decay_expired' | 'stale_in_study'
    --           | 'urgency_escalation' | 'exam_proximity_compress'
    quiz_score    REAL,
    priority_score_at_event REAL,
    metadata      TEXT,                            -- JSON for any extra context
    created_at    TEXT DEFAULT (datetime('now'))
);
```

### Table: `context_packages` (Study Briefs)
```sql
CREATE TABLE context_packages (
    package_id        TEXT PRIMARY KEY,            -- UUID
    user_id           TEXT NOT NULL,
    topic_id          TEXT NOT NULL,
    exam_id           TEXT NOT NULL,
    package_hash      TEXT NOT NULL,               -- hash(topic+user_error_history+ca_snapshot)
    brief_text        TEXT NOT NULL,               -- full context package text
    pyq_ids_included  TEXT,                        -- JSON array of PYQ IDs referenced
    ca_events_included TEXT,                       -- JSON array of CA event IDs
    traps_included    TEXT,                        -- JSON array of known traps
    generated_at      TEXT DEFAULT (datetime('now')),
    is_stale          INTEGER DEFAULT 0            -- 0=fresh, 1=stale (new PYQs added)
);
```

### Table: `return_quiz_questions`
```sql
CREATE TABLE return_quiz_questions (
    question_id       TEXT PRIMARY KEY,
    topic_id          TEXT NOT NULL,
    exam_id           TEXT NOT NULL,
    question_text     TEXT NOT NULL,
    question_type     TEXT NOT NULL,               -- 'mcq' | 'concept_check' | 'fill_blank'
    correct_answer    TEXT NOT NULL,
    option_b          TEXT,                        -- MCQ options
    option_c          TEXT,
    option_d          TEXT,
    difficulty        REAL DEFAULT 0.5,
    dimension_id      TEXT,                        -- nullable: set when question tests a specific dimension
    generated_at      TEXT DEFAULT (datetime('now')),
    validation_status TEXT DEFAULT 'pending'       -- 'pending' | 'validated' | 'flagged'
);
```

### Table: `dimensions`
```sql
-- Lowest level of the hierarchy — specific testable concepts within a subtopic.
-- Dimensions are tracking/display units only: no gap_states, no priority formula.
-- Tracking is derived from return_quiz_attempts via dimension_id on questions.
CREATE TABLE dimensions (
    dimension_id      TEXT NOT NULL,
    topic_id          TEXT NOT NULL,   -- parent subtopic_id (must be a subtopic, not a topic)
    exam_id           TEXT NOT NULL,
    dimension_name    TEXT NOT NULL,
    dimension_desc    TEXT,            -- what exactly this dimension tests
    PRIMARY KEY (dimension_id, exam_id),
    FOREIGN KEY (topic_id, exam_id) REFERENCES topics(topic_id, exam_id)
);
```

### Table: `topic_attempt_summary`
```sql
-- Denormalised per-(user, topic, exam) summary updated on every quiz submission.
-- Drives dashboard display without heavy aggregation at render time.
CREATE TABLE topic_attempt_summary (
    user_id           TEXT NOT NULL,
    topic_id          TEXT NOT NULL,
    exam_id           TEXT NOT NULL,
    total_attempts    INTEGER DEFAULT 0,
    correct_attempts  INTEGER DEFAULT 0,
    coverage_pct      REAL DEFAULT 0.0,   -- dimensions_attempted / total_dimensions (0–1)
    flag_impact_score REAL DEFAULT 0.0,   -- weight × (1 - coverage_pct), for flag sorting
    last_updated      TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, topic_id, exam_id)
);
```

### Table: `return_quiz_attempts`
```sql
CREATE TABLE return_quiz_attempts (
    attempt_id        INTEGER PRIMARY KEY,
    user_id           TEXT NOT NULL,
    topic_id          TEXT NOT NULL,
    exam_id           TEXT NOT NULL,
    question_id       TEXT NOT NULL,
    user_answer       TEXT,
    is_correct        INTEGER,                     -- 0 or 1
    time_taken_ms     INTEGER,
    confidence_rating INTEGER,                     -- 1, 2, 3
    session_id        TEXT NOT NULL,
    created_at        TEXT DEFAULT (datetime('now'))
);
```

---

## 5. IES-Specific Adaptations

### Paper Structure and Weight Defaults

| Paper | Topics | Default w5 | Nature |
|---|---|---|---|
| Paper I (GS) | 20–25 broad topics | 0.60 | Broad, low predictability |
| Paper II (Micro + Macro) | 35–40 topics | 1.00 | High repetition, theory-heavy |
| Paper III (Stats + Econometrics) | 25–30 topics | 0.85 | Technical, high repeatability |
| Paper IV (Indian Economy) | 30–35 topics | 0.90 | Current affairs heavy |

### Return Quiz for Descriptive Prep

For descriptive exams, a standard MCQ return quiz is insufficient to verify understanding. Use a 3-tier return quiz:

**Tier 1 — Concept check (mandatory, 3 questions):**
Yes/No + one-line justification questions on the core mechanism.
Example: "Does a rise in government borrowing always crowd out private investment? Why/why not in 2 lines."
Evaluated by Haiku as: correct / partially correct / incorrect.

**Tier 2 — Trap check (mandatory if traps exist, 2 questions):**
MCQ format testing known PYQ traps for this topic.
Example: "Which of the following is NOT a component of M3 in India's monetary aggregates?"

**Tier 3 — Answer framework check (optional, 1 question):**
"List the 4 key points a complete answer on [topic] must cover" — Haiku evaluates coverage.

Total return quiz: 5–6 questions. Score = weighted average (Tier 1: 50%, Tier 2: 35%, Tier 3: 15%).

### Context Package Format for IES

```
IES STUDY BRIEF — [Topic Name] ([Paper])
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Why this matters: appeared X times in IES [years]. Priority rank: [N]/[total].

EXAM-SPECIFIC ANGLE:
IES asks this from [angle] — not [common misconception].
Expected answer length: [150/250/400] words.
Marks typically allocated: [10/15/20].

KNOWN TRAPS (from PYQ wrong options):
• [Trap 1 — specific to real past question]
• [Trap 2]

YOUR PERSONAL GAP:
You got [N] questions on this wrong. Specific weak point: [...]

PASTE THIS TO YOUR AI AGENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
I'm preparing for IES Economics. Explain [topic] with exam focus.
Must cover: [list of key points the answer needs].
Known traps I need to understand: [traps].
After explaining, test me with: [Tier 1 concept check question].
━━━━━━━━━━━━━━━━━━━━━━━━━━━

RETURN HERE after studying to take the 5-question return quiz.
```

---

## 6. User Simulations and Edge Cases

### Simulation 1 — Cold Start User (Day 1, no history)

**Scenario:** User installs system, no quiz history, no declared mastery.
**Problem:** Priority formula has w7=0 (no mastery), w8=0, w9=0. Base priority dominates. ALL high-PYQ topics are FLAGGED simultaneously.
**Result without mitigation:** User sees 40 topics flagged on Day 1. Overwhelmed, abandons system.
**Mitigation:**
- Run a 10-question diagnostic quiz on Day 1 (2 questions per paper) before showing full priority list
- Diagnostic seeds mastery_level values (not zero) and seeds SAR = 0.5
- Priority list filtered to TOP 5 topics on Day 1, expanding by 2 per day as mastery data fills in
- Schema impact: `user_mastery.is_diagnostic_seeded INTEGER DEFAULT 0` — priority list capped until = 1

### Simulation 2 — Panic User (5 days before exam)

**Scenario:** User joins system 5 days before exam. 120+ topics unflagged.
**Problem:** Normal study loop (study → quiz → verify) takes 1–2 days per topic cluster. 5 days is not enough.
**Mitigation:**
- Exam proximity mode triggers at `days_until_exam ≤ 7` (configured in exam_configurations)
- In proximity mode: context packages compressed to "quick brief" (traps only, no deep context)
- Return quiz reduced to 3 questions (Tier 2 only)
- Session composer outputs max 8 topics per day (not paced, just ranked)
- Gap state transitions are faster: PARTIAL → VERIFIED if next quiz ≥ 70% (reduced from 80%)
- Schema impact: `exam_configurations.proximity_verified_threshold REAL DEFAULT 0.70`

### Simulation 3 — Paper-Specific User (Paper II focus only)

**Scenario:** User knows their Paper IV is strong, wants only Paper II prep.
**Problem:** System surfaces Paper IV topics based on PYQ frequency — user ignores them, cluttering the list.
**Mitigation:**
- `user_paper_preferences` table: user can enable/disable papers
- Priority filter: `WHERE paper_id IN (user_enabled_papers)`
- Disabling a paper does not delete mastery data — re-enabling it restores full history
- Schema impact: separate `user_paper_preferences` table (not a column on user_mastery)

```sql
CREATE TABLE user_paper_preferences (
    user_id   TEXT NOT NULL,
    exam_id   TEXT NOT NULL,
    paper_id  TEXT NOT NULL,
    enabled   INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, exam_id, paper_id)
);
```

### Simulation 4 — Inconsistent User (irregular gaps)

**Scenario:** User studies intensively for 3 days, disappears for 5 days, returns.
**Problem 1:** All VERIFIED topics from 3 days ago are now DECAYING simultaneously (halflife = 14 days, but 5 days of no activity means decay started immediately).
**Problem 2:** System floods user with "review these 15 decaying topics" on return.
**Mitigation:**
- On return after > 2 day gap: run a 5-question "warm-up quiz" on previously VERIFIED topics before showing new flags
- Warm-up quiz re-confirms which topics are still retained vs truly decayed
- Only truly failed warm-up topics move to DECAYING → FLAGGED
- Topics passed in warm-up reset `next_review_at` (+halflife from today)
- Schema impact: `gap_states.last_active_at TEXT` — gap_state_events trigger checks this

### Simulation 5 — Expert User (most topics known)

**Scenario:** User has IES background, already knows 60% of topics deeply.
**Problem:** System spends weeks flagging topics user already knows. User declared high mastery but system doesn't trust it (low SAR since no quiz history).
**Mitigation:**
- Allow bulk self-attestation at onboarding: "I know these topics well" → sets claimed_level = 0.85 for selected topics
- SAR starts at 0.5 by default — system will verify claims via return quizzes when those topics are randomly sampled
- Random verification sampling: every 5th topic shown is a random previously-attested topic, regardless of priority score
- If verification passes → SAR increases → system trusts remaining attestations more
- Schema impact: `user_mastery.attestation_source TEXT` — 'self' | 'quiz' | 'diagnostic'

### Simulation 6 — Multi-Attempt Failure on Same Topic

**Scenario:** User has attempted the return quiz on "IS-LM Model" 3 times, failed all 3 (scored < 50%).
**Problem:** Topic keeps coming back as top priority. User is frustrated. The context package isn't helping.
**Mitigation:**
- After 3 failures on same topic: urgency_multiplier caps at 2.0 (prevents permanent top-priority)
- Context package is regenerated with different framing: "You've struggled with this 3 times. Key point you keep missing: [specific trap identified from quiz errors]"
- A "stuck flag" is set in gap_states — visible to user: "You've been stuck on this. Try approaching from [prerequisite concept] first."
- Schema impact: `gap_states.stuck_flag INTEGER DEFAULT 0` set when `attempt_count >= 3 AND last_return_quiz_score < 0.50`

---

## 7. Known Problems and Mitigations

### P1 — Priority Score Inflation for Topics with No Quiz History

**Problem:** w7 (mastery discount) = 0 for any topic never quizzed. High-PYQ topics always score near their base priority regardless of actual user knowledge. System cannot distinguish between "user doesn't know this" and "user knows this well but never tested."

**Mitigation:** During onboarding, claimed_level = 0.5 is the default (not 0.0). This gives every topic a small mastery discount from the start. SAR = 0.5 means the system weights claimed_level at 50% even without quiz validation. Score = w7 × (quiz_score × 0.5 + claimed_level × 0.5) = w7 × (0 × 0.5 + 0.5 × 0.5) = w7 × 0.25. This prevents all topics from simultaneously hitting the flag threshold on Day 1.

### P2 — Context Package Staleness

**Problem:** A context package generated on Day 1 becomes stale when new PYQs are ingested (e.g., IES 2025 results published) or CA events change.

**Mitigation:** Context package has a `package_hash` = SHA-256 of (topic_id + ca_events_snapshot + pyq_count). When CA changes or new PYQs are added, the hash changes. At context package open time, system checks current hash vs stored hash. If different: regenerate. The regeneration is cheap (one Haiku call, < $0.001).

### P3 — Return Quiz Grade Inflation

**Problem:** 5-question MCQs have a 25% random-correct rate. A user who guesses all 5 gets 1–2 correct by chance. A score of 40% (2/5 correct) could be all luck, but system treats it as PARTIAL.

**Mitigation:** Require minimum 3 correct on Tier 2 (trap questions) for PARTIAL qualification. Random success on trap questions is lower because all 4 options are plausible. Schema: `return_quiz_attempts` stores question_type — the quiz scoring function weights Tier 2 at 2x per question.

### P4 — CA Signal Dominance Near Exam

**Problem:** As exam approaches, every piece of current affairs gets boosted (high proximity_to_exam). Topics with weak PYQ history but recent CA mentions get inflated priority. User wastes time on CA-heavy topics at the expense of theory fundamentals.

**Mitigation:** `w4 × ca_relevance_score` is capped at 40% of base_priority_score regardless of raw CA signal. A CA-only topic can never outscore a strong PYQ topic. The cap is a configuration value: `exam_configurations.ca_weight_cap REAL DEFAULT 0.40`.

### P5 — Forgetting Curve Over-Aggressiveness

**Problem:** Default halflife = 14 days. A user who verified 15 topics in Week 1 will have all 15 topics re-enter DECAYING simultaneously in Week 3. System floods with decay reminders.

**Mitigation:** Stagger `next_review_at` by topic importance. Top-5 priority topics get halflife = 10 days. Medium priority: 14 days. Low priority: 21 days. This naturally spreads the decay schedule over 2 weeks. The base halflife is the same — the staggering is applied at VERIFIED transition time based on the topic's priority rank at that moment.

### P6 — Schema Migration Pain (SQLite → PostgreSQL)

**Problem:** If we use any SQLite-specific feature now, the TALE migration becomes painful later.

**Mitigation:** Zero SQLite-isms in the schema as written above. Use TEXT for all dates (ISO-8601 strings), INTEGER for booleans (0/1), no AUTOINCREMENT (use INTEGER PRIMARY KEY which maps to SERIAL in PostgreSQL), no SQLite-specific functions in application code. The migration is: `pg_restore` from a CSV export. No application logic changes.

### P7 — IES vs UPSC Topic Name Collision

**Problem:** "Monetary Policy" is a topic in both IES Paper IV and UPSC Prelims economy. If both exams share a topic namespace, context packages and mastery data bleed across exams.

**Mitigation:** `PRIMARY KEY (topic_id, exam_id)` on every table. topic_id = "monetary_policy" is valid in both "ies_2026" and "upsc_prelims_2027". They are entirely separate rows with separate mastery, gap states, PYQ counts, and context packages. No collision possible by schema design (Decision 1 above).

### P8 — Context Package Quality Degrades for Obscure Topics

**Problem:** A topic with only 1 PYQ in 10 years has a low priority score but it does appear on the syllabus. Its context package will have minimal PYQ trap data. The "traps included" section will be empty. User gets a thin brief.

**Mitigation:** Context package generation checks `pyq_count` before generating. If < 3 PYQs: package format changes to "theory-first" (no traps section, replaced with "model answer structure for IES"). The AI agent prompt template changes too — instead of "understand these traps", it says "explain the theoretical framework and typical IES answer structure for this topic."

### P9 — User Ignores Return Quiz (Study Loop Never Closes)

**Problem:** User opens context package (IN_STUDY), studies with AI agent, but never comes back to take the return quiz. Topic stays IN_STUDY for 48 hours, then reverts to FLAGGED. Repeat. The mastery level never updates.

**Mitigation:**
- After IN_STUDY for > 24 hours: daily session composer opens with return quiz prompt FIRST, before showing new flags
- If user skips return quiz 3 times for the same topic: system stops generating new flags until the pending quiz is submitted
- The "pending quiz count" is shown prominently in the dashboard header: "3 topics pending return quiz"

---

## 8. IES Build Plan (20-Day Window)

Given exam in ~20 days and needing a usable tool in 10 days, leaving 10 days of actual prep:

### Phase 0 — Foundation (Days 1–2)
- Create SQLite DB with full schema above
- Seed `exam_configurations` with IES 2026 values
- Seed `topics` with IES paper taxonomy (Papers II, III, IV) — with `topic_level` set
- Seed `dimensions` table with known testable dimensions per subtopic
- **Pre-populate `gap_states` with UNVISITED rows for every (user, topic, exam) on init**
  — this makes "what's uncovered" a fast `WHERE state = 'UNVISITED'` query, not a slow anti-join
- **Pre-populate `topic_attempt_summary` with zero rows for every (user, topic, exam) on init**
  — dashboard can always read this table, never gets null results
- Write `priority_engine.py` — implements Formula 2 with all 9 weights
- Write `gap_state_machine.py` — all transitions, event logging, `flag_impact_score` updated on every state change
- Write `dashboard.py` — minimal terminal dashboard (coverage % per paper, flag list sorted by impact, attempt counts)
- Test: simulate 10 topics through full UNVISITED → VERIFIED → DECAYING cycle
- **Output:** Working formula + state machine + minimal dashboard visible from Day 1

### Phase 1 — PYQ Ingestion (Days 3–4)
- Download IES PYQs 2019–2024 (last 5 years, Papers II–IV)
- Run through PDF parser (reuse Devthorium's `digital_pdf` parser)
- Haiku classification: extract topic_id, paper_id, year, marks, answer_length per question
- Populate `pyq_questions` table
- Compute `topic_base_scores` (Formula components w1, w2, w3)
- **Output:** Priority list based purely on PYQ data, no user personalization yet

### Phase 2 — Pattern Analysis (Day 5)
- Adapt `eco_schemes_pattern_v2.py` architecture for IES
- IES-specific canonical concept taxonomy per paper
- Generate pattern report: `exports/ies_pattern_2019_2024.md`
- This feeds the context package generator (trap data, key facts per topic)
- **Output:** Haiku-analyzed PYQ cache with traps, concepts per question

### Phase 3 — Priority Engine + Gap Detection (Days 6–7)
- Wire priority formula to real PYQ data
- Build gap detection script: reads mastery + gap_states, outputs daily priority list
- Build diagnostic quiz (10 questions) to seed Day 1 mastery
- CLI interface: `python scripts/session.py --exam ies_2026 --user rahul`
- **Output:** Daily priority list, gap states updating from quiz input

### Phase 4 — Context Package Generator (Day 8)
- Build `context_package.py`: pulls topic data + PYQ traps + CA mentions + user error history
- Generates the formatted study brief (Section 5 format above)
- Caches to `context_packages` table
- CLI: prints brief to terminal + copies AI agent prompt to clipboard
- **Output:** One-command context package for any flagged topic

### Phase 5 — Return Quiz (Day 9)
- Pre-generate 5–6 return quiz questions per high-priority topic (Tier 1 + Tier 2 only at MVP)
- Haiku validation: each question answerable from concept alone
- Build return quiz CLI: 5 questions, collects answers, computes score, updates gap state + mastery
- **Output:** Full study loop closes for the first time

### Phase 6 — Session Composer + Dashboard (Day 10)
- Build `daily_session.py`: reads priority list → outputs today's study plan (top 5 topics, ordered)
- Build text-based dashboard: shows gap states, mastery per paper, pending return quizzes
- Everything runs from CLI, no frontend
- **Output:** Complete usable system — study plan → context package → AI agent → return quiz → repeat

### Days 11–20: Actual IES prep using the system

---

## 9. What This Foundation Enables Later

Every decision above was made with expansion in mind:

| Later need | How foundation handles it |
|---|---|
| Add UPSC Mains | New `exam_id = 'upsc_mains_2027'`, new topics rows, new exam_configurations row. Zero schema change. |
| Add multi-brain (MCQ + descriptive) | brain_id column added to gap_states + user_mastery. Schema change is additive, not destructive. |
| Migrate to PostgreSQL | All schemas are PostgreSQL-compatible. Data copy, no redesign. |
| Add concept graph | `graph_centrality_score` column already in topic_base_scores — starts at 0, populated when graph is built. |
| Add frontend | SQLite → PostgreSQL + FastAPI wrapper. All business logic stays in Python scripts unchanged. |
| Add second user | user_id is already in every primary key. Multi-user just means multiple user_ids. |
| Add CA signal | `ca_relevance_score` column already in topic_base_scores — starts at 0, populated when CA pipeline is built. |

---

## 10. Actual File Structure (as built)

```
Descriptive-exams/
├── docs/
│   └── FOUNDATION.md              ← this file
├── data/
│   ├── ies.db                     ← SQLite WAL, 16 tables, 1219 PYQs + answers
│   └── (batch .txt files appear during active Anthropic batch jobs)
├── .streamlit/
│   └── config.toml                ← Gemini dark theme (primaryColor=#8AB4F8)
├── web/                           ← Streamlit web app (run: streamlit run web/app.py)
│   ├── app.py                     ← Dashboard: paper tabs, Today's Focus, state machine
│   ├── db.py                      ← Shared DB helpers + clean_q() + get_study_brief() etc.
│   ├── styles.py                  ← Shared Gemini CSS: apply_theme(), badge(), chip()
│   └── pages/
│       ├── 1_Model_Answers.py     ← Browse 1219 answers; intro/body/conclusion + diagram
│       ├── 2_Quiz.py              ← Write answer → Sonnet eval → scores + model reveal
│       ├── 3_Study_Brief.py       ← Topic context package; copy-paste to Claude.ai
│       └── 4_My_Progress.py       ← Quiz attempt history + score trends
├── scripts/                       ← One-time setup scripts (all done, don't re-run)
│   ├── setup_all.py               ← Runs stages 1–6 in sequence
│   ├── init_db.py                 ← Stage 1: schema creation
│   ├── seed_topics.py             ← Stage 2: 30 topics + 126 subtopics
│   ├── ingest_pyq.py              ← Stage 3: 1219 PYQs from PDFs
│   ├── generate_rubrics.py        ← Stage 4: Haiku batch rubric extraction
│   ├── compute_base_scores.py     ← Stage 5a: w1+w2+w3+w5 priority scores
│   ├── generate_answers.py        ← Stage 5b: Sonnet batch model answers (done)
│   ├── generate_return_quiz.py    ← Stage 6: MCQ pre-cache — NOT YET RUN
│   ├── session_planner.py         ← Terminal dashboard (superseded by web app)
│   ├── view_answers.py            ← Terminal answer browser (superseded by web app)
│   ├── quiz_descriptive.py        ← Terminal quiz (superseded by web app)
│   └── generate_context.py        ← Terminal study brief (superseded by web app)
├── pdfs/                          ← PYQ PDFs (source for ingestion)
├── cache/                         ← ChromaDB embeddings cache
├── exports/                       ← Output files
└── config/                        ← Config files
```
