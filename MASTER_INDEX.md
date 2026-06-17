# MASTER_INDEX — Descriptive Exams (Nyaya Scribe)
Created: 2026-06-16 (Session 39)
Updated: 2026-06-16 (Session 41)

---

## How to use
- Look up any architectural artefact by TYPE-ID
- Cross-reference: `.knowledge/INDEX.md` has bugs/audits/plans; this has decisions and patterns
- Add every new DECIDE, RISK, GUARD, SCHEMA, METHOD, SIGNAL inline — never defer to session end

---

## DECIDE — Architectural Decisions

| ID | Decision | Why | Rejected Alternative | Location |
|----|----------|-----|---------------------|----------|
| DECIDE-01 | All 4 exams kept equal in UI; no exam elevated to primary | Rahul: app is for annual use across multiple exam cycles, user progress persists forever | UPSC-primary default with others as archive | base.html mobile-nav, all dashboards |
| DECIDE-02 | Dead UI features removed from nav/routes; exam-specific data/progress never deleted | App built for multi-year use; next year's candidates need past-exam data | Delete all RBI/IES-specific features |  web/templates/ |
| DECIDE-03 | Quick Drill (RBI-only shortcut) demoted to mobile More sheet; UPSC promoted to primary nav slot 3 | UPSC is a full exam domain, not a shortcut; CSS-MOB-001 allows exactly 4 nav tabs | Keep Quick Drill as permanent primary tab | base.html lines 91–102 |
| DECIDE-04 | pyq_questions uses `answer_length TEXT` (e.g. "150 words") not `word_limit INTEGER`; `topic_id NOT NULL` with L1 fallback | Actual schema from m026 migration; agent's assumed schema was wrong | Use word_limit INTEGER + nullable topic_id | migrations/m026, scripts/seed_upsc_gs_pyqs.py |
| DECIDE-05 | Mrunal.org is not sufficient for GS1-3 PYQ coverage — official UPSC PDFs required | Mrunal pages are topic-overview samples, not comprehensive year banks; 221 total vs ~800 expected | Rely on Mrunal as sole source | scripts/parse_mrunal_pyqs.py |
| DECIDE-06 | gs4_keywords.keyword_category CHECK constraint widened from 7 to ~22 values via m034 migration | Original 7-value constraint (value/virtue/principle/governance/psychological/philosophical/governance_term) was designed for a narrower taxonomy than the full GS4 keyword index needed | Remap all keywords to the 7 original categories | migrations/m034_upsc_gs_widen_keyword_category.py |
| DECIDE-07 | GS4 synonym seed uses source='human' not 'seed' | gs4_keyword_synonyms.source CHECK(source IN ('auto','human')) — 'seed' violates constraint, INSERT OR IGNORE silently skips | Add 'seed' to CHECK constraint | scripts/setup_upsc_gs.py seed_synonyms() |
| DECIDE-08 | UPSC GS Mains enters via UPSC tab toggle (not a 5th bottom nav tab) | CSS-MOB-001: exactly 4 mobile nav tabs; 5th tab breaks the mobile grid | New 5th bottom tab for GS | upsc_dashboard.html (planned), PLAN-017 |
| DECIDE-09 | upsc_gs.db is a separate physical DB file (not tables inside upsc_eco_opt.db) | GS Mains has 41 tables; embedding in upsc_eco_opt.db would bloat it and require schema migration of existing data | Add GS tables to upsc_eco_opt.db | web/upsc_gs_db.py, web/app.py |
| DECIDE-10 | Implicit tracking only — no manual Verify/Mark Partial/Reset buttons anywhere | Even creator couldn't use it; Duolingo/Khan Academy never ask users to self-report mastery; behavioral signals are more accurate | Keep manual buttons with better UX | All dashboard + quiz templates |
| DECIDE-11 | UPSC GS Mains is the primary design template for Phase 1 UI redesign | Largest audience, freshest build, no legacy patterns to untangle; replicate pattern to IES/RBI after | Nail IES first (older, more legacy) | .knowledge/plans/UI-REDESIGN-001.md (S40 version) |
| DECIDE-12 | Partial-free freemium: model answers for 2022–2024 free, pre-2022 premium | Free reference library drives acquisition (note-takers); older PYQs drive upgrade from serious aspirants | Fully free model answers OR fully gated | feature_gates.gate_id='model_answers_full' |
| DECIDE-13 | 15 AI evaluations/month free quota; adjustable via feature_gates.quota_free (no redeploy) | Usage-based gate converts better than feature-hide gate (SuperKalam/Coursera pattern) | Hard feature gate (0 free evaluations) | migrations/m035_feature_gates.py |
| DECIDE-14 | PYQ prev/next navigation moves within current filter context (not full paper or full exam) | Most intuitive — user controls the context; avoids disorienting navigation across unrelated topics | Navigate within full paper (all ~215 GS4 Qs) | Planned in pyq_browse_bp.py (Phase 1) |
| DECIDE-15 | Photo evaluation (handwritten → Claude Vision OCR + eval) built in Phase 2 alongside freemium | Biggest moat vs SuperKalam/Prayas.ai (UPSC is pen-paper exam); premium feature, natural pairing | Next session separate sprint | Planned route: POST /practice/submit-photo |
| DECIDE-16 | Current quiz has NO live AI evaluation; submit stores answer, user self-compares vs model answer | Discovery during audit: scores_json/weighted_score columns exist but never populated in web routes | Assumed AI eval was already live | web/blueprints/ies_quiz_bp.py (quiz_submit writes no AI score) |
| DECIDE-17 | cache.db (cross-exam stats aggregation) deferred to Phase 1 | Not needed until dashboard readiness score is built; Phase 0 is foundation only | Build cache.db in Phase 0 | Planned: data/cache.db migration m038 |
| DECIDE-18 | `self_rating` is TEXT ('got_it'/'partial'/'missed'), not numeric — all SQL must use CASE expression | SQLite silently coerces TEXT * 2.0 → 0; discovered S41 when readiness scores were always 0 | Use `self_rating * 2.0` (returns 0) | web/db.py, dashboard_bp.py, upsc_dashboard_bp.py, compute_inferred_states.py |
| DECIDE-19 | `inferred_state` uses canonical gap_states taxonomy (UNVISITED/FLAGGED/IN_STUDY/VERIFIED/DECAYING) | Planning agent caught mismatch before code shipped; non-canonical values (READY/CRUNCH/SHAKY) have no display map | Separate inferred taxonomy with its own display map | compute_inferred_states.py infer_state() |
| DECIDE-20 | Phase 2a = text AI scoring only; photo eval deferred to Phase 2b | Prevents 3-feature session that ships none cleanly; photo eval needs Pillow + new blueprint | Build photo + text scoring together in Phase 2 | ies_quiz_bp.py (Phase 2a done); photo_eval_bp.py (pending Phase 2b) |
| DECIDE-21 | AI scoring uses `claude-haiku-4-5-20251001` (not Sonnet) | Fastest, cheapest, sufficient for structured tool-use 5-dimension scoring; Sonnet overkill at 15 free evals/month | claude-sonnet-4-6 for quality | web/blueprints/ies_quiz_bp.py _score_answer() |
| DECIDE-22 | `can_use_feature(user_id, gate_id)` wraps has_feature + quota check — the atomic gate call | has_feature() checks boolean only; quota enforcement was missing entirely (planning agent caught this) | Check has_feature + get_monthly_usage inline at each callsite | web/db.py can_use_feature() |
| DECIDE-23 | UPSC optional subjects = separate DB per optional, lazy-loaded by user enrollment; `_UPSC_OPT_DB_MAP` in app.py maps optional code → path; `g.upsc_conn` stays as "user's active UPSC optional" | Maintains one-DB-per-exam pattern; zero blueprint changes for new optionals; `exam_id` in every PK already handles schema isolation | Single `upsc_optionals.db` with shared connection | web/app.py `_UPSC_OPT_DB_MAP`; rename: upsc.db → upsc_eco_opt.db (S42) |

---

## SCHEMA — DB Table Designs

| ID | Table / Change | DB | Migration | Notes |
|----|---------------|-----|-----------|-------|
| SCHEMA-01 | upsc_gs.db — 41-table core schema (pyq_questions, topics, model_answers, rubrics, gap_states, mastery, etc.) | upsc_gs.db | m026–m033 | See PLAN-017.md for full spec |
| SCHEMA-02 | gs4_keywords — keyword_category CHECK widened to 22 values | upsc_gs.db | m034 | SQLite requires table recreate to change CHECK; done via CREATE+INSERT+DROP+RENAME |
| SCHEMA-03 | gs4_thinkers — 15 rows (Gandhi→Nussbaum) | upsc_gs.db | setup_upsc_gs.py seed | upsc_relevance_score 0.68–0.97 |
| SCHEMA-04 | gs4_keywords — 123 canonical ethics keywords + 430 synonym expansions | upsc_gs.db | setup_upsc_gs.py seed | categories: core_value/ethical_theory/governance_ethics/etc. |
| SCHEMA-05 | pyq_questions — 221 rows seeded (GS4: 93, GS1: 62, GS2: 29, GS3: 37) | upsc_gs.db | scripts/seed_upsc_gs_pyqs.py | GS1-3 coverage gap; needs official PDFs |
| SCHEMA-06 | feature_gates + user_feature_overrides + user_feature_usage — freemium gating tables | nyaya.db | m035_feature_gates.py | 5 gates seeded; admin toggles is_enabled_for_free/quota_free without redeploy |
| SCHEMA-07 | gap_states.inferred_state + gap_states.inferred_at — implicit tracking columns | ies.db, upsc_eco_opt.db | m036, m037 | Populated by compute_inferred_states.py (written S41); canonical taxonomy UNVISITED/FLAGGED/IN_STUDY/VERIFIED/DECAYING |
| SCHEMA-08 | descriptive_attempts.scores_json (TEXT) + weighted_score (REAL) — AI evaluation output | ies.db | In original CREATE TABLE (no dedicated migration) | Populated by _score_answer() in ies_quiz_bp.py since S41; format: {dimensions:{5 keys}, weighted_score, feedback, model} |

---

## PLAN — Feature Plans

| ID | Title | Status | Location |
|----|-------|--------|----------|
| PLAN-017 | UPSC GS Mains expansion — upsc_gs.db + all 4 papers + GS4 Ethics index | Phase 1 ✅ · Phase 2 partial · Phase 3 pending | .knowledge/plans/PLAN-017.md |
| UI-REDESIGN-001 | Cross-exam UI cleanup — noise reduction, mobile nav fix, visual grouping | Phase 1 ✅ (11 changes) · Pending: GS toggle, English Insights audit | .knowledge/plans/UI-REDESIGN-001.md |

---

## METHOD — Patterns & Methodologies

| ID | Pattern | Where Used | Notes |
|----|---------|-----------|-------|
| METHOD-01 | INSERT OR IGNORE with CHECK constraint validation | seed scripts | Silent skip on CHECK violation — always verify with SELECT COUNT(*) not rowcount |
| METHOD-02 | SQLite multi-DB Flask pattern | web/app.py | g.conn (ies), g.rbi_conn (rbi), g.upsc_conn (upsc_eco_opt), g.nyaya_conn (nyaya), g.upsc_gs_conn (upsc_gs) |
| METHOD-03 | Migration variable: `DB = "db_key"` (not TARGET_DB, not db_name) | scripts/migrate.py | migrate.py reads `getattr(mod, "DB", "ies")` — wrong name → defaults to ies silently |
| METHOD-04 | PYQ ingestion: parse → JSON cache → seed (3-step idempotent) | scripts/parse_mrunal_pyqs.py + seed | Cache JSONs in data/cache/; re-run seed is safe (INSERT OR IGNORE + question_hash UNIQUE) |
| METHOD-05 | has_feature(user_id, gate_id) — freemium gate check | web/db.py | Checks subscription_tier + user_feature_overrides; returns True if tables missing (safe during migration) |
| METHOD-06 | Implicit state inference rules: UNVISITED=0 attempts, FLAGGED=avg<4, IN_STUDY=avg 4–6.9, VERIFIED=avg≥7+recent(<14d), DECAYING=avg≥5+old(>14d) | scripts/compute_inferred_states.py infer_state() | Canonical taxonomy matches gap_states.state CHECK constraint; self_rating mapped via CASE ('got_it'→8, 'partial'→5, 'missed'→2) |

---

## RISK — Known Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|
| RISK-01 | GS1-3 PYQ coverage gap (~75% missing) | HIGH | Download official PDFs from upsc.gov.in manually → run parse_upsc_gs_pdfs.py |
| RISK-02 | topic_id fallback assignments (178/221 questions use L1 fallback) | MEDIUM | Phase 3: Haiku batch pass over pyq_questions to refine topic_id assignments |
| RISK-03 | JINJA2-001: dict key named items/keys/values/get → 500 | HIGH | Already in CLAUDE.md; use names: section, gs_section, upsc_mode for GS toggle vars |
| RISK-04 | CSS-MOB-001: exactly 4 mobile nav tabs — any 5th tab breaks mobile grid | HIGH | In CLAUDE.md; UPSC GS toggle must live inside UPSC tab, not a new tab |
| RISK-05 | WAL contention with 5+ DBs at 100+ concurrent users — profile_bp opens 3+ separate connections per request | HIGH | DECIDE-17: cache.db for cross-exam aggregates; replaces 3-connection pattern in profile_bp (BUG-021 pattern recurs) |
| RISK-06 | No transaction isolation in quiz submit — concurrent users on same topic may corrupt attempt_count | MEDIUM | Fix in Phase 2: BEGIN EXCLUSIVE on submit routes; or use atomic UPDATE+SELECT |
| RISK-07 | No migration rollback safety — deploy new migration, rollback app, in-flight requests hit missing columns | MEDIUM | Deferred: Alembic migration (post-launch); current mitigation: test migrations on local before push |
