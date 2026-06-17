# Deployment Reference

## Python version
Python 3.11. Pinned in `.python-version`. Local binary: `/opt/homebrew/bin/python3.11`

## Local development
```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY + 3 OAuth vars
/opt/homebrew/bin/streamlit run web/app.py
```

All features work without an Anthropic API key except **Quiz** (AI grading) and **My Setup** plan generation (falls back to rule-based plan).  
All pages except Model Answers and UPSC Mains require Google sign-in.

---

## Databases on first boot

Three DBs are gitignored (live user data accumulates). Seed copies are committed and auto-copied on first run:

| Live DB | Seed (committed) | Contents |
|---|---|---|
| `data/ies.db` | `data/ies_seed.db` | 1219 IES PYQs + rubrics + model answers |
| `data/rbi.db` | `data/rbi_seed.db` | 303 RBI MCQs + topic weights |
| `data/upsc_eco_opt.db` | `data/upsc_seed.db` | 908 UPSC model answers |

`app.py` copies seed → live on first load. No manual step needed.

---

## Deploy on Railway (recommended — ~$5/mo)

`railway.toml` is already committed. Steps:

### 1. Create Railway project
1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
2. Select `rahuldev3160/ies-descriptive-prep`
3. Railway picks up `railway.toml` automatically

### 2. Add a persistent volume (CRITICAL — without this, DB data resets on redeploy)
1. In Railway dashboard → your service → **Storage** tab
2. **Add Volume** → Mount Path: `/app/data`
3. This keeps `ies.db`, `rbi.db`, `upsc_eco_opt.db` alive across deploys

### 3. Set environment variables
In Railway → your service → **Variables** tab, add:
```
ANTHROPIC_API_KEY        = sk-ant-api03-...
GOOGLE_CLIENT_ID         = your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET     = GOCSPX-...
OAUTH_REDIRECT_URI       = https://your-railway-domain.up.railway.app/0_Login
```
Railway gives you a domain like `ies-descriptive-prep-production.up.railway.app`.  
Use that as the base for `OAUTH_REDIRECT_URI`.

### 4. Google OAuth setup (one-time, ~5 min)
1. [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Authorised JavaScript origins: `https://your-railway-domain.up.railway.app`
4. Authorised redirect URIs: `https://your-railway-domain.up.railway.app/0_Login`
5. Copy **Client ID** and **Client Secret** → paste into Railway Variables

### 5. Deploy
Railway auto-deploys on every `git push` to `main`. First deploy takes ~3 min.

### 6. Smoke test
1. Open the Railway URL → should show Google sign-in
2. Sign in → onboarding wizard fires (My Setup page)
3. Complete setup → dashboard loads
4. Test with a second Google account to confirm user isolation

---

## Deploy on Hetzner CX21 (~€4.5/mo)

1. Provision CX21 (Ubuntu 24.04), SSH in
2. Install Python 3.11:
   ```bash
   apt install python3.11 python3.11-pip -y
   ```
3. Clone and install:
   ```bash
   git clone https://github.com/rahuldev3160/ies-descriptive-prep.git
   cd ies-descriptive-prep
   pip3.11 install -r requirements.txt
   ```
4. Create `.env` with the 4 secrets, then run with systemd or screen:
   ```bash
   streamlit run web/app.py --server.port 8501 --server.headless true
   ```
5. Point Caddy at port 8501 with HTTPS

---

## Secrets reference
```
ANTHROPIC_API_KEY        AI grading (Quiz + My Setup plan generation)
GOOGLE_CLIENT_ID         OAuth sign-in
GOOGLE_CLIENT_SECRET     OAuth sign-in
OAUTH_REDIRECT_URI       Must match Google Cloud Console exactly
```

## Cost control
- Set a monthly spend cap in [Anthropic console](https://console.anthropic.com) (recommended: $20–50/mo for small launch)
- AI calls: Quiz grading + onboarding plan generation (one-off per user, claude-haiku)
- Monitor in Anthropic dashboard

## Updating YouTube resources
Edit `web/resources.py` — add playlist URLs as you upload new content to @rahuldev0108.  
Push to `main` → Railway auto-redeploys in ~2 min.
