# PLAN-006 — Streamlit → Flask Migration

**Date:** 2026-06-05 (Session 17)
**Status:** COMPLETE
**Commit:** `9f842a2`

## Why

Streamlit idled at 122%+ CPU due to its polling/WebSocket architecture. At idle — nobody using the app — the process consumed more CPU than a production workload should. Flask + gunicorn idles at ~0%.

## What was built

Full rewrite of 13-page Streamlit app to Flask + Jinja2 + HTMX + MathJax. 4 phases:

**Phase 0 (Foundation):**
- `web/app.py` → Flask factory (`create_app()`)
- `web/auth.py` → Flask-compatible (removed Streamlit, fixed BUG-008 CSRF)
- `web/db.py` → Flask `g`-scoped connections (fixed BUG-007, 010, 011)
- `web/blueprints/auth_bp.py` → `/auth/login`, `/auth/callback`, `/auth/logout`
- `web/templates/base.html` + `web/static/style.css` (dark theme)
- `web/wsgi.py` → gunicorn entry point
- `railway.toml` updated, `requirements.txt` updated

**Phase 1 (4 core pages):**
- `/dashboard` (IES dashboard + state changes)
- `/ies/answers` + `/ies/diagram/<dtype>.png`
- `/ies/brief`
- `/upsc/mains`

**Phase 2 (3 practice pages):**
- `/ies/quiz` (AI eval disabled, "coming soon" badge)
- `/ies/return-quiz` + `/ies/return-quiz/submit` (full MCQ + grading)
- `/rbi/prep` (4-tab RBI prep: key data / drill / tier2 / progress)

**Phase 3 (6 remaining pages):**
- `/rbi` (RBI dashboard: metrics, subject coverage, gap alerts)
- `/upsc` + `/upsc/topics/<id>/state` (UPSC dashboard: paper tabs, state buttons)
- `/progress` + `/progress/review` (attempt history, time tracker, answer review lock)
- `/setup` (onboarding wizard + Haiku plan generation)
- `/profile` (avatar, contact, study snapshot, sign out)
- `/practice/english` + score + assess (3-phase: write → auto-score → self-assess)

**Phase 4 (Cutover):**
- `web/pages/` archived to `web/pages_archive/`
- 28 routes verified clean with `app.url_map.iter_rules()`

## Key architecture decisions

1. **No HTMX for MVP** — state changes use plain form POST + redirect (PRG pattern)
2. **Flask `g` for DB** — `g.conn` (ies.db) opened/closed per request by app hooks; `g.rbi_conn`/`g.upsc_conn` opened/closed by blueprint-level hooks
3. **Flask `session` for state** — quiz results, English practice phase, RBI drill stored in signed cookie session
4. **All routes @login_required** — no open pages (BUG-012 fixed)
5. **Scoring module** at project root `/scoring/` — English blueprint adds project root to sys.path

## Pre-deploy action required

Update OAuth redirect URI in Google Cloud Console: `/Login` → `/auth/callback`

## Files

- 11 blueprints in `web/blueprints/`
- 16 templates in `web/templates/`
- 1 CSS in `web/static/style.css`
- `web/wsgi.py`, `web/app.py`, `web/auth.py`, `web/db.py`
