"""
One-shot migration: copy Rahul's local RBI mastery + attempt history to Railway.

Run INSIDE the Railway container via `railway ssh`, then:
    python scripts/migrate_mastery_to_railway.py

Data is hardcoded from local export on 2026-06-04.
"""
import sqlite3
from pathlib import Path

ROOT   = Path(__file__).parent.parent
IES_DB = ROOT / "data" / "ies.db"
RBI_DB = ROOT / "data" / "rbi.db"

# ── 1. Find Rahul's UUID from Railway ies.db ────────────────────────────────
ies = sqlite3.connect(IES_DB)
ies.row_factory = sqlite3.Row
row = ies.execute(
    "SELECT user_id, email FROM users WHERE email=?",
    ("rahuldevsingh0108@gmail.com",)
).fetchone()
ies.close()

if not row:
    print("ERROR: rahuldevsingh0108@gmail.com not found in users table.")
    print("Make sure you've signed in on the Railway app at least once.")
    raise SystemExit(1)

uid = row["user_id"]
print(f"Found user: {row['email']} → {uid}")

# ── 2. Mastery rows (exported 2026-06-04, 29 topics) ────────────────────────
MASTERY = [
    # (topic, subject, attempts, correct, mastery_score, coverage_pct, flag_impact, gap_state)
    ("is_lm",              "macro",       3, 1, 0.3333, 0.1875, 0.20, "FLAGGED"),
    ("env_instruments",    "env_econ",    4, 1, 0.2500, 0.4444, 0.0,  "FLAGGED"),
    ("rbi_instruments",    "rbi_banking", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("banking_regulation", "rbi_banking", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("payments_inclusion", "rbi_banking", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("schemes_indices",    "indian_econ", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("fiscal_data",        "pub_finance", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("india_macro_data",   "indian_econ", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("bop_exchange",       "intl_econ",   0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("classical_growth",   "growth",      0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("consumer_theory",    "micro",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("development_theory", "growth",      0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("diagnostic_tests",   "quant",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("fiscal_federalism",  "pub_finance", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("green_metrics",      "env_econ",    0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("index_numbers",      "quant",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("intra_industry",     "intl_econ",   0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("ols_blue",           "quant",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("phillips_lucas",     "macro",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("poverty_hdi",        "growth",      0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("production_theory",  "micro",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("public_expenditure", "pub_finance", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("rbi_monetary_data",  "indian_econ", 0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("trade_theories",     "intl_econ",   0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("welfare_game",       "micro",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("market_structures",  "micro",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("money_banking",      "macro",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("mundell_fleming",    "intl_econ",   0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
    ("qtm_monetary",       "macro",       0, 0, 0.0,    0.0,    0.0,  "UNVISITED"),
]

# ── 3. Attempt rows (7 rows, session_id nulled — local sessions don't exist) ─
ATTEMPTS = [
    # (question_id, answer_given, is_correct, time_taken_s, created_at)
    ("env_env_002", "B", 1, None, "2026-06-03 13:05:24"),
    ("env_env_007", "C", 0, None, "2026-06-03 13:05:24"),
    ("env_env_008", "B", 0, None, "2026-06-03 13:05:24"),
    ("env_env_010", "A", 0, None, "2026-06-03 13:05:24"),
    ("mac_islm_002", "B", 0, None, "2026-06-03 13:43:29"),
    ("mac_islm_006", "B", 1, None, "2026-06-03 13:43:29"),
    ("mac_islm_011", "B", 0, None, "2026-06-03 13:43:29"),
]

# ── 4. Write to rbi.db ───────────────────────────────────────────────────────
rbi = sqlite3.connect(RBI_DB)
with rbi:
    for (topic, subject, attempts, correct, mastery_score,
         coverage_pct, flag_impact, gap_state) in MASTERY:
        rbi.execute("""
            INSERT INTO rbi_topic_mastery
                (user_id, topic, subject, attempts, correct,
                 mastery_score, coverage_pct, flag_impact, gap_state)
            VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(user_id, topic) DO UPDATE SET
                attempts      = excluded.attempts,
                correct       = excluded.correct,
                mastery_score = excluded.mastery_score,
                coverage_pct  = excluded.coverage_pct,
                gap_state     = excluded.gap_state,
                last_updated  = datetime('now')
        """, (uid, topic, subject, attempts, correct,
              mastery_score, coverage_pct, flag_impact, gap_state))

    for (question_id, answer_given, is_correct, time_taken_s, created_at) in ATTEMPTS:
        rbi.execute("""
            INSERT OR IGNORE INTO rbi_attempts
                (user_id, question_id, answer_given, is_correct, time_taken_s, session_id, created_at)
            VALUES (?,?,?,?,?,NULL,?)
        """, (uid, question_id, answer_given, is_correct, time_taken_s, created_at))

rbi.close()

mastery_check = sqlite3.connect(RBI_DB).execute(
    "SELECT COUNT(*) FROM rbi_topic_mastery WHERE user_id=?", (uid,)
).fetchone()[0]
attempt_check = sqlite3.connect(RBI_DB).execute(
    "SELECT COUNT(*) FROM rbi_attempts WHERE user_id=?", (uid,)
).fetchone()[0]

print(f"Done. Railway rbi.db now has {mastery_check} mastery rows + {attempt_check} attempts for {row['email']}.")
