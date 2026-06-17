---
description: Run and test the Descriptive Exams Flask app. Use when asked to run, start, verify, or smoke-test any route in this app.
---

# Run & Test — Descriptive Exams App (Flask)

## ⚠ App is now Flask, NOT Streamlit

Streamlit pages archived to `web/pages_archive/`. Entry point is `web/wsgi.py`.

## Start the server (dev mode)

```bash
cd "/Users/rahulsingh/Desktop/Claude Projects/Descriptive-exams"
/opt/homebrew/bin/python3.11 -c "
import sys; sys.path.insert(0,'web')
from app import create_app
app = create_app()
app.run(port=8080, debug=True, use_reloader=False)
" &>/tmp/flask_app.log &
sleep 2
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/   # expect 302
```

## Start with gunicorn (production-equivalent)

```bash
cd "/Users/rahulsingh/Desktop/Claude Projects/Descriptive-exams"
/opt/homebrew/bin/python3.11 -m gunicorn \
  --chdir web 'wsgi:app' \
  --bind 0.0.0.0:8080 --workers 2 \
  --timeout 120 \
  --log-level info &>/tmp/gunicorn_app.log &
sleep 2
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/   # expect 302
```

## Verify all routes load

```bash
cd "/Users/rahulsingh/Desktop/Claude Projects/Descriptive-exams"
/opt/homebrew/bin/python3.11 -c "
import sys; sys.path.insert(0,'web')
from app import create_app
app = create_app()
routes = sorted(str(r) for r in app.url_map.iter_rules())
print(f'{len(routes)} routes:')
for r in routes: print(r)
"
# Expected: 31 routes
```

## Error triage

```bash
# Read Flask/gunicorn log
cat /tmp/flask_app.log | grep -E "Error|Traceback|ImportError" | tail -30

# Check a specific route imports cleanly
cd "/Users/rahulsingh/Desktop/Claude Projects/Descriptive-exams"
/opt/homebrew/bin/python3.11 -c "
import sys; sys.path.insert(0,'web')
from blueprints.english_bp import english_bp
print('OK')
"
```

## Route map

| URL | Blueprint | Auth |
|-----|-----------|------|
| `GET /` | app factory | No |
| `GET /auth/login` | auth_bp | No |
| `GET /auth/callback` | auth_bp | No |
| `GET /auth/logout` | auth_bp | Yes |
| `GET /dashboard` | dashboard_bp | Yes |
| `POST /ies/topics/<id>/state` | dashboard_bp | Yes |
| `GET /ies/answers` | ies_answers_bp | Yes |
| `GET /ies/diagram/<dtype>.png` | ies_answers_bp | Yes |
| `GET /ies/brief` | ies_brief_bp | Yes |
| `GET /ies/quiz` | ies_quiz_bp | Yes |
| `GET /ies/return-quiz` | ies_return_quiz_bp | Yes |
| `POST /ies/return-quiz/submit` | ies_return_quiz_bp | Yes |
| `GET /rbi` | rbi_dashboard_bp | Yes |
| `GET /rbi/prep` | rbi_prep_bp | Yes |
| `POST /rbi/prep/drill/questions` | rbi_prep_bp | Yes |
| `POST /rbi/prep/drill/submit` | rbi_prep_bp | Yes |
| `POST /rbi/prep/tier2/submit` | rbi_prep_bp | Yes |
| `GET /upsc` | upsc_dashboard_bp | Yes |
| `POST /upsc/topics/<id>/state` | upsc_dashboard_bp | Yes |
| `GET /upsc/mains` | upsc_bp | Yes |
| `GET /english/dashboard` | english_bp | Yes |
| `GET /practice/english` | english_bp | Yes |
| `POST /practice/english/score` | english_bp | Yes |
| `POST /rbi/topics/<topic>/drill` | rbi_dashboard_bp | Yes |
| `GET /rbi/prep/drill/questions` | rbi_prep_bp | Yes |
| `GET /progress` | progress_bp | Yes |
| `GET /progress/review` | progress_bp | Yes |
| `GET /setup` | setup_bp | Yes |
| `POST /setup` | setup_bp | Yes |
| `GET /profile` | profile_bp | Yes |
| `POST /profile` | profile_bp | Yes |
| `GET /feedback` | feedback_bp | Yes |
| `POST /feedback/submit` | feedback_bp | Yes |

## Auth behaviour

- All routes (except `/`, `/auth/*`) decorated with `@login_required`
- `login_required` checks `g.user_id` (set by `app.before_request` from Flask session token)
- Redirects to `/auth/login` if not authenticated
- OAuth callback → `/auth/callback` → sets `session["session_token"]` → redirects to `/dashboard`

## DB connections

| DB | How opened | g key |
|----|-----------|-------|
| `data/ies.db` | `app.before_request` | `g.conn` |
| `data/rbi.db` | `rbi_dashboard_bp.before_request` + `rbi_prep_bp.before_request` | `g.rbi_conn` |
| `data/upsc_eco_opt.db` | `upsc_dashboard_bp.before_request` + `upsc_bp.before_request` | `g.upsc_conn` |

All connections closed by corresponding `teardown_appcontext` / `teardown_request` hooks — no manual `.close()` needed in routes.

## Databases

```bash
sqlite3 data/rbi.db "SELECT tier, COUNT(*) FROM rbi_questions GROUP BY tier;"
sqlite3 data/ies.db "SELECT COUNT(*) FROM pyq_questions;"
sqlite3 data/ies.db "SELECT COUNT(*) FROM users;"
```

## Railway deploy

Push `main` branch. Railway picks up `railway.toml` start command:
```
gunicorn --chdir web 'wsgi:app' --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

OAuth redirect URI already updated to `/auth/callback` in Google Cloud Console (done S18). `FLASK_SECRET_KEY` and `OAUTH_REDIRECT_URI` set as Railway env vars.

## Mobile layout debugging (CSS-MOB-001)

**Symptom:** sidebar shows + mobile nav hidden + content zoomed out — all at once on some pages.

**Root cause:** Flex `min-width: auto` on `.main-content` lets child elements expand
the layout viewport past 600px on Samsung Internet → ALL media queries stop firing.

**Diagnostic:** Does the broken page have any `min-width > 150px` on a flex child?

**Fix pattern:**
```css
.main-content { min-width: 0; }          /* flex gotcha */
.app-layout { width: 100%; overflow-x: hidden; }  /* outer containment */
```

**Cache-bust + inline critical CSS** (always pair with layout fixes):
```html
<link rel="stylesheet" href="style.css?v=N">   <!-- bump N each deploy -->
<style>
@media (max-width: 600px) {
    .sidebar { display: none !important; }
    .main-content { margin-left: 0 !important; }
    .mobile-nav { display: flex !important; }
}
</style>
```

See `~/.claude/knowledge/patterns/CSS-MOB-001-flex-min-width-viewport.md` for full pattern.
Current CSS version: `?v=4` (bump to `?v=5` on next mobile CSS change).
