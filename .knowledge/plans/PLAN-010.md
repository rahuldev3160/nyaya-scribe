---
name: PLAN-010
description: S20–S22 — Dashboard UI uplift across all 4 dashboards + English content seeding batch2 (15 questions, 5 types)
metadata:
  type: plan
status: COMPLETE
session: S20-S22
commit: 84674b7
---

# PLAN-010 — Dashboard UI Uplift + English Content Batch 2

## Status: COMPLETE

## S20–21: Dashboard UI Uplift

### RBI Dashboard (`rbi_dashboard.html`)
- Action buttons moved above the data grid
- "Priority 1 MCQs — Smart Session" + "Priority 2 MCQs" at `padding:14px 20px; font-size:1rem; font-weight:700; flex:1`
- Subject Coverage + Top Gaps merged into 2-column side-by-side grid
- Full Key Data button deleted (cross-verified: 40 DB rows = 40 hardcoded KEY_SECTIONS rows — identical data)
- "Priority 2 Quiz" renamed → "Priority 2 MCQs"
- Top Gaps column: `grid-template-columns:2fr 1fr auto` with subject as subtitle

### IES Dashboard (`dashboard.html`)
- Primary tier: IES Quiz + IES Past Papers at `padding:14px 20px; font-size:1rem; font-weight:700`
- Secondary tier: PYQ Answers + Study Brief demoted to `btn-sm`

### UPSC Dashboard (`upsc_dashboard.html`)
- Single primary CTA "→ Browse Model Answers" promoted above paper tabs

### English Dashboard (`english_dashboard.html`)
- "▶ Open English Practice" CTA added above tabs
- Model Answers tab refreshed with past-year style prompts

### Sidebar (`base.html`)
- `<a href="/dashboard" class="sidebar-title">` → `<div class="sidebar-title">` (zero data loss; no hover state existed; confirmed no Python/JS references)

### Pre-commit Hook Fix (`.knowledge/bugs/BUG-016.md`)
- Pattern `\.(items|keys|values|get|pop|update|clear)(?!\s*\()` was matching `.getElementById` in JS because `get` is a prefix of `getElementById`
- Fixed with word boundary: `\.(items|keys|values|get|pop|update|clear)\b(?!\s*\()`

## S22: English Content Seeding Batch 2

### Script: `scripts/seed_english_batch2.py`
- Idempotent — INSERT OR IGNORE pattern
- Seeds both `data/ies.db` and `seeds/ies_seed.db`
- Creates English tables if absent (for fresh seeds DB)

### Content Added (15 questions):

**Essays (3 new, total 5):**
- eng_essay_003: RBI macroprudential policy — CRAR, CCyB, PCA, FSDC, NPA decline 11.2%→2.2%
- eng_essay_004: Digital Public Infrastructure (UPI, AA, JAM trinity, DPDP risks)
- eng_essay_005: Farm loan waivers — moral hazard, MSP, fiscal burden, PM-KISAN alternative

**Précis (3 new, total 4):**
- eng_precis_002: India's fiscal consolidation — FRBM journey, NK Singh Committee dual anchors
- eng_precis_003: Climate finance — sovereign green bonds ₹16,000cr, NGFS, NDC gaps
- eng_precis_004: Labour market informality — 90% informal, Labour Codes 2019-20, e-Shram

**Reading Comprehension (3 new, total 4):**
- eng_rc_002: IBC/CIRP — 650-day mean vs 270-day statutory limit; NCLT capacity constraints
- eng_rc_003: Demographic dividend — two conditions: productive employment + human capital (ASER)
- eng_rc_004: GST federalism — states surrendered sales tax for 5-yr compensation that has expired

**Letters (3 new, total 3):**
- eng_letter_001: To RBI Governor — external benchmark migration, OMO liquidity absorption
- eng_letter_002: To 16th Finance Commission — 41%→44% divisible pool share, income-distance criterion
- eng_letter_003: To DFS Secretary — PSL sub-target 7.5%→10%, cash-flow lending, co-lending

**Reports (3 new, total 3):**
- eng_report_001: To RBI Deputy Governor — MCLR lag, SDF floor, NPA constraints, informal sector
- eng_report_002: To Finance Secretary — CAD 1.1% GDP, crude+gold import pressure, PLI recommendations
- eng_report_003: To NABARD Chairman — rural credit gap, KCC for tenant farmers, RIDF cold chain

### Keyword schema
- All questions have section-level keywords (required + bonus)
- Letter/report keywords include format-checking patterns (subject line, salutation, To/From header, yours faithfully, signature)

## Remaining (P2/P3)
- Live word count counter on answer textarea (JS)
- Model answer reveal panel after submission
- `scoring/constants.py` + `scoring/validator.py` (PLAN-005 gap)
