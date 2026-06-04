---
description: Run and visually test the Descriptive Exams Streamlit app. Use when asked to run, start, verify, or screenshot any page in this app.
---

# Run & Test — Descriptive Exams App

## Start the server

```bash
pkill -f "streamlit run" 2>/dev/null
cd "/Users/rahulsingh/Desktop/Claude Projects/Descriptive-exams/web"
/opt/homebrew/bin/streamlit run app.py \
  --server.port 8501 --server.headless true &>/tmp/streamlit_app.log &
sleep 4
curl -s http://localhost:8501 | head -3   # confirm "Streamlit" in response
```

## Error triage — MANDATORY before touching any code

When a page crashes, run this before editing anything:

```bash
# Step 1 — read the full traceback
cat /tmp/streamlit_app.log | grep -A10 "Traceback\|Error"

# Step 2 — classify the error
# TypeError: unsupported operand type(s) for | → Python VERSION mismatch, not a code bug
# ImportError / ModuleNotFoundError             → wrong Python env, check which streamlit
# KeyError / AttributeError                     → logic bug, safe to fix directly

# Step 3 — if TypeError with | operator: confirm runtime before touching code
/opt/homebrew/bin/streamlit --version   # must say Python 3.11
which streamlit                          # must resolve to /opt/homebrew/bin/streamlit
```

**Rule:** If `TypeError.*unsupported.*|` appears in the traceback, the fix is NEVER "remove the annotation." The fix is confirming the server is running on `/opt/homebrew/bin/streamlit` (Python 3.11).

## Auth behaviour (Session 11)

`app.py` is now a **pure router** using `st.navigation()`. Pages are grouped by section.

**When not authenticated:** sidebar shows only "Sign In". All other pages redirect to login.
**When authenticated:** sidebar shows Dashboard + 4 sections (Study / Practice / Progress / Account).

`require_user()` is wired into: `Dashboard.py`, `2_Quiz.py`, `3_Study_Brief.py`, `4_My_Progress.py`, `5_Return_Quiz.py`, `6_RBI_Prep.py`, `8_My_Setup.py`, `9_Answer_Review.py`, `10_Profile.py`.

Pages intentionally open (no auth): `1_Model_Answers.py`, `7_UPSC_Mains.py`.

**Single-session enforcement (NEW S11):** `create_session()` deletes ALL prior sessions for a user before creating the new one. One active login per account at all times.

**Onboarding redirect:** First-time users → redirected from Dashboard.py to `8_My_Setup.py`. After setup → back to Dashboard.

## Navigation structure (NEW S11 — st.navigation)

`app.py` is the router only. Dashboard content lives in `web/pages/Dashboard.py`.

| Section | Pages |
|---|---|
| (root) | Dashboard |
| Study | IES PYQs, Study Brief, UPSC Mains |
| Practice | Quiz (locked), Return Quiz, RBI Prep |
| Progress | My Progress, Answer Review (locked) |
| Account | My Setup, Profile |

## Pages & what they do

| Sidebar label | File | Auth required | Key things to test |
|---|---|---|---|
| Sign In | `web/pages/0_Login.py` | No | Sign-in button; OAuth callback handles `?code=`; redirects to Dashboard on success |
| Dashboard | `web/pages/Dashboard.py` | Yes | Days left, readiness %, Your Path banner, Today's Focus, paper tabs |
| IES PYQs | `web/pages/1_Model_Answers.py` | No | Question browse, no DB errors |
| Quiz | `web/pages/2_Quiz.py` | Yes | Shows full form with locked submit + "Coming Soon · ₹4.50" pill |
| Study Brief | `web/pages/3_Study_Brief.py` | Yes | Topic briefs load |
| My Progress | `web/pages/4_My_Progress.py` | Yes | Attempt history + Today's Time + Last 7 Days charts |
| Return Quiz | `web/pages/5_Return_Quiz.py` | Yes | MCQ form loads |
| RBI Prep | `web/pages/6_RBI_Prep.py` | Yes | 4 tabs: Key Data / Phase 1 Drill / Tier 2 Quiz / My Progress |
| UPSC Mains | `web/pages/7_UPSC_Mains.py` | No | Paper I/II browse, LaTeX renders |
| My Setup | `web/pages/8_My_Setup.py` | Yes | Onboarding form → AI plan; resources always from resources.py (never AI-generated URLs) |
| Answer Review | `web/pages/9_Answer_Review.py` | Yes | Shows locked Pro feature card |
| Profile | `web/pages/10_Profile.py` | Yes | Avatar, name, email, tier badge, phone field, study snapshot, Sign Out |

## RBI Prep tab structure (6_RBI_Prep.py)

- **Key Data** — static rate cards; no DB needed
- **Phase 1 Drill** — reads from `data/rbi.db`, 267 tier-1 questions; Smart Serve or Filter mode
- **Tier 2 Quiz** — 54 hardcoded MCQs, 9 buckets, no DB; instant grading
- **My Progress** — reads rbi_topic_mastery from rbi.db; requires ≥1 drill attempt

## Playwright interaction patterns

**CRITICAL:** Streamlit widgets are CSS-hidden React components. Use `data-testid` selectors.
With st.navigation(), page URLs are now: `/Dashboard`, `/IES_PYQs`, `/Quiz`, etc. (title-derived).

```python
from playwright.async_api import async_playwright
import asyncio

async def test_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # Navigate sidebar (labels now match st.navigation titles)
        await page.get_by_text("RBI Prep", exact=True).first.click()
        await page.wait_for_timeout(2000)

        # Switch tab — use get_by_role("tab"), NOT get_by_text
        await page.get_by_role("tab", name="Tier 2 Quiz").click()
        await page.wait_for_timeout(2000)

        # Radio buttons — data-testid approach
        groups = page.locator("[data-testid='stRadio']")
        for i in range(await groups.count()):
            try:
                await groups.nth(i).locator("label").first.click(timeout=5000)
            except:
                await page.evaluate(
                    f"document.querySelectorAll('[data-testid=\"stRadio\"]')[{i}]"
                    "?.querySelector('label')?.scrollIntoView()"
                )
                await page.wait_for_timeout(150)
                try:
                    await groups.nth(i).locator("label").first.click(timeout=3000)
                except:
                    pass

        await page.screenshot(path="/tmp/test_result.png")
        await browser.close()

asyncio.run(test_page())
```

## Databases

| DB | Tables to check |
|---|---|
| `data/rbi.db` | rbi_questions (267+36), rbi_attempts, rbi_topic_mastery |
| `data/ies.db` | pyq_questions, model_answers, users, sessions |
| `data/upsc.db` | pyq_questions, model_answers |
| `seeds/ies_seed.db` | Same schema, zero user rows — never use for live sessions |
| `seeds/rbi_seed.db` | Same, zero user rows |
| `seeds/upsc_seed.db` | Same, zero user rows |

Quick sanity:
```bash
sqlite3 data/rbi.db "SELECT tier, COUNT(*) FROM rbi_questions GROUP BY tier;"
sqlite3 data/ies.db "SELECT COUNT(*) FROM pyq_questions;"
sqlite3 data/ies.db "SELECT COUNT(*) FROM users;"
```

## Bug status (updated Session 11 — 2026-06-04)

### ALL KNOWN BUGS FIXED ✅

| Bug | Status | Fix applied |
|---|---|---|
| Connection leak | ✅ FIXED (S8) | Per-request conn + close |
| Hardcoded USER_ID='rahul' | ✅ FIXED (S9) | get_user_id() everywhere |
| No auth on pages | ✅ FIXED (S9) | Google OAuth + require_user() |
| No seed DBs | ✅ FIXED (S10) | seeds/ dir + first-boot copy |
| Seeds hidden by volume mount | ✅ FIXED (S11) | Moved seeds/ outside data/ |
| OAuth redirect_uri mismatch | ✅ FIXED (S11) | /Login not /0_Login |
| AI-hallucinated resource URLs | ✅ FIXED (S11) | _authoritative_resources() always overrides |
| Multiple simultaneous sessions | ✅ FIXED (S11) | create_session() deletes all prior sessions first |
| Cluttered sidebar | ✅ FIXED (S11) | st.navigation() with auth-aware sections |

### Open (non-blocking)
- Data migration: run `railway run python scripts/migrate_local_data.py` to link Rahul's RBI data to his Google account
- YouTube playlist URLs in `web/resources.py` — needs Rahul to add specific playlist links
- Payment wallet feature — plan in `docs/PAYMENT_PLAN.md`, ~23h to build (post-exam)
- Subtopic-level gap surfacing in dashboard — future enhancement
- Answer Review actual implementation — behind subscription gate, deferred
