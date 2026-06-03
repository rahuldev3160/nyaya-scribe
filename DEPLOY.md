# Deployment Reference

## Python version
Python 3.11 (Homebrew). Local binary: `/opt/homebrew/bin/python3.11`

## Local development
```bash
cp .env.example .env
# Edit .env — set all three variables (Anthropic + Google OAuth)
/opt/homebrew/bin/streamlit run web/app.py
```

All features work without an Anthropic API key except **Quiz** (AI grading).
All pages except Model Answers and UPSC Mains require Google sign-in.

## Databases on first boot

Three DBs are gitignored (live user data accumulates in them). Committed seed
copies are used to initialise them on a fresh server:

| Live DB | Seed (committed) | Contents |
|---|---|---|
| `data/ies.db` | `data/ies_seed.db` | 1219 IES PYQs + rubrics + model answers |
| `data/rbi.db` | `data/rbi_seed.db` | 303 RBI MCQs + topic weights |
| `data/upsc.db` | `data/upsc_seed.db` | 908 UPSC model answers |

`app.py` copies each seed → live on first load if the live DB is absent. No
manual setup step required.

## Deployment targets

### Hetzner CX21 (~€4.5/mo) — preferred
1. Provision a CX21 Ubuntu 24.04 instance.
2. Install Python 3.11, clone the repo, install deps:
   ```bash
   pip3.11 install -r requirements.txt
   ```
3. Run with a process manager (systemd or `screen`):
   ```bash
   /usr/local/bin/streamlit run web/app.py --server.port 8501 --server.headless true
   ```
4. Point a reverse proxy (nginx/Caddy) at port 8501 with HTTPS.

### Railway ($5/mo)
1. Connect the GitHub repo in the Railway dashboard.
2. Set start command: `streamlit run web/app.py --server.port $PORT --server.headless true`
3. Set Python version to 3.11 in `railway.toml` or via the dashboard.

## Secrets
Set all of the following as environment variables on the server (or in Railway env):

```
ANTHROPIC_API_KEY=sk-ant-api03-...
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
OAUTH_REDIRECT_URI=https://your-domain.com/0_Login
```

**OAUTH_REDIRECT_URI** must exactly match the authorised redirect URI configured
in Google Cloud Console for your OAuth 2.0 client.

## Google OAuth setup (one-time)
1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials.
2. Create an OAuth 2.0 Client ID (Web application).
3. Add your domain to Authorised JavaScript origins.
4. Add `https://your-domain.com/0_Login` to Authorised redirect URIs.
5. Copy Client ID and Client Secret to your environment variables.

## Cost control
- Set a monthly spend limit in the Anthropic console (recommended: $50/month for a small launch).
- AI calls (Quiz grading) are gated on `ANTHROPIC_API_KEY`; if unset, Quiz shows a banner and stops.
- Monitor usage in the Anthropic console dashboard.

## Smoke test after deploy
1. Open the app — should show Google sign-in page.
2. Sign in with a Google account.
3. Navigate to each page; verify no DB errors.
4. Test Quiz with one answer (requires API key).
5. Test with a second Google account to confirm data isolation.
