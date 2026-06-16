# UI-REDESIGN-001 — Clean Navigation & Noise Reduction
**Date:** 2026-06-16
**Status:** PHASE 1 COMPLETE (S39) — Items 1,2,4,5,6,7,9,10,12,13,15 implemented; Items 3 (GS toggle), 8 (ref-tools position), 11 (English Insights tab) pending
**Scope:** Cross-exam UI audit: reduce visual noise, flatten navigation flow, add UPSC GS toggle, equalize all four exam tabs, remove dead/pro-gated routes

---

## Audit Summary

The app has 15 blueprints and 31 routes. The core exam content (dashboards, quizzes, model answers, topic briefs, drills) is solid and well-structured. The noise is concentrated in three places: (1) the IES dashboard has a duplicate "Test Myself" CTA block — the first-time empty-state card and the always-visible full-width button both appear together when the user has zero attempts; (2) the mobile nav devotes one of its 4 fixed slots to "Quick Drill" (an RBI-only shortcut), which actively demotes IES and UPSC content on mobile; (3) the Answer Review route (`/progress/review`) is a locked Pro page that shows a padlock and "coming soon" — it is reachable from the sidebar's Progress item flow but provides zero value to any current user. Additionally, the UPSC tab currently shows "Economics Optional" only; the GS Mains expansion needs a toggle within that tab rather than a 5th nav tab. The feedback route is low-value as a permanent sidebar item for daily users. Setup is essentially a one-time onboarding flow but appears alongside daily-use items in the nav.

---

## Route Map

| Route | Blueprint | Template | Decision |
|-------|-----------|----------|----------|
| `GET /` | app.py (index) | — (redirect) | KEEP — smart routing by exam_focus |
| `GET /auth/login` | auth_bp | login.html | KEEP |
| `POST /auth/login` | auth_bp | — (redirect) | KEEP |
| `GET /auth/callback` | auth_bp | — (redirect) | KEEP |
| `GET /auth/logout` | auth_bp | — (redirect) | KEEP |
| `GET /dashboard` | dashboard_bp | dashboard.html | KEEP — IES hub |
| `POST /ies/topics/<id>/state` | dashboard_bp | — (redirect) | KEEP |
| `GET /ies/answers` | ies_answers_bp | ies_answers.html | KEEP |
| `GET /ies/diagram/<dtype>.png` | ies_answers_bp | — (PNG) | KEEP |
| `GET /ies/brief` | ies_brief_bp | ies_brief.html | KEEP |
| `GET /ies/quiz` | ies_quiz_bp | ies_quiz.html | KEEP |
| `POST /ies/quiz/submit` | ies_quiz_bp | — (redirect) | KEEP |
| `POST /ies/quiz/rate` | ies_quiz_bp | — (redirect) | KEEP |
| `GET /ies/return-quiz` | ies_return_quiz_bp | ies_return_quiz.html | KEEP |
| `POST /ies/return-quiz/submit` | ies_return_quiz_bp | — (redirect) | KEEP |
| `GET /rbi` | rbi_dashboard_bp | rbi_dashboard.html | KEEP |
| `POST /rbi/topics/<t>/drill` | rbi_dashboard_bp | — (redirect) | KEEP |
| `GET /rbi/prep` | rbi_prep_bp | rbi_prep.html | KEEP |
| `POST /rbi/prep/tier2/submit` | rbi_prep_bp | — (redirect) | KEEP |
| `POST /rbi/prep/drill/submit` | rbi_prep_bp | — (redirect) | KEEP |
| `GET /rbi/prep/drill/questions` | rbi_prep_bp | — (redirect) | DEMOTE — internal redirect helper, never user-facing |
| `GET /upsc` | upsc_dashboard_bp | upsc_dashboard.html | KEEP — needs GS toggle added |
| `POST /upsc/topics/<id>/state` | upsc_dashboard_bp | — (redirect) | KEEP |
| `GET /upsc/mains` | upsc_bp | upsc_mains.html | KEEP |
| `GET /english/dashboard` | english_bp | english_dashboard.html | KEEP |
| `GET /practice/english` | english_bp | english.html | KEEP |
| `POST /practice/english/score` | english_bp | — (redirect) | KEEP |
| `GET /progress` | progress_bp | progress.html | KEEP — good macro view |
| `GET /progress/review` | progress_bp | answer_review.html | REMOVE from nav — pro-locked placeholder, zero current value |
| `GET /setup` | setup_bp | setup.html | DEMOTE — one-time flow; accessible via profile or banner, not primary nav |
| `GET|POST /profile` | profile_bp | profile.html | KEEP |
| `GET /feedback` | feedback_bp | feedback.html | DEMOTE — move to "More" sheet only, not main sidebar |
| `POST /feedback/submit` | feedback_bp | — (redirect) | KEEP (form action) |

**Summary:** 33 routes total (including form endpoints). KEEP: 28. DEMOTE: 3 (setup, feedback, /rbi/prep/drill/questions). REMOVE from nav: 1 (answer_review). No routes deleted — all data remains intact.

---

## Ranked Changes

### 1. [HIGH] Fix duplicate IES "Test Myself" CTA — dashboard.html lines 56–75

**File:** `web/templates/dashboard.html` lines 56–75
**Problem:** When `micro_mcq == 0 and micro_descriptive == 0` a full "Start here" card appears (lines 56–71), then immediately below it the always-visible full-width "📋 Test Myself — MCQ" button (lines 72–75) appears as well. When the user has done at least one attempt, only the bottom button shows — but the layout still has an awkward gap where the card was. New users see two back-to-back CTAs for the same thing.
**Action:** Remove the outer `{% if micro_mcq == 0 and micro_descriptive == 0 %}` block (lines 56–71 inclusive). The always-on "📋 Test Myself — MCQ" button (line 72–75) already covers this. If you want a first-time orientation, fold it into the welcome banner at lines 6–17 instead.
**Reason:** Two CTAs for the same action on the same screen is classic UI noise. Removing the conditional block simplifies the template and removes a code path.

---

### 2. [HIGH] Fix mobile nav — replace "Quick Drill" with UPSC tab — base.html line 95

**File:** `web/templates/base.html` lines 86–108
**CSS constraint:** 4-column mobile grid, CSS-MOB-001 — exactly 4 tabs.
**Current tabs:** IES Prep | RBI Prep | ⚡ Quick Drill | Progress
**Problem:** "Quick Drill" (line 95) is an RBI-specific shortcut that launches the RBI phase1 drill immediately. It occupies the #3 slot in the mobile nav, demoting UPSC and English off the primary nav entirely. On mobile, UPSC and English are only reachable via the "More" sheet — they are second-class citizens.
**Action:** Replace the Quick Drill tab (lines 95–98) with the UPSC tab:
```html
<a href="/upsc" class="mobile-nav-item {% if active_page in ['upsc_dashboard','upsc_mains'] %}active{% endif %}">
    <span class="mobile-nav-icon">🎓</span>
    <span class="mobile-nav-label">UPSC</span>
</a>
```
Move the Quick Drill shortcut into the "More" sheet (the mobile-more-sheet div, lines 110–119) alongside English, Feedback, Setup, Profile. The More sheet can hold any number of items.
**Reason:** All four exam domains should be equally accessible. UPSC is a 500-mark optional that belongs on primary nav. RBI drill is a one-exam shortcut that should not displace a full exam tab.

---

### 3. [HIGH] Add UPSC GS toggle on the UPSC tab — upsc_dashboard.html and upsc_dashboard_bp.py

**Files:**
- `web/templates/upsc_dashboard.html` — add a toggle between "Economics Optional" and "GS Mains" at the top, above the metric row (after line 16)
- `web/blueprints/upsc_dashboard_bp.py` — the route at line 118 (`/upsc`) needs a `?section=` query param to switch between `eco_opt` and `gs_mains`
**Action:** Add a segmented control / toggle at the top of the UPSC dashboard page:
```html
<div style="display:flex;gap:8px;margin-bottom:20px;">
  <a href="/upsc?section=eco_opt" class="btn {% if section == 'eco_opt' %}btn-primary{% endif %}">Eco Optional</a>
  <a href="/upsc?section=gs_mains" class="btn {% if section == 'gs_mains' %}btn-primary{% endif %}">GS Mains</a>
</div>
```
When `section=gs_mains`, render the UPSC GS dashboard content (PLAN-017 schema). When `section=eco_opt` (default), render the existing economics optional topic list. No new bottom nav tab is added — CSS-MOB-001 compliant.
**Reason:** GS Mains expansion requires a new UI entry point inside the existing UPSC tab. This is the least disruptive way to add it.

---

### 4. [HIGH] Remove Answer Review from sidebar and mobile More sheet — base.html

**File:** `web/templates/base.html`
**Problem:** `/progress/review` is a pure "coming soon / Pro locked" page (answer_review.html lines 16–33). It has no functional content for free users. It does not appear in the sidebar currently (checked — it's not there), but it IS a registered route and linked from nowhere critical. However it is reachable and confusing.
**Action:** No sidebar entry to remove (already absent). Ensure no link to `/progress/review` exists in any template that a daily user would encounter. Add a DB-level note that this route will be activated post-Pro launch. Do not delete the blueprint or template — preserve for Pro rollout.
**To verify:** `grep -r "progress/review" web/templates/` — confirm no accidental link.
**Reason:** A locked padlock page with "coming soon" is noise that erodes trust. Keep the route live (so direct links don't 404) but don't surface it.

---

### 5. [HIGH] Demote Feedback from main sidebar to "More" only — base.html line 61

**File:** `web/templates/base.html` line 61
**Problem:** The sidebar's "Track & Account" group has: My Progress | Feedback | Study Plan | Profile | Sign Out. "Feedback" is a bug/feature submission form — it's something a user touches once a week at most, not a daily-use feature. It sits between Progress (high value, daily) and Study Plan/Profile (setup-level).
**Action:** Remove the Feedback link from the sidebar's "Track & Account" nav group (line 61). It already exists in the mobile More sheet (base.html line 115). For desktop, add it to the bottom of the sidebar as a small tertiary link after Sign Out, or inside a "..." overflow:
```html
<a href="/feedback" class="nav-link" style="font-size:0.75rem;color:#6E6E73;">💬 <span class="nav-text">Send Feedback</span></a>
```
**Reason:** Feedback is maintenance UX, not study UX. Removing it from the primary nav group reduces cognitive load on the sidebar without deleting the feature.

---

### 6. [MEDIUM] Demote "Study Plan" in sidebar — make it tertiary — base.html line 63

**File:** `web/templates/base.html` line 63
**Problem:** `/setup` is a one-time onboarding wizard that generates a study plan. After first run, it's rarely needed (only when re-doing the plan with `?redo=1`). It sits in the "Track & Account" group between Feedback and Profile — all three look equally important.
**Action:** Move the Study Plan link below Profile and reduce its visual weight:
```html
<a href="/setup" class="nav-link" style="font-size:0.75rem;opacity:0.75;" {% if active_page == 'setup' %}active{% endif %}>📋 <span class="nav-text">Study Plan</span></a>
```
Or: add a "⚙️ Redo study plan" link inside the Profile page template instead, and remove it from the sidebar entirely.
**Reason:** Once a user has their plan, this link is rarely clicked. It should not compete visually with Progress and Profile.

---

### 7. [MEDIUM] Equalize exam headers — remove IES emoji bias, add consistent subtitle format — dashboard.html, rbi_dashboard.html, upsc_dashboard.html, english_dashboard.html

**Files:**
- `web/templates/dashboard.html` line 22: `📚 IES 2026 Study Dashboard`
- `web/templates/rbi_dashboard.html` line 14: `🏦 RBI DEPR 2026 Dashboard`
- `web/templates/upsc_dashboard.html` line 14: `UPSC Eco Optional` (no emoji, inconsistent)
- `web/templates/english_dashboard.html` line 10: `✏️ English Dashboard`

**Action:** Standardize all four headers to:
- `web/templates/upsc_dashboard.html` line 14: add `🎓` prefix to h1, change subtitle at line 15 to match format of others (`Mains 2026 · August 22 · Paper I + Paper II`)
- Ensure all four dashboards share the same header structure: `<h2>[emoji] [Exam Name] Dashboard</h2>` + subtitle

**Reason:** UPSC dashboard header is a plain `<h1>` with no emoji and a vague subtitle ("GS Paper + Optional" — which is wrong, it's Eco Optional only). Visual inconsistency makes exams feel unequal.

---

### 8. [MEDIUM] IES dashboard — move "Reference tools" buttons above the state-summary section, not below the primary CTA — dashboard.html lines 76–81

**File:** `web/templates/dashboard.html` lines 76–81
**Problem:** The reference buttons (Write an Answer, Model Answers, Topic Summaries) appear at lines 76–81, immediately after the primary CTA. This is good placement. However the crunch-mode banner at lines 83–89 and the skeleton/focus-cards below (lines 92–304) push them far down on mobile after page-load animation completes. The actual content order is fine on desktop but the skeleton + animation sequence means mobile users see the skeleton for a beat before content appears.
**Action:** No position change needed. However: add `display:none` skeleton for the reference-tools section so it also shimmers during load (minor polish). Or: consider rendering the reference tools row _inside_ the `dashboard-content` div (currently it is outside, above the skeleton div). Move lines 76–81 to inside `.dashboard-content` immediately after `<!-- Today's Focus -->` header.
**Reason:** Currently the ref tools disappear during the skeleton-load animation because the `dashboard-content` div has `opacity:0` while loading. The buttons at lines 76–81 are outside `.dashboard-content` and remain visible, creating a flash where only the buttons and CTA show before content loads.

---

### 9. [MEDIUM] IES dashboard — remove "Reset" button from topic rows — dashboard.html line 232–235

**File:** `web/templates/dashboard.html` lines 231–235
**Problem:** Every topic row in the paper tabs has 4 buttons: Quiz | Advance | Verify | Reset. The "Reset" button (POST to state=UNVISITED) is destructive — it wipes all state for a topic. It is in the same row as the study buttons, no confirmation, just a red btn-danger. On mobile the topic-row collapses to 4 columns so Reset is visible and easy to accidentally tap.
**Action:** Remove the Reset form+button from `dashboard.html` topic rows (lines 231–235). The state can be reset via the focus cards if truly needed, or add it as a hidden action in a `<details>` expander. The same Reset button exists on the UPSC dashboard (`upsc_dashboard.html` lines 134–136) — remove it there too.
**Reason:** Destructive action with no confirmation on a mobile-accessible button is a usability risk. Users who want to reset can do so via a less prominent path.

---

### 10. [MEDIUM] RBI dashboard — the metrics grid (lines 155–179) duplicates stats already shown in "My Progress" panel above it — rbi_dashboard.html

**File:** `web/templates/rbi_dashboard.html` lines 154–179
**Problem:** The "My Progress" panel (lines 110–150) shows Mastery Score, Exam Readiness, Qs Attempted, Topics ≥50%. Then immediately below (lines 154–179), a second gem-card grid shows P1 Answered, P1 Accuracy, Mastery, Readiness — 4 of which are the same numbers in different cards. The page has the same data twice, formatted differently.
**Action:** Merge the two sections. Replace the standalone metrics grid (lines 154–179) with just P1 Answered and P1 Accuracy cards (the two that are not already in "My Progress"). Add these two to the `dash-2col` grid inside "My Progress" panel as additional stat cells.
**Reason:** Duplicated stats create visual noise and make the page feel bloated. The RBI dashboard is already long — Subject Coverage + Top Gaps + Metrics grid + "My Progress" panel is redundant.

---

### 11. [MEDIUM] English dashboard — the "Insights" tab is empty or thin — english_dashboard.html

**File:** `web/templates/english_dashboard.html` (tab 4: Insights)
**Action:** Read what's actually in the Insights tab panel. If it's empty or just a placeholder, either: (a) remove the Insights tab button from the tab-bar and keep the content reachable from Progress tab; or (b) fold Insights content into the Practice tab.
**Note:** Need to read lines 80+ to confirm. Flag for review before removing.
**Priority:** MEDIUM — confirm first.

---

### 12. [LOW] Sidebar desktop — the `📚 Exam Prep` title in sidebar is generic — base.html line 46

**File:** `web/templates/base.html` line 46
**Problem:** The sidebar title is `📚 Exam Prep`. The product is called Nyaya Scribe.
**Action:** Change sidebar title text from `Exam Prep` to `Nyaya Scribe` (or just `Nyaya` if space is tight).
**CSS:** No changes needed — `.sidebar-title` styles are fine.
**Reason:** Brand alignment. The product is Nyaya Scribe per CLAUDE.md.

---

### 13. [LOW] Progress page — "Detailed Progress" links section (lines 72–86) uses anchor `#ies-progress` — progress.html line 74

**File:** `web/templates/progress.html` line 74
**Problem:** The link `href="/dashboard#ies-progress"` uses an anchor fragment `#ies-progress` that does not exist as an `id` in `dashboard.html`. The page will load correctly but won't scroll to any section.
**Action:** Either add `id="ies-progress"` to the "My IES Progress" section header in `dashboard.html` (line 258), or change the link in progress.html to `/dashboard` without the anchor.
**Reason:** Broken anchor creates confusion when the page doesn't scroll to the expected section.

---

### 14. [LOW] Remove /rbi/prep/drill/questions redirect route — rbi_prep_bp.py lines 559–569

**File:** `web/blueprints/rbi_prep_bp.py` lines 559–569
**Problem:** The `drill_questions_redirect` route at `/rbi/prep/drill/questions` is a pure redirect helper (GET → redirect to /rbi/prep with params). It has no template, no data access, and no direct link from any template (confirmed: not referenced in any template). It was likely used during development to test filter params.
**Action:** Delete the route function (lines 559–569). Keep the Blueprint registered. No template changes needed.
**Risk:** Low — confirm no external links with `grep -r "drill/questions" web/templates/`.
**Reason:** Dead route clutters the blueprint.

---

### 15. [LOW] UPSC dashboard — duplicate `id` attribute on paper tabs div — upsc_dashboard.html line 57

**File:** `web/templates/upsc_dashboard.html` line 57
**Problem:** The div has both `style="margin-bottom: 2rem;"` and a second `id="topics"` attribute: `<div id="upsc-papers" style="margin-bottom: 2rem;" id="topics">`. Two `id` attributes on one element — the second `id="topics"` is ignored by browsers but is invalid HTML. The `upsc_topic_state` redirect (upsc_dashboard_bp.py line 237) redirects to `url_for("upsc_dashboard.upsc_dashboard_page") + "#topics"` — this anchor won't work because the `id="topics"` is ignored when there's a preceding `id="upsc-papers"`.
**Action:** In `upsc_dashboard.html` line 57, remove the duplicate `id="topics"` or rename it: change to `<div id="upsc-papers" style="margin-bottom: 2rem;">` and update the redirect in `upsc_dashboard_bp.py` line 237 to `+ "#upsc-papers"`.
**Reason:** Invalid HTML, broken scroll-to-anchor behavior.

---

## CSS Changes Needed

| Change | File | Lines | Notes |
|--------|------|-------|-------|
| Mobile nav — replace Quick Drill item | `web/static/style.css` | 538–571 | No CSS changes needed — same 4-column structure, just swap content |
| `.topic-row` — 4 buttons → 3 buttons on desktop | `web/static/style.css` line 509 | Change `grid-template-columns: 4fr 2fr 1fr 1fr 1fr 1fr` to `4fr 2fr 1fr 1fr 1fr` when Reset button is removed |
| `.mobile-nav` — active state for UPSC pages | `web/static/style.css` | 567–568 | The `.mobile-nav-item.active` rule already handles this — just add correct active condition in template |
| Sidebar feedback link styling | `web/templates/base.html` | 61 | Use inline `style="font-size:0.75rem;color:#6E6E73;"` on the nav-link for demoted feedback |

---

## What NOT to touch

1. **All DB schemas** — ies.db, rbi.db, upsc.db, nyaya.db, english.db, upsc_gs.db. No schema changes in this plan.
2. **All attempt/mastery data** — descriptive_attempts, return_quiz_attempts, rbi_attempts, english_attempts. User progress must carry forward.
3. **All gap_states data** — topic state tracking is the core of the IES and UPSC study flows.
4. **The 4-tab mobile nav count** — CSS-MOB-001: exactly 4 tabs. Swapping Quick Drill for UPSC keeps the count at 4.
5. **Auth flow** — login.html, /auth/login, /auth/callback, /auth/logout. Do not touch.
6. **Feedback blueprint** — keep the route and template live. Only demote it in the nav.
7. **Answer Review route** — keep `/progress/review` alive (no 404). Just don't add it to any nav.
8. **Setup/onboarding flow** — the study plan generation with Claude AI is valuable. Demote the nav link only; do not change the route or template logic.
9. **RBI Key Data seed** (app.py lines 99–147) — factual data, do not touch.
10. **All diagram generation** (`/ies/diagram/<dtype>.png`) — matplotlib diagrams, used in model answers.
11. **JINJA2-001 constraint** — never rename a template variable to `items`, `keys`, `values`, `get`. Any new template variables for GS toggle must use names like `section`, `gs_section`, `upsc_mode`.

---

## Implementation Order

Priority order for a single session:
1. Fix IES duplicate CTA (change 1 — 5 min)
2. Fix mobile nav Quick Drill → UPSC swap (change 2 — 10 min)
3. Fix UPSC duplicate id bug (change 15 — 2 min)
4. Fix broken anchor #ies-progress (change 13 — 2 min)
5. Remove Reset buttons from topic rows (change 9 — 5 min)
6. Demote Feedback in sidebar (change 5 — 5 min)
7. Fix UPSC dashboard header format (change 7 — 5 min)
8. Merge RBI duplicate metrics (change 10 — 20 min)
9. Demote Setup in sidebar (change 6 — 5 min)
10. Add UPSC GS toggle stub (change 3 — 1 session, depends on PLAN-017 implementation)

Changes 11–14 can wait until a polish pass.
