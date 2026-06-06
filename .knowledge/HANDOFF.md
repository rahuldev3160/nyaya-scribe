# HANDOFF — Descriptive Exams

Last updated: 2026-06-06 (Session 24)

---

## Session 24 — Essay Quality Overhaul

### What was done

1. **Root-cause diagnosis — essay quality bug**
   - `seeds/ies_seed.db` had old narrow, analytically-framed essay questions (e.g. "Analyse the causes of India's current account deficit") from the original seeding
   - `m008` (S23) only updated `data/ies.db` via `UPDATE` — it never touched the seed DB
   - Fresh local installs (seed copy → app start without running `scripts/migrate.py`) would get the old narrow questions
   - `_run_migrations()` in `app.py` only handles DDL (add column, create tables) — the `m*.py` content migrations were Railway-only

2. **Fix 1 — seed DB backfill**
   - Applied m008 and m009 directly to `seeds/ies_seed.db` so fresh installs start with the correct questions

3. **Fix 2 — auto-migration on app start**
   - Added `_run_content_migrations()` to `web/app.py::create_app()` — calls `scripts/migrate.py::main()` on every startup
   - Idempotent (tracks applied migrations in `_migrations` table) — safe to run on Railway too

4. **m009 — Open-ended UPSC-style essay replacement**
   - Replaced all 5 old proposition-based ("do you agree?") essays with open-canvas UPSC themes:
     1. The cost of inequality is borne by the whole society, not just the poor
     2. Agriculture is India's past — but it need not remain India's problem
     3. A democracy that fails its poor has failed its purpose
     4. India's cities are broken by design — but they can be repaired by will
     5. The climate crisis and the development crisis are one and the same crisis
   - Applied to `data/ies.db` and `seeds/ies_seed.db`

5. **m010 — 3 economics/banking essays added**
   - eng_essay_006: The invisible hand of the market needs the visible hand of regulation
   - eng_essay_007: A bank is not merely a custodian of money — it is a custodian of public trust
   - eng_essay_008: Financial inclusion is the unfinished agenda of Indian independence
   - All with ~500-word model answers (intro / body / conclusion)
   - Applied to `data/ies.db` and `seeds/ies_seed.db`

### Key decisions

- **DECIDE-S24-01**: Essay prompts must be open-canvas (no built-in thesis/binary choice) matching UPSC Essay Paper style. Proposition-test format ("do you agree") is not acceptable.
- **DECIDE-S24-02**: Every content migration must be applied to BOTH `data/ies.db` AND `seeds/ies_seed.db`. The seed is the source of truth for Railway fresh deploys.
- **DECIDE-S24-03**: `create_app()` now auto-runs `scripts/migrate.py` so local installs never require a manual migration step.

### DB state at session end (ies.db — english_questions)

| type_id | count | model answers |
|---------|-------|---------------|
| essay   | 8     | all ✅        |
| letter  | 3     | all ✅        |
| précis  | 4     | all ✅        |
| rc      | 4     | all ✅        |
| report  | 3     | all ✅        |
| **total** | **22** | **all ✅** |

---

## Exact Next Step

Resume here in S25:
- **Open items from PLAN-011 (P2/P3):**
  1. Progress tab: "Avg Auto Score / Avg Self Score" columns always show 0 after scoring removal — replace with attempt count + word count stats
  2. Précis word count inconsistency: Insights tab says 150–170w; seed `word_count_target` = 140 — align to one standard
  3. RC marks mismatch: Insights says 5m each; seeds have 10m per question — audit and fix
  4. Custom domain: `nyayascribe.com` → Railway custom domain + OAuth redirect update (pending domain registration)

---

## Watch For

- Seed DB sync: any future `m0XX` that uses `UPDATE` must also be applied to `seeds/ies_seed.db` explicitly (the migration runner only tracks `data/*.db`)
- `_run_content_migrations()` adds ~100ms to app cold start — acceptable for now; if startup time becomes an issue, add a filesystem-level lock check
