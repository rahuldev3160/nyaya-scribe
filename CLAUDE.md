# CLAUDE.md — Descriptive Exams Project

## Knowledge Base — ALWAYS CHECK FIRST
Before any audit, bug investigation, or architecture review:
1. Read `.knowledge/INDEX.md` — scan open bugs and past audits
2. Read `~/.claude/knowledge/patterns/PATTERNS.md` — check for known patterns before investigating from scratch

## Knowledge Base — ALWAYS UPDATE AFTER
After any of these task types, write synthesized records to `.knowledge/` before finishing the response:
- Multi-agent analysis or audit
- Significant bug investigation and fix (>1 file changed)
- Architecture review or plan
- Deployment diagnostic
- Any task that consumed >5,000 tokens

**What to write:** Synthesized findings only — not raw agent output. One record per bug/audit/plan.
**Where:** `.knowledge/bugs/`, `.knowledge/audits/`, `.knowledge/plans/`, `.knowledge/diagnostics/`
**Always:** Update `.knowledge/INDEX.md` to reflect the new/changed records.

## Brand
- Umbrella: **NYAYA** (`nyaya.app` — primary domain)
- This product: **Nyaya Scribe** — the expression faculty (descriptive answer writing + AI scoring)
- Tagline: *"The logic of getting in."*
- Competitors: prayas.ai (UPSC-only answer eval), SuperKalam (MCQ-focused)

## Environment
- Python: `/opt/homebrew/bin/streamlit` (Python 3.11). Never use `/Library/Python/3.9/`
- App entry point: `flask run` or `gunicorn web/wsgi:app`
- DB files: `data/ies.db`, `data/rbi.db`, `data/upsc_eco_opt.db`, `data/nyaya.db`, `data/english.db`, `data/upsc_gs.db`
- Seeds: `seeds/ies_seed.db`, `seeds/rbi_seed.db`, `seeds/upsc_eco_opt_seed.db`, `seeds/nyaya_seed.db`
- Production: `ies-descriptive-prep-production.up.railway.app`
- Railway SSH: `railway ssh python scripts/X.py` (not `railway run`)

## Architecture Constraints
- Flask app. Entry: `web/wsgi.py`. 31 routes across 15 blueprints.
- All user data is scoped by `user_id` (UUID). Never trust session alone — use `@login_required` + `g.user_id`.
- DB connections: `g.conn` (ies.db), `g.rbi_conn` (rbi.db), `g.upsc_conn` (upsc_eco_opt.db), `g.nyaya_conn` (nyaya.db), `g.english_conn` (english.db), `g.upsc_gs_conn` (upsc_gs.db) — opened/closed in app.py before_request/teardown_appcontext.
- **nyaya.db is the canonical identity+event store.** Auth (users, sessions), all user_events, and product_enrollments live here. Exam data (questions, rubrics, attempts, mastery) stays in ies/rbi/upsc_eco_opt.db.
- **Cross-DB JOIN**: SQLite cannot JOIN across .db files. For user lookups when querying ies/rbi/upsc tables, do two queries then Python-merge (see feedback_bp.py for the pattern).
- **JINJA2-001**: Never name a dict key `items`, `keys`, `values`, `get`, or any Python dict method name when the dict is passed to a Jinja2 template. Dot-notation `sec.items` resolves to the Python builtin, not the key → 500. Fix at the data layer: rename the key (e.g. `rows`, `entries`). See BUG-016.

## Code Style
- No comments unless WHY is non-obvious
- No trailing summary in responses — Rahul can read the diff
- Explain technical concepts with analogies when building/debugging (see memory)
- Use parallel tool calls wherever independent
