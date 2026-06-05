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
- App entry point: `streamlit run web/app.py`
- DB files: `data/ies.db`, `data/rbi.db`, `data/upsc.db`
- Seeds: `seeds/ies_seed.db`, `seeds/rbi_seed.db`, `seeds/upsc_seed.db`
- Production: `ies-descriptive-prep-production.up.railway.app`
- Railway SSH: `railway ssh python scripts/X.py` (not `railway run`)

## Architecture Constraints
- Flask app. Entry: `web/wsgi.py`. 34 routes across 14 blueprints.
- All user data is scoped by `user_id` (UUID). Never trust session alone — use `@login_required` + `g.user_id`.
- DB connections: `g.conn` (ies.db), `g.rbi_conn` (rbi.db), `g.upsc_conn` (upsc.db) — opened/closed by blueprint hooks.
- **JINJA2-001**: Never name a dict key `items`, `keys`, `values`, `get`, or any Python dict method name when the dict is passed to a Jinja2 template. Dot-notation `sec.items` resolves to the Python builtin, not the key → 500. Fix at the data layer: rename the key (e.g. `rows`, `entries`). See BUG-016.

## Code Style
- No comments unless WHY is non-obvious
- No trailing summary in responses — Rahul can read the diff
- Explain technical concepts with analogies when building/debugging (see memory)
- Use parallel tool calls wherever independent
