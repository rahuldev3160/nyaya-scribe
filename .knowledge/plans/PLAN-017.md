# PLAN-017 — UPSC GS Mains Expansion
**Date:** 2026-06-16 (Session 38–39)
**Status:** PHASE 1 COMPLETE (S39) — Phase 2 PYQ ingestion in progress

### Phase 1 Completion Record (S39 — 2026-06-16)
- migrations/m026–m034 applied to data/upsc_gs.db ✅
  - m034: widened gs4_keywords.keyword_category CHECK constraint (was 7 values, now covers full taxonomy)
- scripts/setup_upsc_gs.py: seeded 15 GS4 thinkers + 123 canonical keywords + 430 synonym expansions ✅
- web/upsc_gs_db.py ✅ | web/app.py upsc_gs_conn plumbing ✅ | scripts/migrate.py ✅
- config/topics_upsc_gs.json: 33 L1 + 131 L2 topics ✅
- Confirmed DB counts: 41 tables, 4 exam configs, 163 topics, 6 ethical frameworks seeded ✅

### Phase 2: PYQ Ingestion (PARTIAL — S39)
Scripts written + fixed: scripts/fetch_upsc_gs_pdfs.py, parse_upsc_gs_pdfs.py, parse_mrunal_pyqs.py, seed_upsc_gs_pyqs.py ✅
Seeded: 221 questions (GS4: 93 ✅, GS1: 62, GS2: 29, GS3: 37)
Coverage gap: GS1-3 missing several years — Mrunal pages are topic samples not year banks
**To complete Phase 2**: Download official UPSC PDFs manually from upsc.gov.in → drop in data/cache/upsc_gs_pdfs/ → run parse_upsc_gs_pdfs.py + seed_upsc_gs_pyqs.py
**Scope:** New `upsc_gs.db` covering all 4 UPSC Mains GS papers + Ethics keyword index + cross-subject linking + CA integration

---

## Architecture Decision

**`upsc_gs.db`** — single new physical SQLite file.
- `exam_id = 'upsc_gs_mains'`
- `paper_id` values: `gs1`, `gs2`, `gs3`, `gs4`
- New Flask connection: `g.upsc_gs_conn` (added to `app.py` before_request + teardown)
- GS content goes under **UPSC nav tab** (not a 5th tab — would break CSS-MOB-001 4-col mobile grid)
- New file: `web/upsc_gs_db.py` following the exact pattern of `web/upsc_db.py`
- Migration files: `m020–m026` using the existing file-based `migrate.py` system (NOT a new `_run_upsc_gs_migrations()` function in app.py — that was the legacy pattern)

---

## Per-Paper Taxonomy Summary

| Paper | L1 sections | L2 topics | L3 subtopics | Total PYQs (2013-2024) |
|-------|------------|-----------|--------------|----------------------|
| GS1 — History/Geo/Culture/Society | 9 | 47 | 182 | ~252 |
| GS2 — Polity/Governance/IR | 7 | 40 | ~145 | ~240 |
| GS3 — Economy/Env/Tech/Security | 7 | 42 | 148 | ~240 |
| GS4 — Ethics/Integrity/Aptitude | 6 clusters | 42 concepts | concept graph | ~215 |
| **Total** | | | | **~935 (850-900 after dedup)** |

---

## PYQ Sources (Verified)

| Paper | Primary Source | Format | Notes |
|-------|---------------|--------|-------|
| All papers 2019-2024 | `upsc.gov.in` official PDFs | Text-layer PDF — pdftotext works | Direct download |
| All papers 2013-2018 | Mrunal.org (`mrunal.org/gsm1` through `/gsm4`) | Machine-readable HTML/text | Best free source; community-verified |
| GS2 IR specifically | `legacyias.com/gs2-international-relations-pyq-2013-2025-2/` | Clean HTML | Best for IR-only extraction |
| GS3 segments | `legacyias.com` per-segment pages | Clean HTML tables | Best structured format found |
| Constitution text | `github.com/Yash-Handa/The_Constitution_Of_India` | JSON | Validate against `indiacode.nic.in` for 106th Amendment (2023) before seeding |
| Cross-check | `github.com/amanbh2/UPSC-Star` | JSON | Do NOT use as primary — use for topic classification validation only |

**OCR path:** For any 2013-2018 official PDF where pdftotext produces <50 words/page → fall through to `pytesseract`. Mrunal is the safer primary for those years.

---

## New Tables (Beyond Standard Schema)

All reuse existing tables (`topics`, `pyq_questions`, `question_rubrics`, `model_answers`, `gap_states`, `gap_state_events`, `user_mastery`, `return_quiz_questions`, `descriptive_attempts`, `topic_base_scores`, `_migrations`).

### Schema additions to `pyq_questions` (via ALTER TABLE in migrations)
```sql
ALTER TABLE pyq_questions ADD COLUMN secondary_topic_ids TEXT;    -- JSON array for multi-topic Qs
ALTER TABLE pyq_questions ADD COLUMN cross_paper_flag INTEGER DEFAULT 0;
ALTER TABLE pyq_questions ADD COLUMN answer_word_count INTEGER;   -- 150 for 10-mark, 250 for 15-mark
ALTER TABLE pyq_questions ADD COLUMN legal_provisions_flag INTEGER DEFAULT 0;
ALTER TABLE pyq_questions ADD COLUMN case_study_preamble TEXT;    -- GS4 case study preamble text
ALTER TABLE pyq_questions ADD COLUMN staleness_flag INTEGER DEFAULT 0; -- 1 = outdated content
```

### Schema additions to `model_answers`
```sql
ALTER TABLE model_answers ADD COLUMN answer_type TEXT DEFAULT 'descriptive'
    CHECK(answer_type IN ('descriptive','analytical','case_study','opinion'));
ALTER TABLE model_answers ADD COLUMN data_vintage_date TEXT;      -- when numbers were current
ALTER TABLE model_answers ADD COLUMN has_stale_ca INTEGER DEFAULT 0;
ALTER TABLE model_answers ADD COLUMN ca_linked_events TEXT;       -- JSON: [event_id, ...]
```

### Schema additions to `topics`
```sql
ALTER TABLE topics ADD COLUMN ca_sensitivity TEXT DEFAULT 'static'
    CHECK(ca_sensitivity IN ('static','ca_light','ca_heavy'));
ALTER TABLE topics ADD COLUMN refresh_cycle TEXT;                 -- 'annual','quarterly','monthly'
```

### Schema additions to `question_rubrics`
```sql
ALTER TABLE question_rubrics ADD COLUMN rubric_type TEXT DEFAULT 'factual'
    CHECK(rubric_type IN ('factual','analytical','position_paper','case_study'));
ALTER TABLE question_rubrics ADD COLUMN constitutional_provisions TEXT;  -- JSON array (GS2)
ALTER TABLE question_rubrics ADD COLUMN current_affairs_hook TEXT;
ALTER TABLE question_rubrics ADD COLUMN data_points_required TEXT;       -- JSON array (GS3)
ALTER TABLE question_rubrics ADD COLUMN synthesis_paper_checks TEXT;     -- JSON (synthesis Qs)
```

### New tables (GS-specific)

**`topic_links`** — cross-paper concept linking (all papers within upsc_gs.db + cross to upsc.db)
```sql
CREATE TABLE topic_links (
    link_id TEXT PRIMARY KEY,
    source_topic_id TEXT NOT NULL, source_paper_id TEXT NOT NULL, source_exam_id TEXT NOT NULL DEFAULT 'upsc_gs_mains',
    target_topic_id TEXT NOT NULL, target_paper_id TEXT NOT NULL, target_exam_id TEXT NOT NULL,
    link_type TEXT NOT NULL CHECK(link_type IN (
        'historical_origin','constitutional_basis','ethical_dimension','policy_implementation',
        'geo_economic_link','ir_domestic_nexus','centre_state_fiscal','society_to_development','technology_policy'
    )),
    link_strength REAL NOT NULL DEFAULT 0.5 CHECK(link_strength >= 0.0 AND link_strength <= 1.0),
    link_note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(source_topic_id, target_topic_id, link_type)
);
```

**`ca_events`** — current affairs linked to GS topics
```sql
CREATE TABLE ca_events (
    event_id TEXT PRIMARY KEY,           -- 'ca_2025_01_001'
    event_date TEXT NOT NULL,
    headline TEXT NOT NULL,              -- max 150 chars
    event_summary TEXT,                  -- max 200 words, exam-context language
    source TEXT NOT NULL CHECK(source IN ('PIB','Hindu','IE','LiveMint','MEA','RBI','NITI','PRS','MoEFCC','ISRO','SupremeCourt','Mint','ET','Manual')),
    source_url TEXT,
    event_type TEXT NOT NULL CHECK(event_type IN ('policy','legislation','judgment','international','environment','science_tech','disaster','economic_data','governance','social')),
    affected_gs_topics TEXT,             -- JSON: [{paper_id, topic_id, relevance_score}]
    exam_relevance_tier INTEGER DEFAULT 2 CHECK(exam_relevance_tier IN (1,2,3)),
    staleness_date TEXT,                 -- ISO date; NULL = never stales (e.g. legislation)
    staleness_reason TEXT,
    is_stale INTEGER DEFAULT 0,
    added_by TEXT DEFAULT 'system',
    verified_at TEXT,
    added_at TEXT DEFAULT (datetime('now'))
);
```

**`ca_topic_links`** — normalised junction for topic-based CA queries
```sql
CREATE TABLE ca_topic_links (
    link_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES ca_events(event_id) ON DELETE CASCADE,
    paper_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    relevance_score REAL DEFAULT 1.0,
    link_source TEXT DEFAULT 'auto' CHECK(link_source IN ('auto','human')),
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id)
);
```

**`government_schemes`** — GS2/GS3 scheme reference (~150 schemes at seed)
```sql
CREATE TABLE government_schemes (
    scheme_id TEXT PRIMARY KEY, scheme_name TEXT NOT NULL, ministry TEXT NOT NULL,
    launch_year INTEGER, objective TEXT, budget_outlay TEXT,
    beneficiary_group TEXT, gs_topic_ids TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','merged','renamed','discontinued')),
    renamed_to TEXT, merged_into TEXT,
    upsc_ask_frequency TEXT DEFAULT 'low' CHECK(upsc_ask_frequency IN ('high','medium','low')),
    last_verified_at TEXT, created_at TEXT DEFAULT (datetime('now'))
);
```

**`committees_index`** — GS2 committees/commissions
```sql
CREATE TABLE committees_index (
    committee_id TEXT PRIMARY KEY, committee_name TEXT NOT NULL, year INTEGER,
    mandate TEXT, key_recommendations TEXT,   -- JSON array of top 5
    gs2_topic_ids TEXT, pyq_question_ids TEXT,
    status TEXT CHECK(status IN ('implemented','partial','pending','rejected'))
);
```

**`constitution_index`** — GS2 constitutional provisions (seedable from GitHub JSON)
```sql
CREATE TABLE constitution_index (
    article_id TEXT PRIMARY KEY,             -- 'Art_21', 'Art_368', 'Sch_7'
    article_number TEXT NOT NULL, part_number TEXT, schedule_number TEXT,
    short_title TEXT NOT NULL,
    amendment_history TEXT,                  -- JSON: [{amendment_no, year, change_summary}]
    current_status TEXT,                     -- 'in_force'|'modified'|'repealed'
    gs2_topic_ids TEXT, pyq_question_ids TEXT, landmark_cases TEXT   -- JSON array
);
```

**`bilateral_relations`** — GS2 IR tracker
```sql
CREATE TABLE bilateral_relations (
    relation_id TEXT PRIMARY KEY,            -- 'india_china'
    country_name TEXT NOT NULL, region TEXT,
    relationship_tier TEXT, key_agreements TEXT, key_friction_points TEXT,
    recent_developments TEXT, ca_sensitivity TEXT DEFAULT 'high',
    pyq_question_ids TEXT, data_as_of TEXT   -- ISO date staleness marker
);
```

**GS3 auxiliary tables:**
- `budget_snapshots (budget_year, line_item, value, gs3_topic_id, source_doc, updated_at)` — perishable Budget numbers
- `economic_indicators (indicator_id, indicator_name, current_value, target_value, as_of_date, source, gs3_topic_id, is_stale)` — triggers model answer staleness warnings
- `env_conventions (convention_id, full_name, year_adopted, india_signatory, key_provisions, india_commitments, last_cop, cop_outcomes, upsc_frequency, ca_sensitivity, updated_at)`
- `protected_areas (pa_id, pa_name, pa_type, state, hotspot, area_sqkm, key_species, gs3_relevance, upsc_asked)`
- `tech_topic_versions (topic_id, version_date, tech_snapshot, is_superseded, superseded_by)` — S&T staleness tracking
- `security_frameworks (framework_id, full_name, enacted_year, key_provisions, nodal_agency, current_status, lwe_relevance, cyber_relevance, border_relevance, upsc_frequency, last_updated)`
- `section_weight_overrides (paper_id, section_name, floor_priority, w5_multiplier)` — critical for DM (floor_priority=0.40)

**GS4 Ethics tables:**
- `gs4_concepts (concept_id, concept_name, concept_category, formal_definition, upsc_usage_pattern, typical_question_angle, prerequisite_concept_ids, related_thinker_ids, cross_paper_topic_ids, keyword_tags, ask_frequency, centrality_score)`
- `gs4_keywords (keyword_id, keyword_text, canonical_form, synonyms, keyword_category, concept_ids, created_at)`
- `gs4_keyword_synonyms (synonym_id, keyword_text, canonical_keyword_id, source)` — handles probity=integrity=uprightness
- `gs4_question_keywords (question_id, keyword_id, relevance_score, is_primary)` — junction
- `gs4_thinkers (thinker_id, name, era, school_of_thought, key_works, core_concepts, upsc_relevance_score, most_cited_quote, typical_question_angle, years_appeared, concept_links, indian_governance_application, common_mistake)`
- `gs4_case_study_templates (template_id, scenario_type, scenario_description, core_ethical_conflict, recommended_frameworks, answer_structure, stakeholder_type_list, common_dilemma_patterns, word_target, difficulty, upsc_frequency, last_appeared_year)`
- `gs4_ethical_frameworks (framework_id, framework_name, framework_short, key_principle, upsc_usage_pattern, answer_trigger, thinker_ids, upsc_relevance_score, typical_question_type, common_pitfalls)`
- `practice_cases (case_id, case_source, template_id, scenario_text, word_count, question_parts, concept_tags, keyword_ids, difficulty, generation_model, model_answer, rubric_json, human_reviewed, created_at)`

**Cross-paper:**
- `eco_opt_bridges (bridge_id, gs_topic_id, gs_paper_id, eco_opt_topic_id, eco_opt_paper_id, bridge_type, bridge_note, opt_mastery_threshold)` — GS3↔Economics Optional Python-merge
- `synthesis_questions (synth_id, question_text, required_papers, required_topic_ids, synthesis_type, marks_equivalent, word_limit, difficulty, source_pyq_year, ca_event_ids, is_ca_triggered, priority_score)`
- `bridge_topic_scores (topic_id, inbound_link_count, avg_link_strength, is_bridge)` — materialised, not live query

---

## Priority Formula Adaptations by Paper

### GS1 (History/Geo/Culture/Society)
```
w1=0.18, w2=0.22, w3=0.12, w4=0.12, w5=0.15, w6=0.06
ca_weight_cap=0.50, decay_halflife_days=10
Key: syllabus_floor_score for Art & Culture subtopics with 0 PYQs
```

### GS2 (Constitution section)
```
w1=0.25, w2=0.12, w3=0.18, w4=0.05, w5=0.15, w6=0.05
Key: persistence >> recency for static constitutional provisions
```

### GS2 (IR section)
```
w1=0.18, w2=0.20, w3=0.06, w4=0.22, w5=0.10, w6=0.04
ca_weight_cap=0.55, stale_after_days=180 for IR model answers
Key: w4 goes from IES default 0.08 → 0.22; pending legislation stale in 30 days
```

### GS3 (Economy)
```
w1=0.30, w2=0.25, w3=0.15, w4=0.20, w5=0.05, w6=0.05
Key: placeholder tokens in model answers for volatile numbers (fiscal deficit %, repo rate)
```

### GS3 (Technology)
```
w1=0.15 (computed at L2 level, not L3), w2=0.35, w3=0.10, w4=0.35, w5=0.05, w6=0.00
Key: recurrence MUST be counted at L2 parent topic, not L3 mission/product level
```

### GS3 (Disaster Management)
```
w1=0.15, w2=0.10, w3=0.20, w4=0.10, w5=0.40, w6=0.05
floor_priority=0.40 (only 16 PYQs in 12 years; formula alone will score DM near zero)
```

### GS4 (Ethics)
```
w1 = concept_frequency (distinct years concept tagged / 13)  — NOT question recurrence
w2 = 0.20 (recency, unchanged)
w3 = 0.20 (persistence — multi-year span bonus)
w4 = 0.10 (CA-driven: corruption scandal → conflict_of_interest boosted)
w5 = 0.15 (syllabus distribution weights from frequency table)
w6 = 0.10 (concept dependency graph centrality — PageRank over gs4_concept_dependencies)
is_foundational flag on concepts: always surfaced regardless of priority score
```

---

## Ethics-Specific Architecture

### Keyword Index Build Strategy
1. Manual seed: 12 canonical concepts → keyword rows + synonym table
2. Haiku batch over all 215 GS4 PYQs: extract 3-7 keywords per question
3. Python fuzzy-match → synonym table; unmatched → manual review queue
4. Cross-paper links: GS4 concepts → GS2/GS3 topic entries via `gs4_cross_paper_links`
5. Ongoing: new PYQs auto-run Haiku extraction + normalise

### Thinkers (Top 5 by UPSC relevance)
1. Gandhi (0.97) — means-ends inseparability, Satyagraha, Trusteeship
2. Vivekananda (0.93) — service as worship, character, inner strength
3. Kant (0.90) — Categorical Imperative, duty, dignity
4. Aristotle (0.88) — Virtue Ethics, eudaimonia, phronesis
5. Ambedkar (0.88) — Constitutional morality over social morality, dignity

### Return Quiz Format (3-tier)
- **Tier 1** (10%): MCQ — concept definition. Auto-graded.
- **Tier 2** (30%): Short answer (80-120 words). Haiku evaluates on 3 criteria: concept accuracy, framework citation, governance grounding.
- **Tier 3** (60%): Mini case study (250 words). Sonnet evaluates on 5 criteria. **Mandatory for VERIFIED state.**

VERIFIED requires Tier 3 score ≥ 14/18. GS4 is **self-assess only** — no AI scoring of full descriptive answers (no objectively correct answer exists).

### Case Study Templates (10 types, by frequency)
1. CST-002: Hierarchical/Political Pressure (9 appearances 2013-2024)
2. CST-007: Corruption/Misuse of Office (8)
3. CST-003: Whistleblowing Dilemma (7)
4. CST-001: Official Duty vs. Personal Obligation (6)
5. CST-005: Development vs. Environment (6)
...etc.

---

## Cross-Paper Link Taxonomy (9 types)

| Code | Type | Example |
|------|------|---------|
| LT-01 | `historical_origin` | GS1 colonial decentralisation → GS2 Art. 245-263 |
| LT-02 | `constitutional_basis` | GS2 Art. 21A → GS3 RTE implementation |
| LT-03 | `ethical_dimension` | GS2/GS3 land acquisition → GS4 justice/rights dilemma |
| LT-04 | `policy_implementation` | GS2 scheme design → GS3 economic mechanism |
| LT-05 | `geo_economic_link` | GS1 Western Ghats → GS3 environment regulation |
| LT-06 | `ir_domestic_nexus` | GS2 Paris Agreement → GS3 renewable targets |
| LT-07 | `centre_state_fiscal` | GS2 Finance Commission → GS3 fiscal devolution |
| LT-08 | `society_to_development` | GS1 women/caste → GS2 social justice → GS3 economy |
| LT-09 | `technology_policy` | GS3 AI → GS2 DPDP Act → GS4 surveillance ethics |

30 critical cross-paper links inventoried (see agent output for full table).

---

## CA Integration

### Staleness Rules
| event_type | staleness_date logic |
|------------|---------------------|
| `economic_data` | event_date + 90 days (quarterly release supersedes) |
| `international` | event_date + 180 days |
| `legislation` | NULL (permanent until repealed/amended) |
| `judgment` | NULL (permanent until overturned) |
| `environment` | event_date + 365 days (annual COP cycle) |
| `science_tech` | NULL default; admin sets on generation change |
| `policy` | event_date + 365 days |
| `governance` | event_date + 730 days |
| `social` | event_date + 1095 days (NFHS cadence) |

### CA Update Workflow
- **Launch (MVP):** Manual weekly admin entry via `/admin/ca/add` route. ~5-10 events/week, ~30 min.
- **Ideal (post-traction):** Weekly Haiku batch (RSS → extraction → approval queue). Cost ~$0.13/week.

---

## New Blueprints Needed

| Blueprint | Route | Mirrors |
|-----------|-------|---------|
| `gs_dashboard_bp.py` | `/gs` | `upsc_dashboard_bp.py` exactly |
| `gs_quiz_bp.py` | `/gs/mains` | `upsc_bp.py` |
| `gs4_ethics_bp.py` | `/gs/ethics` | New — concept browser, thinker directory, keyword search, case study practice, Tier 1-3 return quiz |

Navigation: GS enters via UPSC tab (toggle: "Economics Optional" / "GS Mains"). No 5th bottom-nav tab.

`upsc_dashboard_bp.py` (Economics Optional) requires zero changes.

---

## Content Pipeline (5 Phases)

### Phase 1 — Structure (no AI, ~2-3 hours)
- Write migration files `m020–m026`
- Write `scripts/setup_upsc_gs.py` to create seed DB with taxonomy + reference data
- Manually define ~77 topics across GS1-4
- Seed `exam_configurations`, `gs4_thinkers` (15), `gs4_keywords` (~200), `gs4_concepts` (42), `gs4_case_study_templates` (10), `government_schemes` (50 initial)
- Pre-populate `gap_states` UNVISITED rows and `topic_base_scores` zeros

### Phase 2 — PYQ Ingestion
- Download: 2019-2024 from upsc.gov.in (text PDFs), 2013-2018 from Mrunal
- Write `clean_gs_q(text, paper_id)` — handles GS-specific page headers, mark indicators
- Haiku batch classification (all 4 papers together): output `primary_topic_id`, `secondary_topic_ids`, `cross_paper_flag`, `answer_word_count`, `legal_provisions_flag`
- GS4 uses divergent prompt: concept extraction + keyword tags (not topic classification)
- Handle GS4 case study preambles: store in `case_study_preamble` column

### Phase 3 — AI Content Generation (Anthropic Batch API)
- Sonnet batch: rubric generation (GS rubrics need `constitutional_provisions`, `current_affairs_hook`, `data_points_required` fields beyond IES defaults)
- Sonnet batch: model answer generation (GS1-3: 150/250 words; GS4 case studies use dilemma/stakeholder/frameworks/recommendation structure)
- GS3 model answers: use placeholder tokens for volatile numbers (`[FISCAL_DEFICIT_FY26]`) filled at render from `economic_indicators` table
- Haiku batch: GS4 keyword extraction (215 Ethics questions → keyword tags)
- 1 Sonnet call: GS4 thinker database initialization

### Phase 4 — Scoring and Indexing
- Run `compute_base_scores.py` (add `"upsc_gs_mains": "upsc_gs.db"` to EXAM_DB_MAP — zero code change)
- Seed `topic_links` (cross-paper): AI-assisted first draft + manual review
- Seed `eco_opt_bridges` (GS3↔Economics Optional): 6 highest-priority pairs manually
- Build `bridge_topic_scores` materialised table
- Seed `government_schemes`, `committees_index`, `env_conventions` (manual curation)

### Phase 5 — Return Quiz + Ethics Practice
- GS1-3: `generate_return_quiz.py` with `exam_id="upsc_gs_mains"` + paper_id param (no code change needed)
- GS4: generate Tier 1 (MCQ) via existing script; generate Tier 2/3 with new `quiz_type` column
- Generate 50 AI practice case studies (5 per template × 10 templates): Haiku scenarios + Sonnet model answers, `human_reviewed=0` until spot-checked

---

## Cost Estimate

| Phase | Model | Calls | Estimated Cost |
|-------|-------|-------|---------------|
| Haiku classification | Haiku 3.5 batch | 950 | $0.04 |
| Sonnet rubric generation | Sonnet 4.5 batch | 950 | $1.50 |
| Sonnet model answers | Sonnet 4.5 batch | 950 | $2.71 |
| Haiku keyword extraction GS4 | Haiku 3.5 batch | 215 | $0.01 |
| Sonnet return quiz GS1-3 | Sonnet 4.5 batch | 77 topics | $0.18 |
| GS4 thinker/concept seeding | Sonnet 4.5 | 2-3 calls | $0.10 |
| **Total** | | | **~$4.54** |
| **With 2× re-run buffer** | | | **~$9-10** |

DB file size: ~4-5 MB (well within Railway's limits).

---

## Key Edge Cases to Handle

1. **2013-2018 PDF OCR**: pdftotext first → if <50 words/page → pytesseract fallback. Post-extraction check: abort if >20% of texts under 50 chars.
2. **Multi-topic GS questions** (~30% of GS1): `pyq_topic_links` junction + `secondary_topic_ids` JSON. Primary topic scores fully; secondary topics score at 0.5× weight.
3. **Art & Culture near-zero PYQs**: `syllabus_floor_score` field in `topic_base_scores` — apply floor when `base_priority_score < floor AND syllabus_weight > 0.5`.
4. **GS3 Economy / Economics Optional overlap**: Never set GS3 priority to zero based on Optional `gap_state`. `bridge_type = 'theory_only'` caveat means mastery doesn't transfer.
5. **Disaster Management thin PYQ signal**: `floor_priority = 0.40` + `w5 = 0.40` for DM section in `section_weight_overrides`.
6. **IR staleness**: 180-day auto-flag on model answers; pending legislation = 30-day window.
7. **GS4 AI scoring**: Disabled for descriptive answers (`ai_scoring_enabled=False` for `paper_id='gs4'`). Tier 3 mini-case uses Sonnet with explicit instruction "do not penalise valid alternative ethical stances."
8. **SYNC-001 in profile_bp**: Must add `upsc_gs.db` short-lived direct connection for cross-DB stats aggregation (same pattern as BUG-021 fix).
9. **JINJA2-001 compliance**: All new table columns named to avoid `items`, `keys`, `values`, `get` — enforced throughout schema design.
10. **Budget number placeholders**: GS3 model answers use `[FISCAL_DEFICIT_FY26]` tokens filled at render; `economic_indicators.is_stale = 1` triggers banner on topic page.

---

## Implementation Order (Parallelism Map)

```
Phase 1: Schema + seed (human task, ~3 hrs)
    ↓
Phase 2: PYQ download + clean + ingest (can start GS1 while GS3 downloads)
    ↓
Phase 3: Run Haiku batch (classification) → Sonnet batch (rubrics) → Sonnet batch (answers)
         [GS1-3 and GS4 can run in parallel — different prompt templates]
    ↓
Phase 4: Scoring + topic_links seeding (parallel: scoring vs. manual link curation)
    ↓
Phase 5: Return quiz generation (GS1-3 automated, GS4 requires new quiz_type support first)
    ↓
Blueprint development can start after Phase 1 (DB exists) — no need to wait for content
```

---

## Files to Create/Modify

**New files:**
- `web/upsc_gs_db.py` — DB connection helper
- `web/blueprints/gs_dashboard_bp.py`
- `web/blueprints/gs_quiz_bp.py`
- `web/blueprints/gs4_ethics_bp.py`
- `migrations/m020_upsc_gs_core_tables.py` through `m026_upsc_gs_pyq_columns.py`
- `scripts/setup_upsc_gs.py` — seed creator
- `scripts/clean_gs_q.py` — GS-specific PDF cleaning
- `scripts/compute_bridge_scores.py` — materialise bridge_topic_scores
- `scripts/load_upsc_gs_pyqs.py` — post-deploy PYQ loader

**Modified files:**
- `web/app.py` — add `_UPSC_GS_DB_PATH`, `_boot_db("upsc_gs")`, `g.upsc_gs_conn` open/close, register 3 new blueprints
- `scripts/migrate.py` — add `"upsc_gs"` to `DB_PATHS`
- `scripts/compute_base_scores.py` — add `"upsc_gs_mains": "upsc_gs.db"` to `EXAM_DB_MAP`
- `scripts/generate_return_quiz.py` — add `quiz_type` column support for Tier 2/3 GS4 format

---

## Status
- [x] Research complete (all 6 agents, S38)
- [ ] Phase 1: Schema + migrations + seed setup
- [ ] Phase 2: PYQ ingest pipeline
- [ ] Phase 3: AI content generation batches
- [ ] Phase 4: Scoring + indexing + manual seeding
- [ ] Phase 5: Return quiz + practice cases
- [ ] Blueprint development
- [ ] Navigation integration
- [ ] Deploy to Railway
