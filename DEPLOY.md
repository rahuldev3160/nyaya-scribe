# Deployment Reference

## Python version
Python 3.11 (Homebrew). Local binary: `/opt/homebrew/bin/python3.11`

## Local development
```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY (required for Quiz feature only)
/opt/homebrew/bin/streamlit run web/app.py
```

All features work without an API key except **Quiz** (AI grading), which requires `ANTHROPIC_API_KEY`.

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
4. Point a reverse proxy (nginx/Caddy) at port 8501.

### Railway ($5/mo)
1. Connect the GitHub repo in the Railway dashboard.
2. Set start command: `streamlit run web/app.py --server.port $PORT --server.headless true`
3. Set Python version to 3.11 in `railway.toml` or via the dashboard.

## Secrets
Set the following environment variable on the host (or in Railway/Hetzner env):
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

## Cost control
- Set a monthly spend limit in the [Anthropic console](https://console.anthropic.com) (recommended: $50/month for a small launch).
- Rate limiting is built in: 5 quiz submissions per user per 10 minutes.
