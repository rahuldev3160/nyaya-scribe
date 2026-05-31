# Deploy to Streamlit Community Cloud

## Prerequisites
- GitHub account with this repo pushed
- Anthropic API key

## Steps

1. **Push the repo to GitHub** (DB is committed at `data/ies.db`, ~14 MB)

2. **Go to [share.streamlit.io](https://share.streamlit.io)** → New app

3. **Configure:**
   - Repository: `your-github-username/Descriptive-exams`
   - Branch: `main`
   - Main file path: `web/app.py`
   - Python version: 3.9

4. **Add secrets** (Advanced settings → Secrets):
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-api03-..."
   ```

5. **Deploy** — first boot takes ~2 minutes to install dependencies.

## Cost control
- Set a monthly spend limit in the [Anthropic console](https://console.anthropic.com) (recommended: $50/month for a small launch)
- Rate limiting is built in: 5 quiz submissions per user per 10 minutes

## Local development
```bash
cp .env.example .env
# Edit .env with your API key
/Users/rahulsingh/Library/Python/3.9/bin/streamlit run web/app.py
```
