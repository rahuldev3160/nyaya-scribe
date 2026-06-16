# MASTER_INDEX — Descriptive Exams (Nyaya Scribe)
Created: 2026-06-16 (Session 39)
Updated: 2026-06-16 (Session 39)

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
| DECIDE-09 | upsc_gs.db is a separate physical DB file (not tables inside upsc.db) | GS Mains has 41 tables; embedding in upsc.db would bloat it and require schema migration of existing data | Add GS tables to upsc.db | web/upsc_gs_db.py, web/app.py |

---

## SCHEMA — DB Table Designs

| ID | Table / Change | DB | Migration | Notes |
|----|---------------|-----|-----------|-------|
| SCHEMA-01 | upsc_gs.db — 41-table core schema (pyq_questions, topics, model_answers, rubrics, gap_states, mastery, etc.) | upsc_gs.db | m026–m033 | See PLAN-017.md for full spec |
| SCHEMA-02 | gs4_keywords — keyword_category CHECK widened to 22 values | upsc_gs.db | m034 | SQLite requires table recreate to change CHECK; done via CREATE+INSERT+DROP+RENAME |
| SCHEMA-03 | gs4_thinkers — 15 rows (Gandhi→Nussbaum) | upsc_gs.db | setup_upsc_gs.py seed | upsc_relevance_score 0.68–0.97 |
| SCHEMA-04 | gs4_keywords — 123 canonical ethics keywords + 430 synonym expansions | upsc_gs.db | setup_upsc_gs.py seed | categories: core_value/ethical_theory/governance_ethics/etc. |
| SCHEMA-05 | pyq_questions — 221 rows seeded (GS4: 93, GS1: 62, GS2: 29, GS3: 37) | upsc_gs.db | scripts/seed_upsc_gs_pyqs.py | GS1-3 coverage gap; needs official PDFs |

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
| METHOD-02 | SQLite multi-DB Flask pattern | web/app.py | g.conn (ies), g.rbi_conn (rbi), g.upsc_conn (upsc), g.nyaya_conn (nyaya), g.upsc_gs_conn (upsc_gs) |
| METHOD-03 | Migration variable: `DB = "db_key"` (not TARGET_DB, not db_name) | scripts/migrate.py | migrate.py reads `getattr(mod, "DB", "ies")` — wrong name → defaults to ies silently |
| METHOD-04 | PYQ ingestion: parse → JSON cache → seed (3-step idempotent) | scripts/parse_mrunal_pyqs.py + seed | Cache JSONs in data/cache/; re-run seed is safe (INSERT OR IGNORE + question_hash UNIQUE) |

---

## RISK — Known Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|-----------|
| RISK-01 | GS1-3 PYQ coverage gap (~75% missing) | HIGH | Download official PDFs from upsc.gov.in manually → run parse_upsc_gs_pdfs.py |
| RISK-02 | topic_id fallback assignments (178/221 questions use L1 fallback) | MEDIUM | Phase 3: Haiku batch pass over pyq_questions to refine topic_id assignments |
| RISK-03 | JINJA2-001: dict key named items/keys/values/get → 500 | HIGH | Already in CLAUDE.md; use names: section, gs_section, upsc_mode for GS toggle vars |
| RISK-04 | CSS-MOB-001: exactly 4 mobile nav tabs — any 5th tab breaks mobile grid | HIGH | In CLAUDE.md; UPSC GS toggle must live inside UPSC tab, not a new tab |
