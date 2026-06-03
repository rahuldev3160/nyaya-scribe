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

**Rule:** If `TypeError.*unsupported.*|` appears in the traceback, the fix is NEVER "remove the annotation." The fix is confirming the server is running on `/opt/homebrew/bin/streamlit` (Python 3.11). Removing the annotation is a symptom suppression — it masks the root cause and will recur on the next file that uses modern syntax.

## Auth behaviour (Session 10)

`require_user()` is wired into: `app.py`, `2_Quiz.py`, `3_Study_Brief.py`, `4_My_Progress.py`, `5_Return_Quiz.py`, `6_RBI_Prep.py`, `8_My_Setup.py`, `9_Answer_Review.py`.
**Without OAuth env vars**, these pages redirect to `0_Login.py` which shows a configuration message.
**For local testing without OAuth**: set `GOOGLE_CLIENT_ID=dummy` to skip the redirect (login page shows config message but pages won't auth-gate). Or test pages individually by setting `st.session_state.session_token` manually in browser dev tools.

Pages intentionally open (no auth): `1_Model_Answers.py`, `7_UPSC_Mains.py`.

**Onboarding redirect (NEW S10):** First-time users who complete OAuth are immediately redirected from `app.py` to `8_My_Setup.py` (onboarding wizard). After completing setup they return to the dashboard. Subsequent logins skip straight to dashboard.

## Pages & what they do

| Sidebar label | File | Auth required | Key things to test |
|---|---|---|---|
| Login | `web/pages/0_Login.py` | No | Sign-in button shows; OAuth callback handles `?code=` |
| app | `web/app.py` | Yes | Dashboard loads; "Your Path" banner shows for onboarded users |
| Model Answers | `web/pages/1_Model_Answers.py` | No | Question browse, no DB errors |
| Quiz | `web/pages/2_Quiz.py` | Yes + API key | API key gate shows banner if key absent |
| Study Brief | `web/pages/3_Study_Brief.py` | Yes | Topic briefs load |
| My Progress | `web/pages/4_My_Progress.py` | Yes | Attempt history + Today's Time + Last 7 Days charts |
| Return Quiz | `web/pages/5_Return_Quiz.py` | Yes | MCQ form loads |
| RBI Prep | `web/pages/6_RBI_Prep.py` | Yes | 4 tabs: Key Data / Phase 1 Drill / Tier 2 Quiz / My Progress |
| UPSC Mains | `web/pages/7_UPSC_Mains.py` | No | Paper I/II browse, LaTeX renders |
| My Setup | `web/pages/8_My_Setup.py` | Yes | Onboarding form (4 questions) → AI plan generated → shown; re-accessible anytime |
| Answer Review | `web/pages/9_Answer_Review.py` | Yes | Shows locked Pro feature card (subscription_tier='free' for all users now) |

## RBI Prep tab structure (6_RBI_Prep.py)

- **Key Data** — static rate cards; no DB needed
- **Phase 1 Drill** — reads from `data/rbi.db`, 267 tier-1 questions; Smart Serve or Filter mode
- **Tier 2 Quiz** — 54 hardcoded MCQs, 9 buckets, no DB; instant grading
- **My Progress** — reads rbi_topic_mastery from rbi.db; requires ≥1 drill attempt

## Playwright interaction patterns

**CRITICAL:** Streamlit widgets are CSS-hidden React components. Use `data-testid` selectors.

```python
from playwright.async_api import async_playwright
import asyncio

async def test_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)

        # Navigate sidebar
        await page.get_by_text("RBI Prep", exact=True).first.click()
        await page.wait_for_timeout(2000)

        # Switch tab — use get_by_role("tab"), NOT get_by_text (strict-mode ambiguity)
        await page.get_by_role("tab", name="Tier 2 Quiz").click()
        await page.wait_for_timeout(2000)

        # Click radio buttons — use [data-testid="stRadio"] groups
        groups = page.locator("[data-testid='stRadio']")
        for i in range(await groups.count()):
            try:
                await groups.nth(i).locator("label").first.click(timeout=5000)
            except:
                # Scroll main container, retry
                await page.evaluate(
                    f"document.querySelectorAll('[data-testid=\"stRadio\"]')[{i}]"
                    "?.querySelector('label')?.scrollIntoView()"
                )
                await page.wait_for_timeout(150)
                try:
                    await groups.nth(i).locator("label").first.click(timeout=3000)
                except:
                    pass

        # Submit
        await page.get_by_role("button", name="Submit →").click()
        await page.wait_for_timeout(5000)

        # Verify results — look for expanders
        expanders = page.locator("details")
        count = await expanders.count()
        assert count > 0, "No result expanders — submit may have failed"

        # Check for Python errors on page
        body = await page.content()
        assert "KeyError" not in body and "Traceback" not in body

        await page.screenshot(path="/tmp/test_result.png")
        await browser.close()

asyncio.run(test_page())
```

## Reusable helpers

Import from `scripts/streamlit_test_utils.py`:

```python
from scripts.streamlit_test_utils import (
    start_server, navigate_to_page, click_tab,
    answer_radio_groups, submit_form, check_for_errors,
    get_expander_count
)
```

## Databases

| DB | Tables to check |
|---|---|
| `data/rbi.db` | rbi_questions (267+36), rbi_attempts, rbi_topic_mastery |
| `data/ies.db` | questions, rubrics, model_answers, attempts |
| `data/upsc.db` | same schema as ies.db |

Quick sanity:
```bash
sqlite3 data/rbi.db "SELECT tier, COUNT(*) FROM rbi_questions GROUP BY tier;"
sqlite3 data/ies.db "SELECT COUNT(*) FROM questions;"
```

## Bug status (updated Session 10 — 2026-06-04)

### ALL KNOWN BUGS FIXED ✅

| Bug | Status | Fix applied |
|---|---|---|
| Connection leak — per-rerun `get_conn()` | ✅ FIXED (S8) | `@st.cache_resource` per-page |
| `@st.cache_resource` shared conn unsafe for multi-user | ✅ FIXED (S9) | Per-request `conn = get_conn()` + `conn.close()` on all 7 pages |
| `6_RBI_Prep.py` hardcoded `USER_ID = "rahul"` | ✅ FIXED (S9) | `get_user_id()` on all 6 call sites |
| Silent quiz save failure `2_Quiz.py` | ✅ FIXED (S8) | `st.toast(err)` |
| Mastery not written on first attempt | ✅ FIXED (S8) | `INSERT OR IGNORE` + `UPDATE` |
| No transaction in `submit_return_quiz` | ✅ FIXED (S8) | `with conn:` atomic block |
| `4_My_Progress.py` wrong user import | ✅ FIXED (S9) | `get_user_id()` function |
| No auth on any page | ✅ FIXED (S9) | Google OAuth + `require_user()` on 6 pages |
| No seed DBs for rbi/upsc — data loss on deploy | ✅ FIXED (S10) | `rbi_seed.db` + `upsc_seed.db` committed; first-boot copy in `app.py` |
| Composite indexes missing | ✅ FIXED (S10) | 6 indexes in ies_seed.db + 1 in rbi_seed.db + both init scripts |

### Open (non-blocking)
- Subtopic-level gap surfacing in dashboard — future enhancement
- Answer Review feature (actual implementation) — behind subscription gate, deferred
- YouTube playlist URLs in `web/resources.py` — needs Rahul to add specific playlist links
