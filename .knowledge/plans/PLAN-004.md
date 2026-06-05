# PLAN-004 — English Question Type Templates (IES / RBI / UPSC)

**Date:** 2026-06-05
**Status:** COMPLETE — templates produced as reference document; not yet implemented in DB
**Scope:** Structural format templates for all English question types appearing in IES, RBI Grade B Phase 2, and UPSC Mains English (Paper B)

---

## Purpose

Design templates that will inform:
1. Model answer storage schema (section-by-section: title / intro / body / conclusion / metadata)
2. Automated scoring keyword lists per section per question type
3. Section-by-section spec for human graders and LLM evaluators

---

## Exam Coverage (Verified)

| Exam | Paper | Marks | Nature | Question Types |
|------|-------|-------|--------|----------------|
| UPSC CSE Mains | Paper B (Compulsory English) | 300 | Qualifying (min 75/300) | Essay, Comprehension, Précis, Translation, Grammar/Usage |
| RBI Grade B Phase 2 | Descriptive English | 100 | Counted in merit | Essay (40), Précis (30), Comprehension (30) |
| IES/ESE | GS Paper I Prelims only | MCQ | Not qualifying/descriptive | Synonyms, antonyms, error spotting, one-word sub, idioms |

**IES finding:** No descriptive English in IES Mains. Only ~10–15 MCQ English questions in GS Prelims Paper I.

---

## Templates Produced (9 total)

1. Essay Writing — UPSC (100m) + RBI (40m)
2. Précis / Summary Writing — UPSC (60m) + RBI (30m)
3. Formal Letter (Official Correspondence) — UPSC (15–20m)
4. Informal / Personal Letter — UPSC (10–15m, rare)
5. Reading Comprehension — UPSC (60m) + RBI (30m)
6. Translation — UPSC (40m) only
7. Grammar and Usage / Vocabulary — UPSC (40m) + IES MCQ
8. Report Writing — UPSC (15–20m, rare)
9. Paragraph Writing / Short Composition — UPSC (10–15m)

---

## Key Scoring Conventions Verified

- Précis: Missing title = -2m; missing word count = -2–4m; lifted phrases = -3–5m per instance; length deviation >10% = -4–6m
- Essay: No thesis = -5–8m; bullet points instead of prose = full structure marks lost; new argument in conclusion = -5–7m
- Formal Letter: Missing subject line = -2m; wrong close (faithful/sincere mismatch) = -2–3m
- Comprehension: External knowledge = full marks lost for that question

## UPSC vs RBI Essay Distinction
- UPSC: rewards literary expression + analytical depth
- RBI: rewards policy clarity + multi-dimensional analysis (economic / social / technological / policy dimensions mandatory)

---

## Implementation Notes for App

When storing model answers for English question types, use these section mappings:

| Question Type | intro_text | body_text | conclusion_text | extra fields |
|--------------|-----------|-----------|----------------|-------------|
| Essay | Introduction (hook + thesis) | Body paragraphs (PEEL) | Conclusion (synthesis + way forward) | None |
| Précis | Title | Body (compressed argument) | Closing sentence + [word count] | `title` field |
| Formal Letter | Opening paragraph | Main body | Closing paragraph | `format_block` (sender/date/recipient/subject/salutation) |
| Report | Introduction (purpose) | Findings + Analysis | Recommendations | `metadata_block` (To/From/Sub/Date) |
| Comprehension | N/A | Per-question answers | N/A | Individual Q&A pairs |

---

## Sources Verified

- UPSC.gov.in official PDFs (Essay-Precis-Writing-and-Comprehension.pdf)
- RBI Grade B Phase 2 PYQ analysis 2021–2025 (C4S Courses, Bankwhizz, PracticeMock)
- Anantam IAS pattern guides (verified against actual papers)
- UPSC CSE Mains 2024 Paper B (Insights on India)
