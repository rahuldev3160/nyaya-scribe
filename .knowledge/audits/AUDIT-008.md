# AUDIT-008 — Global DB Schema & Indexing Audit
**Date:** 2026-06-21 (Session 43)
**Scope:** All 6 production DBs — ies.db, rbi.db, upsc_eco_opt.db, upsc_gs.db, english.db, nyaya.db
**Method:** 3 parallel subagents running `.schema`, `PRAGMA table_info`, sample data queries
**Bugs found:** 0 new (BUG-028 already fixed); structural gaps catalogued
**Decisions pending:** DECIDE-32 (cross-DB topic linking) + DECIDE-33 (rbi year column) — awaiting Rahul answers

---

## Summary

No live bugs. Five structural gaps that affect discoverability and future analytics:
1. **5 different question_id formats** across DBs — can't standardize retroactively, must document going forward
2. **4 different index prefix conventions** — document, apply to new indexes only
3. **Missing indexes** in ies.db (3), eco_opt.db (5), english.db (2), rbi.db (1)
4. **No FTS5** in any current DB — essay/ethics will be first; IES + RBI need it too
5. **rbi.db has no year column** — recency tracked via `is_recent_dev` flag only

---

## question_id Format Map

| DB | Format | Example | Year in ID? | Topic model |
|---|---|---|---|---|
| ies.db | `{paper}_{seq:04d}` | `ge_01_0001` | No | Normalized FK → topics table |
| rbi.db | `{subject}_{topic}_{seq:03d}` | `env_env_002` | No year column | Denormalized inline strings |
| upsc_eco_opt.db | `{exam}_{paper}_{seq:04d}` | `upsc_p1_0001` | No | Normalized FK → topics table |
| upsc_gs.db | `{paper}_{year}_{seq:02d}` | `gs1_2013_q01` | **Yes — best format** | Normalized FK + paper prefix |
| english.db | `eng_{type}_{seq:03d}` | `eng_essay_001` | No | type_id only (no topics table) |
| essay (planned) | `essay_{section}_{year}_{seq:03d}` | `essay_a_2024_001` | Yes | Normalized FK + junction tables |
| ethics (planned) | `ethics_{section}_{year}_{seq:03d}` | `ethics_a_2024_001` | Yes | Normalized FK + junction tables |

**Verdict:** Cannot rename existing IDs — FK refs, URLs, and attempt records would all break. New content (essay, ethics) follows upsc_gs.db pattern (year-embedded). Existing IDs stay as-is, documented in SCHEMA_CONVENTIONS.md.

---

## Index Coverage Map

### ies.db — 10 indexes (3 gaps)

**Present:**
- `idx_pyq_exam_topic` — `pyq_questions(exam_id, topic_id)`
- `idx_ma_exam_qid` — `model_answers(exam_id, question_id)`
- `idx_topics_exam_level` — `topics(exam_id, topic_level)`
- `idx_gs_user_exam` — `gap_states(user_id, exam_id)`
- `idx_um_user_exam` — `user_mastery(user_id, exam_id)`
- `idx_ue_user` — `user_events(user_id, created_at DESC)`
- `idx_ue_type` — `user_events(event_type, created_at DESC)`
- `idx_sessions_user` — `sessions(user_id)`
- `idx_english_attempts_user` — `english_attempts(user_id, exam_id, created_at DESC)`
- `idx_feedback_created` — `user_feedback(created_at DESC)`

**Missing (add in m047):**
- `descriptive_attempts(user_id, exam_id)` — full scan per user dashboard
- `gap_state_events(user_id, topic_id, exam_id)` — full scan for event history
- `context_packages(user_id, topic_id, exam_id)` — full scan

**Stale tables to DROP (verify no refs first):** `rbi_attempts_new`, `gs4_keywords_new`

---

### rbi.db — 9 indexes (1 gap)

**Present:**
- `idx_questions_subject` — `rbi_questions(subject)` (single col)
- `idx_questions_topic` — `rbi_questions(topic)` (single col)
- `idx_questions_tier`, `idx_questions_difficulty`, `idx_questions_is_trap`, `idx_questions_is_recent`
- `idx_attempts_user` — `rbi_attempts(user_id, question_id)`
- `idx_rbi_sess_user`, `idx_mastery_user`

**Missing (add in m050):**
- `rbi_questions(subject, topic)` composite — queries filtering both columns use only one single-col index

**No year column** — recency via `is_recent_dev BOOLEAN` flag only. Adding `year INTEGER` is Tier 3 (needs Rahul answer on data availability).

**Topic model:** denormalized inline strings (`subject TEXT`, `topic TEXT`, `subtopic TEXT` on question row directly). Unlike every other DB which uses a normalized `topics` table. Not worth migrating unless a specific feature requires it.

---

### upsc_eco_opt.db — 5 indexes (5 gaps vs upsc_gs)

**Present:**
- `idx_pyq_exam_topic` — `pyq_questions(exam_id, topic_id)`
- `idx_ma_exam_qid` — `model_answers(exam_id, question_id)`
- `idx_topics_exam_level` — `topics(exam_id, topic_level)`
- `idx_gs_user_exam` — `gap_states(user_id, exam_id)`
- `idx_um_user_exam` — `user_mastery(user_id, exam_id)`

**Missing (add in m048):**
- `descriptive_attempts(user_id, exam_id, created_at DESC)`
- `pyq_questions(paper_id, year DESC)`
- `gap_states(user_id, exam_id, state)`
- `topic_base_scores(exam_id, base_priority_score DESC)`
- `return_quiz_attempts(user_id, topic_id, exam_id, created_at DESC)`

**Schema drift vs upsc_gs.db** (columns in upsc_gs not in eco_opt):
- `gap_states`: missing `inferred_state`, `inferred_at` (eco_opt has them; upsc_gs doesn't — reversed drift)
- `self_rating`: TEXT in eco_opt (BUG-028 ALTER artifact), INTEGER in upsc_gs
- `return_quiz_questions/attempts`: missing `quiz_tier`, `ai_score`
- `pyq_questions`: missing `secondary_topic_ids`, `cross_paper_flag`, `case_study_preamble`, `staleness_flag`
- `topics`: missing `ca_sensitivity`, `refresh_cycle`

Defer column sync until a feature specifically requires parity.

---

### upsc_gs.db — 15 indexes (well-covered, reference standard)

Prefix: `idx_uggs_`. All hot paths covered. This DB is the reference implementation for index coverage going forward.

---

### english.db — 1 index (2 gaps)

**Present:**
- `idx_english_attempts_user` — `english_attempts(user_id, exam_id, created_at DESC)`

**Missing (add in m049):**
- `english_questions(type_id)` — every type-filter query is a full scan
- `english_keywords(question_id)` — keyword lookup is a full scan

**Design note:** No topics/mastery/gap_states — intentional (pure practice, no progression model). `attempt_id` is TEXT UUID (all other DBs use INTEGER autoincrement) — leave as-is.

---

### nyaya.db — 8 indexes (complete for its scope)

Identity + event store. No content tables. Indexes cover all hot paths (user lookup by google_sub, session lookup by user, event queries by user+type). No gaps.

**Seed drift:** `nyaya_seed.db` is missing `feature_gates`, `user_feature_overrides`, `user_feature_usage`, `user_feedback` tables that exist in live. Fresh deploy from seed would break freemium gating. Seed needs updating before next major deploy.

---

## FTS5 Coverage

| DB | FTS5 present? | Recommended? |
|---|---|---|
| ies.db | No | **Yes** — `pyq_fts` over `pyq_questions(question_text, topic_id)` |
| rbi.db | No | **Yes** — `rbi_fts` over `rbi_questions(question_text, topic, subtopic)` |
| upsc_eco_opt.db | No | Yes (lower priority — smaller question bank) |
| upsc_gs.db | No (yet) | **Yes** — planned in m041 (essay_fts) + m044 (ethics_fts) |
| english.db | No | Low priority (keyword matching table already handles this) |
| nyaya.db | No | No (no text content to search) |

---

## Recommended Migration Plan (Tier 1 — safe, additive)

| Migration | DB | Action |
|---|---|---|
| m047 | ies | Add 3 missing B-tree indexes + DROP stale tables (after grep verification) |
| m048 | upsc_eco_opt | Add 5 missing B-tree indexes |
| m049 | english | Add 2 missing B-tree indexes |
| m050 | rbi | Add 1 composite B-tree index |
| m051 | ies | FTS5 virtual table on pyq_questions |
| m052 | rbi | FTS5 virtual table on rbi_questions |

Then m039–m046 (essay + ethics) pick up with essay/ethics question_id format confirmed.

---

## Pending Decisions (block Tier 3)

**DECIDE-32 (pending Rahul):** Cross-DB topic linking — should "Monetary Policy" in IES and RBI point to a single canonical entity in nyaya.db `master_topics`? Yes → architecture project. No → document column name consistency only (already in T1-A).

**DECIDE-33 (pending Rahul):** rbi.db year column — does source data support year attribution per question? Yes → `ALTER TABLE rbi_questions ADD COLUMN year INTEGER`. No → leave `is_recent_dev` flag as-is.

---

## Proposed SCHEMA_CONVENTIONS.md Rules (to write next session)

1. **question_id:** `{module}_{section}_{year}_{seq:03d}` for all new content (year-embedded, upsc_gs convention)
2. **Index naming:** `idx_{db_abbrev}_{table}_{cols}` — e.g. `idx_ies_da_user_exam` (don't rename existing)
3. **Year:** `INTEGER` calendar year always; never TEXT, never fiscal year notation
4. **topic_id:** slug FK to a `topics` table always; no inline strings in question rows
5. **attempt_id:** `INTEGER PRIMARY KEY AUTOINCREMENT` for all new tables
6. **FTS5:** mandatory for any question/answer table likely to exceed 200 rows
7. **Index prefix:** `idx_{db_abbrev}_` for all new indexes; existing prefixes stay
