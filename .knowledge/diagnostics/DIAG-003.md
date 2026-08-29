---
id: DIAG-003
type: diagnostic
project: descriptive-exams
session: nyaya-arena-law-track-phase5-prep
date: 2026-08-29
status: PARTIALLY RESOLVED
resolution: RISK-02 (Nyaya-Arena docs/risks.md) narrowed, not fully closed
---

# DIAG-003: Bilingual/Devanagari spike (RISK-02)

## Why
CLC DU's law exam is bilingual (Hindi/English). Scribe's stack had zero tested Hindi
handling. Ran a real technical spike (not a design doc) before any law-content work
depends on it.

## (a) SQLite storage round-trip
`sqlite3` (in-memory DB, same driver/behavior as all of Scribe's `.db` files) stores and
reads back a full Devanagari sentence with zero mangling — exact string equality after
round-trip, correct UTF-8 byte length. **No issue.** No real DB file was touched for this
test (used `:memory:` to avoid any risk to live data).

## (b) Claude API scoring in Hindi
One real `claude-haiku-4-5-20251001` call: Hindi rubric + Hindi student answer (deliberately
wrong claim — "Article 21 only covers right to life, not liberty"), asked for a JSON score
+ one-line Hindi feedback. **Result: correct score (1/5), coherent and factually correct
Hindi feedback, valid JSON** (wrapped in a ```json fence — same shape Recall's `_parse_json`
3-tier fallback already handles; confirm Scribe's own JSON-parsing helper for any future
law-scoring route does the same before assuming raw `json.loads` is enough). **No issue.**

## (c) Frontend rendering (Nyaya Arena, Next.js)
`globals.css` sets `body { font-family: Arial, Helvetica, sans-serif }`; page components
override with inline `fontFamily: "system-ui"`. Neither explicitly includes a Devanagari
font, but **this is not a real risk** — browsers automatically substitute a Unicode-capable
system font for glyphs missing from the requested family (standard behavior in Chrome/
Safari/Firefox on any OS shipping a Devanagari font, which all modern ones do). No action
needed here.

## (d) NEW finding: PDF generation has no real Devanagari font registered
`scripts/generate_model_answer_pdfs.py`'s `register_fonts()` tries, in order: `Arial
Unicode.ttf` (often absent on modern Macs), plain `Arial.ttf`, then falls back to
Helvetica. **None of the fallback tiers reliably contain Devanagari glyphs**, and
ReportLab (unlike a browser) does **not** auto-substitute a fallback font for missing
glyphs — a Hindi-medium PDF generated through this same helper would render Devanagari
text as blank boxes/tofu. This is the one real, concrete gap RISK-02 flagged and it's
still open: **before any Hindi-medium PDF export ships (e.g., a law model-answer PDF),
`register_fonts()` needs an actual bundled or system Devanagari-capable TTF (e.g. Noto
Sans Devanagari) added to its fallback chain and tested with a real Hindi render.**

## Net result
Storage, AI scoring, and web rendering are all clear. The PDF export path is the one
genuine unresolved piece — narrower and cheaper to fix than the original "zero bilingual
handling anywhere" framing, but not a closed risk yet.
