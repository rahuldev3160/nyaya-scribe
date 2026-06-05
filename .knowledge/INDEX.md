# Knowledge Base — Descriptive Exams
Last updated: 2026-06-05 (Session 14)

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
| [BUG-007](bugs/BUG-007.md) | OPEN | MEDIUM | resource | DB connection leaks — 12+ st.stop() paths bypass conn.close() | — | S13 | — |
| [BUG-008](bugs/BUG-008.md) | OPEN | LOW | security | OAuth CSRF — state param generated but never validated in callback | — | S13 | — |
| [BUG-009](bugs/BUG-009.md) | OPEN | LOW | consistency | Transaction rollback swallows gap_state_events silently | — | S13 | — |
| [BUG-010](bugs/BUG-010.md) | OPEN | HIGH | data-isolation | set_topic_state() calls get_user_id() internally — wrong-user writes possible | — | S13 | — |
| [BUG-011](bugs/BUG-011.md) | OPEN | MEDIUM | data-isolation | "rahul" fallback in get_user_id() — data written under literal string in error paths | — | S13 | — |
| [BUG-012](bugs/BUG-012.md) | INFO | LOW | auth | 1_Model_Answers.py + 7_UPSC_Mains.py have no require_user() — may be intentional | — | S13 | — |
| [BUG-013](bugs/BUG-013.md) | FIXED | HIGH | auth | CookieManager(key="main") instantiated 3x → StreamlitDuplicateElementKey with st.navigation() | — | S14 | ba83b9b |
| [BUG-014](bugs/BUG-014.md) | FIXED | MEDIUM | auth | validate_session crashes on naive datetimes from SQLite datetime('now') vs UTC-aware Python | — | S14 | ba83b9b |
| [BUG-015](bugs/BUG-015.md) | FIXED | LOW | auth | "Page not found" flash on cookie-restored sessions — nav rebuilt before rerun | — | S14 | ba83b9b |

---

## Audits

| ID | Date | Scope | Agents | Bugs Found | Fixed | Open |
|----|------|-------|--------|------------|-------|------|
| [AUDIT-001](audits/AUDIT-001.md) | 2026-06-05 | arch/auth/nav/data-isolation/quiz-integrity | 3 parallel | 12 | 6 | 6 |

---

## Plans

| ID | Date | Title | Status |
|----|------|-------|--------|
| [PLAN-001](plans/PLAN-001.md) | 2026-06-03 | Multi-user architecture (S10) | COMPLETE |
| [PLAN-002](plans/PLAN-002.md) | 2026-06-05 | S14 features: persistent login + plan templates + dashboard labeling | COMPLETE |
| [PLAN-003](plans/PLAN-003.md) | 2026-06-05 | S15: RBI+UPSC dashboards + plan reduction 144→24 + exam date labels | COMPLETE |
| [PLAN-004](plans/PLAN-004.md) | 2026-06-05 | English question type templates — 9 types (Essay, Précis, Letter, RC, Report, etc.) for RBI+UPSC | COMPLETE |
| [PLAN-005](plans/PLAN-005.md) | 2026-06-05 | English Practice Module — taxonomy (7 types), schema (4 tables), keyword scoring, page 11 | PLANNING |

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
