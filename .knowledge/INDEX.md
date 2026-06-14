# Knowledge Base — Descriptive Exams
Last updated: 2026-06-14 (Session 37)

## How to use
- Scan this file at the start of any audit or bug-fix session before doing any analysis
- Check Open Bugs before writing new investigation code — the work may already be done
- Patterns column links to `~/.claude/knowledge/patterns/` — check those before diagnosing a new bug
- Add new records immediately after any audit, multi-agent task, significant fix, or deployment issue

---

## Bugs

| ID | Status | Severity | Category | Summary | Pattern | Session | Commit |
|----|--------|----------|----------|---------|---------|---------|--------|
| [BUG-001](bugs/BUG-001.md) | FIXED | CRITICAL | navigation | OAuth callback crashes — Dashboard not in nav | NAV-001 | S13 | 0fec71e |
| [BUG-002](bugs/BUG-002.md) | FIXED | CRITICAL | navigation | Logout crashes — Login not in authed nav | NAV-001 | S13 | 831479c |
| [BUG-003](bugs/BUG-003.md) | FIXED | HIGH | auth+resource | require_user() nav mismatch + connection leak on session expiry | NAV-001 | S13 | 831479c |
| [BUG-004](bugs/BUG-004.md) | FIXED | HIGH | data-isolation | Session state bleed — User B inherits User A's quiz/RBI state | SESSION-001 | S13 | 831479c |
| [BUG-005](bugs/BUG-005.md) | FIXED | HIGH | concurrency | attempt_count race — read-then-write across concurrent tabs | DB-001 | S13 | 831479c |
| [BUG-006](bugs/BUG-006.md) | FIXED | MEDIUM | validation | Quiz accepts partial answers — any() instead of all() | — | S13 | 831479c |
| [BUG-007](bugs/BUG-007.md) | FIXED | MEDIUM | resource | DB connection leaks — fixed by Flask g-scoped connections + teardown hooks | — | S17 | 9f842a2 |
| [BUG-008](bugs/BUG-008.md) | FIXED | LOW | security | OAuth CSRF — state validated in Flask auth_bp callback via session["oauth_state"] | — | S17 | 9f842a2 |
| [BUG-009](bugs/BUG-009.md) | FIXED | LOW | consistency | Transaction rollback swallows gap_state_events silently — try/except + flash redirect in submit() | — | S13/S26 | — |
| [BUG-010](bugs/BUG-010.md) | FIXED | HIGH | data-isolation | set_topic_state() now takes explicit user_id param; all routes pass g.user_id | — | S17 | 9f842a2 |
| [BUG-011](bugs/BUG-011.md) | FIXED | MEDIUM | data-isolation | "rahul" fallback gone — Flask context always has g.user_id or returns 401 | — | S17 | 9f842a2 |
| [BUG-012](bugs/BUG-012.md) | FIXED | LOW | auth | All Flask routes use @login_required — no open pages remaining | — | S17 | 9f842a2 |
| [BUG-013](bugs/BUG-013.md) | FIXED | HIGH | auth | CookieManager(key="main") instantiated 3x → StreamlitDuplicateElementKey with st.navigation() | — | S14 | ba83b9b |
| [BUG-014](bugs/BUG-014.md) | FIXED | MEDIUM | auth | validate_session crashes on naive datetimes from SQLite datetime('now') vs UTC-aware Python | — | S14 | ba83b9b |
| [BUG-015](bugs/BUG-015.md) | FIXED | LOW | auth | "Page not found" flash on cookie-restored sessions — nav rebuilt before rerun | — | S14 | ba83b9b |
| [BUG-016](bugs/BUG-016.md) | FIXED | HIGH | template | Jinja2 dict key `items` shadows Python builtin → 500; root fix: renamed key to `rows` in both blueprints | JINJA2-001 | S18+S20 | 1384854 |
| [BUG-017](bugs/BUG-017.md) | FIXED | HIGH | ui | RBI tab panels are siblings of #rbi-tabs div, not children — switchTab querySelectorAll finds nothing, all panels stack | — | S18 | f68b976 |
| [BUG-018](bugs/BUG-018.md) | FIXED | HIGH | scoring | Drill scoring always 0 — form submits full option text but code took `chosen_full[0]` (first char of sentence) vs `correct_option` letter | — | S18 | 6968d5d |
| BUG-019 | FIXED | CRITICAL | data-loss | RBI drill `drill_submit()` called `save_attempt(answer_given="")` when user skipped — SQLite `CHECK(answer_given IN('A','B','C','D'))` raised, bare `except` swallowed it silently; 4/5 of Shubhang's answers lost. Fix: pre-validate all answers before any saves, redirect with flash error if any unanswered. | — | S24 | 389ff67 |
| BUG-020 | FIXED | CRITICAL | navigation | Topic→paper mismatch: set_state/upsc_topic_state redirected with `?topic=` but no `?paper=`; receiving pages defaulted to ge_01/upsc_p1 and returned 0 questions for 23/30 IES topics and all UPSC Paper II topics. Also: ies_quiz by-topic mode showed incoherent dropdown. Fix: DB lookup before redirect + auto-detect paper on receive. | — | S27 | 96f308e |
| [BUG-021](bugs/BUG-021.md) | FIXED | MEDIUM | data-sync | Profile "MCQs Attempted" always 0 — queried `return_quiz_attempts` in ies.db only; RBI MCQs in `rbi_attempts`/rbi.db and blueprint-scoped `g.rbi_conn` not available on /profile route. Fix: open short-lived direct connections per DB in profile_bp. | SYNC-001 | S28 | TBD |
| [BUG-022](bugs/BUG-022.md) | FIXED | HIGH | data-sync | Progress page "Time per page" permanently stale — `get_time_breakdown` read ies.db `user_events` with `event_type='page_time'`, but all writes since S25 go to nyaya.db as `event_type='page_view'`. Double mismatch: wrong DB + wrong event type. Fix: use `get_nyaya_conn()` + filter `page_view`. | SYNC-001 | S28 | TBD |
| [BUG-023](bugs/BUG-023.md) | FIXED | MEDIUM | data-sync | Profile "Answers Graded" undercounts — only queries IES `descriptive_attempts` in ies.db; UPSC `descriptive_attempts` in upsc.db ignored. Fix: open direct upsc.db connection in profile_bp and sum. | SYNC-001 | S28 | TBD |
| [BUG-024](bugs/BUG-024.md) | FIXED | MEDIUM | data-integrity | Orphaned `user_events` rows with no `users` FK — `user_events` had no `REFERENCES users(user_id)`; `validate_session` didn't JOIN users so stale sessions returned ghost user_ids. Fix: FK + ON DELETE CASCADE via `_run_nyaya_migrations()`; validate_session now JOINs users. | — | S29 | 4bf3097 |
| [BUG-025](bugs/BUG-025.md) | FIXED | HIGH | data | Quiz model answer panel always empty — `get_questions()` selects `ma.answer_id` but not `intro_text/body_text/conclusion_text` (too expensive for 1219 rows). Fix: call `get_answer()` for `selected_q` only, merge 3 text fields after question selection. | — | S30 | 49d0d0e |

---

## Audits

| ID | Date | Scope | Agents | Bugs Found | Fixed | Open |
|----|------|-------|--------|------------|-------|------|
| [AUDIT-001](audits/AUDIT-001.md) | 2026-06-05 | arch/auth/nav/data-isolation/quiz-integrity | 3 parallel | 12 | 6 | 6 |
| [AUDIT-002](audits/AUDIT-002.md) | 2026-06-06 | performance/lag/multi-user | 4 parallel | 9 RC | 8 | 1 (RC-8 deferred) |
| [AUDIT-003](audits/AUDIT-003.md) | 2026-06-07 | auth+event recording flow — full journey trace | inline | 4 | 3 | 1 (BUG-D: daemon thread writes, LOW) |
| [AUDIT-004](audits/AUDIT-004.md) | 2026-06-07 | Data flow architecture — all 4 exam domains (RBI, IES, UPSC, English+shared) | 4 parallel | 8 problem classes, 2 live bugs | 2 fixed same session | 6 open → PLAN-014 |
| [AUDIT-005](audits/AUDIT-005.md) | 2026-06-08 | Mobile layout regressions — all 4 issues (login tiny, sidebar shows, nav disappears, zoom-out) | inline | 6 root causes | 6 fixed (commit ca37f51) | 0 open |
| [AUDIT-006](audits/AUDIT-006.md) | 2026-06-08 | Mobile UI polish — button text overflow, mid-word breaks in stat cards, grid collapse strategy | inline | 5 root causes | 5 fixed (commit 7f405e9) | 0 open |

---

## Plans

| ID | Date | Title | Status |
|----|------|-------|--------|
| [PLAN-001](plans/PLAN-001.md) | 2026-06-03 | Multi-user architecture (S10) | COMPLETE |
| [PLAN-002](plans/PLAN-002.md) | 2026-06-05 | S14 features: persistent login + plan templates + dashboard labeling | COMPLETE |
| [PLAN-003](plans/PLAN-003.md) | 2026-06-05 | S15: RBI+UPSC dashboards + plan reduction 144→24 + exam date labels | COMPLETE |
| [PLAN-004](plans/PLAN-004.md) | 2026-06-05 | English question type templates — 9 types (Essay, Précis, Letter, RC, Report, etc.) for RBI+UPSC | COMPLETE |
| [PLAN-005](plans/PLAN-005.md) | 2026-06-05 | English Practice Module — taxonomy (7 types), schema (4 tables), keyword scoring, page 11 | COMPLETE |
| [PLAN-006](plans/PLAN-006.md) | 2026-06-05 | Streamlit→Flask migration — 28 routes, gunicorn, 0% idle CPU | COMPLETE |
| [PLAN-007](plans/PLAN-007.md) | 2026-06-06 | S18: Railway deploy + 5 UI features + 3 critical bug fixes | COMPLETE |
| [PLAN-008](plans/PLAN-008.md) | 2026-06-06 | S19: English dashboard UX fixes + Feedback feature | COMPLETE |
| [PLAN-009](plans/PLAN-009.md) | 2026-06-06 | S19: RBI dashboard redesign + sidebar overhaul + Priority 1/2 rename | COMPLETE |
| [PLAN-010](plans/PLAN-010.md) | 2026-06-06 | S20–S22: Dashboard UI uplift (all 4 dashboards) + English content seeding batch2 | COMPLETE |
| [PLAN-011](plans/PLAN-011.md) | 2026-06-06 | S23: Multi-DB migrations (m003–m008), remove keyword scoring, DB-driven model answers, new essay Qs | COMPLETE |
| PLAN-012 | 2026-06-06 | S24: Essay quality overhaul — UPSC open-canvas style, m009+m010, seed DB sync, auto-migration | COMPLETE |
| [PLAN-013](plans/PLAN-013.md) | 2026-06-06 | S25: nyaya.db — 4th canonical DB for identity+events; Phase 1+2 complete (commit 9a26646) | PHASE 2 COMPLETE |
| [PLAN-014](plans/PLAN-014.md) | 2026-06-07 | S33: Single-source architecture refactor — kill INSERT OR IGNORE drift, eliminate KEY_SECTIONS/BUCKETS, centralise metadata, English to own DB | ALL PHASES COMPLETE (S37 — commit bc90ab4) |
| PLAN-015 | 2026-06-08 | S35: Mobile-first UI — bottom tab nav, responsive grids, sidebar DOM removal, full-screen login, CSS-MOB-001 fix | COMPLETE (commit ca37f51) |
| PLAN-016 | 2026-06-13 | S36: Engagement activation — post-setup routing, smart login, button redesign, first-action cards, nav cleanup | COMPLETE (commit e51b27a) |

---

## Diagnostics / Deployments

| ID | Date | Issue | Resolution |
|----|------|-------|------------|
| [DIAG-001](diagnostics/DIAG-001.md) | 2026-06-04 | Railway SSH + data migration setup | RESOLVED |
| [DIAG-002](diagnostics/DIAG-002.md) | 2026-06-05 | Production "Page not found" on login | RESOLVED → BUG-001 |

---

## Patterns Reference
Cross-project patterns live at `~/.claude/knowledge/patterns/PATTERNS.md`

| Pattern ID | Name | Applies To | Seen In |
|------------|------|------------|---------|
| NAV-001 | Streamlit st.navigation() timing — st.switch_page to unregistered page | Any Streamlit multi-page app | BUG-001, BUG-002, BUG-003 |
| SESSION-001 | Session state not cleared on user switch | Any Streamlit app with auth | BUG-004 |
| DB-001 | Read-modify-write race on DB counters | Any app with concurrent writes | BUG-005 |
| JINJA2-001 | Dict key named `items`/`keys`/`values` shadows Python builtin in Jinja2 → 500 | Any Jinja2 template | BUG-016 (recurred x2) |
| SYNC-001 | Blueprint-scoped `g.*_conn` not available outside that blueprint's routes — cross-DB aggregates must open short-lived direct connections | Any route that reads from multiple .db files | BUG-021 |
| CSS-MOB-001 | Flex `min-width:auto` expands layout viewport past 600px breakpoint on Samsung Internet — ALL mobile media queries fail at once. Fix: `min-width:0` on flex items + inline critical CSS with `!important` + `style.css?v=N` cache-bust | Any responsive Flask/web app | AUDIT-005 |
