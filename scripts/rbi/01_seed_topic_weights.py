"""Seed rbi_topic_weights from 2024 actual paper distribution + research data."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"

# Source: ixamBee 2024 memory-based PYQ analysis + study plan
# base_weight derived from: (exam_mcqs / 65) × phase2_multiplier
# phase2_multiplier = 1.3 if topic is in Phase 2, else 1.0
TOPIC_WEIGHTS = [
    # Macroeconomics (rank 1)
    ("is_lm",               "macro",       0.20, 13, 1, "stable",    "IS-LM, AD-AS, fiscal/monetary policy. Phase 2 Paper 1."),
    ("qtm_monetary",        "macro",       0.08, 5,  1, "stable",    "QTM velocity, Classical Dichotomy, Monetarism, Taylor Rule"),
    ("phillips_lucas",      "macro",       0.05, 3,  1, "stable",    "Phillips curve, Lucas Critique, expectations, NAIRU"),
    ("money_banking",       "macro",       0.05, 3,  1, "stable",    "Money multiplier, monetary aggregates, transmission chain"),
    # International Economics (rank 2 — REVISED UP)
    ("mundell_fleming",     "intl_econ",   0.10, 6,  1, "increasing","Mundell-Fleming appeared TWICE in 2024. Open economy IS-LM."),
    ("trade_theories",      "intl_econ",   0.07, 4,  1, "stable",    "Ricardo, HO, Stolper-Samuelson, Linder, New Trade Theory (Krugman)"),
    ("bop_exchange",        "intl_econ",   0.05, 3,  1, "stable",    "BOP identity, Marshall-Lerner, J-curve, ERPI"),
    ("intra_industry",      "intl_econ",   0.03, 2,  0, "stable",    "Intra-industry trade index, Grubel-Lloyd, product differentiation"),
    # Indian Economy / Current Affairs (rank 2)
    ("india_macro_data",    "indian_econ", 0.09, 6,  1, "increasing","GDP growth, CPI, fiscal deficit, CAD — last 6 months data"),
    ("rbi_monetary_data",   "indian_econ", 0.05, 3,  1, "stable",    "Repo, CRR, SLR, MPC decisions, surplus transfer"),
    ("schemes_indices",     "indian_econ", 0.04, 3,  0, "increasing","PMJDY, MUDRA, PSL norms, FI-Index, WEF TTDI, MPI"),
    # Growth & Development (rank 3)
    ("classical_growth",    "growth",      0.07, 5,  1, "stable",    "Harrod-Domar (numerical), Solow steady-state, AK model"),
    ("development_theory",  "growth",      0.05, 3,  1, "stable",    "Lewis, Hirschman, Rostow, Leibenstein, Schumpeter, Sen capability"),
    ("poverty_hdi",         "growth",      0.03, 2,  0, "stable",    "Lorenz, Gini, HDI, IHDI, Demographic Transition"),
    # Microeconomics (rank 4, heavy Phase 2)
    ("consumer_theory",     "micro",       0.06, 4,  1, "stable",    "Slutsky, IC analysis, WARP, Giffen, CV/EV. Phase 2 Paper 1."),
    ("market_structures",   "micro",       0.05, 3,  1, "stable",    "Bertrand, Cournot, Stackelberg, price discrimination (3rd-degree numerical)"),
    ("welfare_game",        "micro",       0.04, 2,  1, "stable",    "Pareto, 1st/2nd welfare theorems, Nash equilibrium, prisoner's dilemma"),
    ("production_theory",   "micro",       0.03, 2,  1, "stable",    "Isoquants, CES, Cobb-Douglas, AP/MP, returns to scale"),
    # Quantitative Methods (rank 5, Phase 2 Paper 2)
    ("ols_blue",            "quant",       0.06, 4,  1, "stable",    "OLS residuals, Gauss-Markov BLUE, heteroscedasticity, multicollinearity (appeared TWICE 2024)"),
    ("diagnostic_tests",    "quant",       0.04, 3,  1, "increasing","Jarque-Bera, Ramsey RESET, Durbin-Watson, autocorrelation"),
    ("index_numbers",       "quant",       0.02, 2,  0, "stable",    "Laspeyres, Paasche, Fisher ideal, CPI methodology"),
    # Public Finance (rank 6, partial Phase 2)
    ("public_expenditure",  "pub_finance", 0.04, 3,  1, "stable",    "Wagner's Law, Peacock-Wiseman, Laffer Curve"),
    ("fiscal_federalism",   "pub_finance", 0.03, 2,  1, "stable",    "Finance Commission (15th/16th), vertical imbalance, devolution"),
    ("fiscal_data",         "pub_finance", 0.02, 2,  0, "increasing","GFD, primary deficit, revenue deficit — Budget 2026-27 numbers"),
    # RBI / Banking (current affairs + theory overlap)
    ("rbi_instruments",     "rbi_banking", 0.04, 3,  0, "stable",    "LAF corridor, SDF, OMO, VRRR, CRR, SLR"),
    ("banking_regulation",  "rbi_banking", 0.03, 2,  0, "stable",    "NPA, CRAR, Basel III, PCA, IBC/CIRP"),
    ("payments_inclusion",  "rbi_banking", 0.02, 2,  0, "stable",    "RTGS, NEFT, UPI, CBDC, PSL, financial inclusion"),
    # Environmental Economics (rank 8, NOT in Phase 2)
    ("env_instruments",     "env_econ",    0.02, 2,  0, "stable",    "Pigouvian tax, Coase theorem, carbon tax vs cap-and-trade"),
    ("green_metrics",       "env_econ",    0.01, 1,  0, "stable",    "Green GDP, genuine savings, environmental valuation methods"),
]


def seed_into(conn) -> None:
    conn.executemany(
        """INSERT OR REPLACE INTO rbi_topic_weights
           (topic, subject, base_weight, exam_mcqs_2024, phase2_present, trend, notes)
           VALUES (?,?,?,?,?,?,?)""",
        TOPIC_WEIGHTS,
    )
    conn.commit()


def seed_weights():
    conn = sqlite3.connect(DB_PATH)
    seed_into(conn)
    count = conn.execute("SELECT COUNT(*) FROM rbi_topic_weights").fetchone()[0]
    conn.close()
    print(f"Seeded {count} topic weights into rbi_topic_weights")


if __name__ == "__main__":
    seed_weights()
