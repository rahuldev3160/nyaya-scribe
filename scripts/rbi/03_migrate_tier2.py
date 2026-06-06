"""
Migrate existing 36 hardcoded Tier 2 MCQs from 6_RBI_Prep.py → rbi.db.
Maps each BUCKETS entry to the rbi_questions schema with tier=2.
Run after 00_init_rbi_db.py.
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"

# Full BUCKETS data extracted from 6_RBI_Prep.py
# Maps to: subject, topic, tier=2
BUCKET_META = {
    "rbi_instruments": ("rbi_banking", "rbi_instruments"),
    "banking_norms":   ("rbi_banking", "banking_regulation"),
    "payment_systems": ("rbi_banking", "payments_inclusion"),
    "fin_inclusion":   ("indian_econ", "schemes_indices"),
    "fiscal_budget":   ("pub_finance", "fiscal_data"),
    "india_economy":   ("indian_econ", "india_macro_data"),
}

QUESTIONS = [
    # rbi_instruments
    {
        "bucket": "rbi_instruments",
        "id": "t2_ri_001",
        "question": "Which rate serves as the floor of the LAF corridor as of April 2022?",
        "option_a": "Reverse Repo Rate",
        "option_b": "Standing Deposit Facility (SDF) Rate",
        "option_c": "Bank Rate",
        "option_d": "Repo Rate",
        "correct_option": "B",
        "explanation": "SDF replaced reverse repo as the LAF floor in April 2022. Collateral-free — banks park surplus with RBI without pledging G-secs. SDF = Repo − 25 bps.",
        "is_trap": 1,
    },
    {
        "bucket": "rbi_instruments",
        "id": "t2_ri_002",
        "question": "The Marginal Standing Facility (MSF) rate is fixed at:",
        "option_a": "Repo − 25 bps",
        "option_b": "Repo + 50 bps",
        "option_c": "Repo + 25 bps",
        "option_d": "Equal to Bank Rate",
        "correct_option": "C",
        "explanation": "MSF is the LAF corridor ceiling at Repo + 25 bps. Emergency overnight window; banks can dip into up to 3% of NDTL from their SLR portfolio.",
        "is_trap": 0,
    },
    {
        "bucket": "rbi_instruments",
        "id": "t2_ri_003",
        "question": "Both CRR and SLR are computed as a percentage of:",
        "option_a": "Total Assets",
        "option_b": "Risk-Weighted Assets",
        "option_c": "Gross Advances",
        "option_d": "Net Demand and Time Liabilities (NDTL)",
        "correct_option": "D",
        "explanation": "NDTL = demand liabilities + time liabilities − inter-bank liabilities. Both CRR and SLR use NDTL as the base for computation.",
        "is_trap": 0,
    },
    {
        "bucket": "rbi_instruments",
        "id": "t2_ri_004",
        "question": "When RBI conducts OMO by buying G-secs from banks, the primary effect is:",
        "option_a": "Liquidity absorption from the system",
        "option_b": "Liquidity injection into the system",
        "option_c": "Increase in SLR requirement",
        "option_d": "Reduction in repo rate",
        "correct_option": "B",
        "explanation": "OMO Purchase → RBI pays banks → money enters system (injection). OMO Sale → RBI sells G-secs → absorbs liquidity. Used for durable liquidity management.",
        "is_trap": 0,
    },
    {
        "bucket": "rbi_instruments",
        "id": "t2_ri_005",
        "question": "The LAF corridor is bounded by:",
        "option_a": "Reverse Repo Rate and MSF Rate",
        "option_b": "SDF Rate and MSF Rate",
        "option_c": "Repo Rate and Bank Rate",
        "option_d": "CRR floor and SLR ceiling",
        "correct_option": "B",
        "explanation": "Post-April 2022: SDF (floor, Repo−25bps) ↔ Repo (policy rate) ↔ MSF (ceiling, Repo+25bps). Symmetric ±25 bps = 50 bps total corridor width.",
        "is_trap": 1,
    },
    {
        "bucket": "rbi_instruments",
        "id": "t2_ri_006",
        "question": "Variable Rate Reverse Repo (VRRR) auctions are primarily used by RBI to:",
        "option_a": "Inject durable liquidity at a fixed rate",
        "option_b": "Absorb excess surplus liquidity from banks",
        "option_c": "Signal a reduction in repo rate",
        "option_d": "Regulate NBFC borrowings",
        "correct_option": "B",
        "explanation": "VRRR is a market-based absorption tool. Banks bid at market-determined rates, letting RBI drain surplus liquidity in a calibrated manner, complementing the SDF.",
        "is_trap": 0,
    },
    # banking_norms
    {
        "bucket": "banking_norms",
        "id": "t2_bn_001",
        "question": "A loan account is classified as NPA if interest or installment remains overdue for more than:",
        "option_a": "30 days",
        "option_b": "60 days",
        "option_c": "90 days",
        "option_d": "180 days",
        "correct_option": "C",
        "explanation": "90-day NPA norm: unpaid interest/principal for 90 days → Sub-Standard asset. Applies to term loans and OD/CC accounts (90 days continuously out of order).",
        "is_trap": 0,
    },
    {
        "bucket": "banking_norms",
        "id": "t2_bn_002",
        "question": "Under Basel III as implemented by RBI, the minimum CRAR for commercial banks is:",
        "option_a": "8%",
        "option_b": "9%",
        "option_c": "10%",
        "option_d": "11.5%",
        "correct_option": "B",
        "explanation": "Basel III global minimum = 8%. RBI mandates 9% for Indian banks. Including Capital Conservation Buffer (CCB = 2.5%), effective minimum CRAR = 11.5%.",
        "is_trap": 1,
    },
    {
        "bucket": "banking_norms",
        "id": "t2_bn_003",
        "question": "'Stressed assets' in the Indian banking system refers to:",
        "option_a": "NPAs alone",
        "option_b": "Restructured standard assets alone",
        "option_c": "NPAs + Restructured Standard Assets",
        "option_d": "Doubtful assets only",
        "correct_option": "C",
        "explanation": "Stressed assets = Gross NPAs + Restructured Standard Assets. Captures the full extent of asset quality problems including restructured loans that avoided NPA classification.",
        "is_trap": 0,
    },
    {
        "bucket": "banking_norms",
        "id": "t2_bn_004",
        "question": "Under IBC 2016, the maximum duration of the Corporate Insolvency Resolution Process (CIRP) is:",
        "option_a": "90 days",
        "option_b": "180 days",
        "option_c": "270 days",
        "option_d": "365 days",
        "correct_option": "C",
        "explanation": "CIRP: 180 days initial + 90 days NCLT-approved extension = 270 days max. Time-bound to prevent value erosion. Resolution plan voted by Committee of Creditors.",
        "is_trap": 0,
    },
    {
        "bucket": "banking_norms",
        "id": "t2_bn_005",
        "question": "One of the triggers for RBI's Prompt Corrective Action (PCA) framework is:",
        "option_a": "CRAR falls below 12%",
        "option_b": "Net NPA ratio exceeds 6%",
        "option_c": "Credit growth exceeds 20% YoY",
        "option_d": "ROE falls below 8%",
        "correct_option": "B",
        "explanation": "PCA triggers: Net NPA > 6% OR CRAR below threshold OR ROA < 0 for 2 consecutive years. Any one trigger invokes PCA restrictions. ROE is not a PCA trigger.",
        "is_trap": 0,
    },
    {
        "bucket": "banking_norms",
        "id": "t2_bn_006",
        "question": "The NPA classification progresses as: Sub-Standard → Doubtful → Loss. A loan moves from Sub-Standard to Doubtful after:",
        "option_a": "6 months as Sub-Standard",
        "option_b": "12 months as Sub-Standard",
        "option_c": "18 months as Sub-Standard",
        "option_d": "24 months as Sub-Standard",
        "correct_option": "B",
        "explanation": "Sub-Standard = NPA for < 12 months. After 12 months as Sub-Standard → Doubtful. After 36 months as Doubtful (or if deemed unrecoverable) → Loss asset.",
        "is_trap": 0,
    },
    # payment_systems
    {
        "bucket": "payment_systems",
        "id": "t2_ps_001",
        "question": "RTGS and NEFT are operated by:",
        "option_a": "NPCI",
        "option_b": "RBI",
        "option_c": "Ministry of Finance",
        "option_d": "SBI as the lead bank",
        "correct_option": "B",
        "explanation": "RTGS (Real Time Gross Settlement) and NEFT (National Electronic Funds Transfer) are operated by RBI. UPI, IMPS, RuPay, NACH, FASTag are operated by NPCI.",
        "is_trap": 1,
    },
    {
        "bucket": "payment_systems",
        "id": "t2_ps_002",
        "question": "The Digital Rupee (e₹) introduced by RBI is best described as:",
        "option_a": "A cryptocurrency similar to Bitcoin",
        "option_b": "A Central Bank Digital Currency (CBDC) that is legal tender",
        "option_c": "A stablecoin pegged to the US dollar",
        "option_d": "A digital voucher for targeted subsidy delivery",
        "correct_option": "B",
        "explanation": "e₹ = CBDC issued by RBI. Legal tender. Not a cryptocurrency (decentralised). Not e-RUPI (which is a purpose/person-specific digital voucher). Retail pilot Nov 2022.",
        "is_trap": 1,
    },
    {
        "bucket": "payment_systems",
        "id": "t2_ps_003",
        "question": "NEFT operates on which settlement mechanism?",
        "option_a": "Real-time gross settlement",
        "option_b": "Deferred net settlement in half-hourly batches",
        "option_c": "Immediate mobile payment settlement",
        "option_d": "Daily end-of-day net settlement",
        "correct_option": "B",
        "explanation": "NEFT = Deferred Net Settlement (DNS) in 48 half-hourly batches, 24×7 since Dec 2019. RTGS = Real-time gross settlement for large-value (≥₹2 lakh). IMPS = immediate mobile.",
        "is_trap": 0,
    },
    {
        "bucket": "payment_systems",
        "id": "t2_ps_004",
        "question": "e-RUPI is best described as:",
        "option_a": "India's Central Bank Digital Currency",
        "option_b": "A person-and-purpose-specific prepaid digital voucher",
        "option_c": "A UPI-based payment gateway",
        "option_d": "A CBDC for wholesale interbank settlements",
        "correct_option": "B",
        "explanation": "e-RUPI = prepaid e-voucher (not CBDC). Person-specific + purpose-specific (e.g., health/education). Developed by NPCI. Used for targeted DBT — beneficiary can only use it for the designated purpose.",
        "is_trap": 1,
    },
    {
        "bucket": "payment_systems",
        "id": "t2_ps_005",
        "question": "The minimum transaction amount for RTGS is:",
        "option_a": "₹50,000",
        "option_b": "₹1 lakh",
        "option_c": "₹2 lakh",
        "option_d": "No minimum",
        "correct_option": "C",
        "explanation": "RTGS minimum = ₹2 lakh. No upper limit. NEFT has no minimum. RTGS is designed for large-value, time-critical transactions with immediate settlement.",
        "is_trap": 0,
    },
    {
        "bucket": "payment_systems",
        "id": "t2_ps_006",
        "question": "NACH (National Automated Clearing House) primarily handles:",
        "option_a": "Real-time individual fund transfers above ₹2 lakh",
        "option_b": "Bulk recurring transactions like salary, pension, EMI",
        "option_c": "International remittances via SWIFT",
        "option_d": "Interbank forex settlement",
        "correct_option": "B",
        "explanation": "NACH = operated by NPCI. Replaced ECS. Handles bulk credit/debit mandates: salary disbursement, pension, EMI collection, utility bills. Not for real-time or individual transfers.",
        "is_trap": 0,
    },
    # fin_inclusion
    {
        "bucket": "fin_inclusion",
        "id": "t2_fi_001",
        "question": "The PSL (Priority Sector Lending) target for domestic Scheduled Commercial Banks is:",
        "option_a": "32% of ANBC",
        "option_b": "36% of ANBC",
        "option_c": "40% of ANBC",
        "option_d": "45% of ANBC",
        "correct_option": "C",
        "explanation": "PSL total = 40% of Adjusted Net Bank Credit (ANBC). Sub-targets: Agriculture 18% (incl. 10% to Small & Marginal Farmers), Micro enterprises 7.5%, Weaker sections 12%.",
        "is_trap": 0,
    },
    {
        "bucket": "fin_inclusion",
        "id": "t2_fi_002",
        "question": "The RBI Financial Inclusion Index (FI-Index) has three dimensions. Which has the highest weight?",
        "option_a": "Access (35%)",
        "option_b": "Usage (45%)",
        "option_c": "Quality (20%)",
        "option_d": "All three have equal weights (33.3% each)",
        "correct_option": "B",
        "explanation": "FI-Index = composite of Access (35%), Usage (45%), Quality (20%). Usage has the highest weight because mere access without actual use of financial services does not indicate inclusion. Published annually in July.",
        "is_trap": 1,
    },
    {
        "bucket": "fin_inclusion",
        "id": "t2_fi_003",
        "question": "PMJDY (Pradhan Mantri Jan Dhan Yojana) accounts offer an overdraft facility of up to:",
        "option_a": "₹5,000",
        "option_b": "₹10,000",
        "option_c": "₹15,000",
        "option_d": "₹25,000",
        "correct_option": "B",
        "explanation": "PMJDY zero-balance accounts include: ₹10,000 OD facility, RuPay debit card, ₹2 lakh accidental insurance. ~56 crore beneficiaries. Linked to Aadhaar for DBT.",
        "is_trap": 0,
    },
    {
        "bucket": "fin_inclusion",
        "id": "t2_fi_004",
        "question": "Under MUDRA (PMMY), 'Kishor' loans cover the range:",
        "option_a": "Up to ₹50,000",
        "option_b": "₹50,001 to ₹5 lakh",
        "option_c": "₹5 lakh to ₹10 lakh",
        "option_d": "Above ₹10 lakh",
        "correct_option": "B",
        "explanation": "MUDRA three categories: Shishu (up to ₹50,000), Kishor (₹50,001–₹5 lakh), Tarun (₹5 lakh–₹10 lakh). Kishor loans grew from 5.9% to 44.7% of total disbursements (FY16 to FY25).",
        "is_trap": 0,
    },
    {
        "bucket": "fin_inclusion",
        "id": "t2_fi_005",
        "question": "The sub-target for Micro Enterprises under PSL for domestic SCBs is:",
        "option_a": "5% of ANBC",
        "option_b": "7.5% of ANBC",
        "option_c": "10% of ANBC",
        "option_d": "12% of ANBC",
        "correct_option": "B",
        "explanation": "Micro Enterprises sub-target = 7.5% of ANBC. Agriculture = 18% (of which 10% to Small & Marginal Farmers). Weaker sections = 12%. Total PSL = 40%.",
        "is_trap": 0,
    },
    {
        "bucket": "fin_inclusion",
        "id": "t2_fi_006",
        "question": "India's LFPR (Labour Force Participation Rate) as per the 2024 PLFS is approximately:",
        "option_a": "45.2%",
        "option_b": "52.3%",
        "option_c": "59.6%",
        "option_d": "67.1%",
        "correct_option": "C",
        "explanation": "PLFS 2024: LFPR = 59.6%. Unemployment rate = 4.9% (Dec 2025). PLFS revamped from Jan 2024. Conducted by MoSPI. Measures participation in labour force (employed + seeking work).",
        "is_trap": 0,
        "is_recent_dev": 1,
    },
    # fiscal_budget
    {
        "bucket": "fiscal_budget",
        "id": "t2_fb_001",
        "question": "The Gross Fiscal Deficit (GFD) target for FY 2026-27 (Budget Estimate) is:",
        "option_a": "3.5% of GDP",
        "option_b": "4.0% of GDP",
        "option_c": "4.3% of GDP",
        "option_d": "4.9% of GDP",
        "correct_option": "C",
        "explanation": "FY26-27 BE: GFD = 4.3% of GDP (₹16,95,768 crore). Down from 4.4% (FY25-26 RE) and 4.8% (FY24-25 actual). Govt targeting debt/GDP ≤ 50% ± 1% by 2031.",
        "is_trap": 0,
        "is_recent_dev": 1,
    },
    {
        "bucket": "fiscal_budget",
        "id": "t2_fb_002",
        "question": "The formula for Gross Fiscal Deficit is:",
        "option_a": "Revenue Expenditure − Revenue Receipts",
        "option_b": "Total Expenditure − Revenue Receipts − Non-debt Capital Receipts",
        "option_c": "Total Expenditure − Total Receipts + Borrowings",
        "option_d": "Capital Expenditure − Capital Receipts",
        "correct_option": "B",
        "explanation": "GFD = Total Expenditure − Revenue Receipts − Non-debt Capital Receipts. Non-debt capital receipts include disinvestment proceeds (not borrowings). GFD = total borrowing requirement of the government.",
        "is_trap": 1,
    },
    {
        "bucket": "fiscal_budget",
        "id": "t2_fb_003",
        "question": "The Primary Deficit differs from GFD because it:",
        "option_a": "Excludes capital expenditure",
        "option_b": "Excludes interest payments on past debt",
        "option_c": "Includes only central government borrowings",
        "option_d": "Equals GFD minus revenue deficit",
        "correct_option": "B",
        "explanation": "Primary Deficit = GFD − Interest Payments. It shows borrowing excluding the burden of past debt. A zero primary deficit means current spending is covered by revenue — only historical debt interest remains unfunded.",
        "is_trap": 0,
    },
    {
        "bucket": "fiscal_budget",
        "id": "t2_fb_004",
        "question": "Capital Expenditure (Capex) in Union Budget 2026-27 is approximately:",
        "option_a": "₹8.5 lakh crore",
        "option_b": "₹10.5 lakh crore",
        "option_c": "₹12.2 lakh crore",
        "option_d": "₹14.1 lakh crore",
        "correct_option": "C",
        "explanation": "Capex FY26-27 BE = ₹12.21 lakh crore (+11.5% over RE). Highest ever. Share of capex in total expenditure: 22.1% (FY25). Effective capex including grants to states = ₹17.1 lakh crore.",
        "is_trap": 0,
        "is_recent_dev": 1,
    },
    {
        "bucket": "fiscal_budget",
        "id": "t2_fb_005",
        "question": "The 16th Finance Commission recommended vertical devolution to states at:",
        "option_a": "39% of the divisible pool",
        "option_b": "40% of the divisible pool",
        "option_c": "41% of the divisible pool",
        "option_d": "43% of the divisible pool",
        "correct_option": "C",
        "explanation": "16th FC (Chair: Dr Arvind Panagariya) recommended 41% — same as 15th FC. The 15th FC had reduced it from 42% (14th FC) due to creation of J&K and Ladakh as UTs. Report tabled Feb 1, 2026.",
        "is_trap": 1,
        "is_recent_dev": 1,
    },
    {
        "bucket": "fiscal_budget",
        "id": "t2_fb_006",
        "question": "Ricardian Equivalence proposition states that:",
        "option_a": "A tax cut increases private consumption because households feel richer",
        "option_b": "Debt-financed and tax-financed government spending have the same effect on aggregate demand",
        "option_c": "Government borrowing always crowds out private investment via higher interest rates",
        "option_d": "Wagner's Law and Keynesian multiplier are equivalent in the long run",
        "correct_option": "B",
        "explanation": "Ricardian Equivalence (Barro): rational agents anticipate future tax increases to repay current debt, so they save the tax cut today. Debt-financed spending = tax-financed spending in effect on AD. Requires: rational agents, perfect capital markets, no liquidity constraints — very strong assumptions often violated in practice.",
        "is_trap": 1,
    },
    # india_economy
    {
        "bucket": "india_economy",
        "id": "t2_ie_001",
        "question": "India's real GDP growth rate in FY 2025-26 (2nd Advance Estimate, base year 2022-23) is approximately:",
        "option_a": "6.4%",
        "option_b": "7.0%",
        "option_c": "7.6%",
        "option_d": "8.2%",
        "correct_option": "C",
        "explanation": "FY26 GDP growth = 7.6% (2nd Advance Estimate, new base year 2022-23). FY25 = 7.1%. FY27 projection = 6.8–7.2% (Economic Survey). GDP base year revised from 2011-12 to 2022-23 in FY26.",
        "is_trap": 0,
        "is_recent_dev": 1,
    },
    {
        "bucket": "india_economy",
        "id": "t2_ie_002",
        "question": "India's Gross NPA ratio as of September 2025 is approximately:",
        "option_a": "4.6%",
        "option_b": "3.1%",
        "option_c": "2.2%",
        "option_d": "1.5%",
        "correct_option": "C",
        "explanation": "GNPA ratio = 2.2% (Sep 2025) — multi-decade low. Peak was 11.2% (March 2018). Slippage ratio = 0.7%. Reflects IBC-driven resolution, improved credit discipline. Bank credit growth ≈ 11.4% YoY (Nov 2025).",
        "is_trap": 0,
        "is_recent_dev": 1,
    },
    {
        "bucket": "india_economy",
        "id": "t2_ie_003",
        "question": "India's GDP base year was recently revised to:",
        "option_a": "2004-05",
        "option_b": "2011-12",
        "option_c": "2017-18",
        "option_d": "2022-23",
        "correct_option": "D",
        "explanation": "MoSPI revised GDP base year to 2022-23 in FY26 (from 2011-12, which had replaced 2004-05). New base year growth rates may differ from earlier estimates. This also revised the CPI base year.",
        "is_trap": 1,
        "is_recent_dev": 1,
    },
    {
        "bucket": "india_economy",
        "id": "t2_ie_004",
        "question": "India's RBI surplus transfer to the Government in FY 2024-25 was:",
        "option_a": "₹87,416 crore",
        "option_b": "₹1.41 lakh crore",
        "option_c": "₹2.11 lakh crore",
        "option_d": "₹2.68 lakh crore",
        "correct_option": "D",
        "explanation": "RBI surplus transfer FY25 = ₹2.68 lakh crore — record transfer, 27% higher than FY24. Under the revised Economic Capital Framework (ECF, reviewed 2025). This is distinct from RBI dividend — it's the surplus after maintaining contingency and revaluation reserves.",
        "is_trap": 0,
        "is_recent_dev": 1,
    },
    {
        "bucket": "india_economy",
        "id": "t2_ie_005",
        "question": "Which index is published annually by RBI in July to measure access, usage, and quality of financial services?",
        "option_a": "Financial Soundness Indicator (FSI)",
        "option_b": "Composite Financial Inclusion Index (FI-Index)",
        "option_c": "Credit Depth Index (CDI)",
        "option_d": "NITI Aayog Multidimensional Poverty Index (MPI)",
        "correct_option": "B",
        "explanation": "RBI FI-Index: composite of Access (35%), Usage (45%), Quality (20%). Scale 0–100. FI-Index = 67 in 2025 (↑ 24.3% since 2021). Published every July. Not the same as the NITI Aayog MPI which measures poverty.",
        "is_trap": 0,
        "is_recent_dev": 1,
    },
    {
        "bucket": "india_economy",
        "id": "t2_ie_006",
        "question": "India's headline CPI inflation (April–December FY26 average) was approximately:",
        "option_a": "5.8%",
        "option_b": "4.2%",
        "option_c": "2.9%",
        "option_d": "1.7%",
        "correct_option": "D",
        "explanation": "Headline CPI FY26 (Apr–Dec): ~1.7%, driven by sharp food disinflation. Core CPI = 4.3% (2.9% excluding gold/silver). MPC targets 4% ±2% under FITF. This sharp fall enabled MPC's rate cut cycle (cumulative 125 bps since Feb 2025).",
        "is_trap": 0,
        "is_recent_dev": 1,
    },
]


def seed_into(conn) -> None:
    existing = {row[0] for row in conn.execute("SELECT id FROM rbi_questions").fetchall()}
    for q in QUESTIONS:
        if q["id"] in existing:
            continue
        subject, topic = BUCKET_META[q["bucket"]]
        conn.execute("""
            INSERT INTO rbi_questions
            (id, question, option_a, option_b, option_c, option_d,
             correct_option, explanation, subject, topic, subtopic,
             dimension, tier, difficulty, is_core_concept, is_recent_dev,
             is_trap, question_type, tags)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,2,'medium',0,?,?,?,?)
        """, (
            q["id"], q["question"], q["option_a"], q["option_b"],
            q["option_c"], q["option_d"], q["correct_option"],
            q["explanation"], subject, topic, "",
            "trap" if q.get("is_trap") else "definition",
            int(q.get("is_recent_dev", 0)),
            int(q.get("is_trap", 0)),
            "standard",
            json.dumps(["tier2", subject, topic]),
        ))
    conn.commit()


def migrate():
    conn = sqlite3.connect(DB_PATH)

    # Check existing
    existing = {row[0] for row in conn.execute("SELECT id FROM rbi_questions").fetchall()}

    inserted = 0
    for q in QUESTIONS:
        if q["id"] in existing:
            continue
        subject, topic = BUCKET_META[q["bucket"]]
        conn.execute("""
            INSERT INTO rbi_questions
            (id, question, option_a, option_b, option_c, option_d,
             correct_option, explanation, subject, topic, subtopic,
             dimension, tier, difficulty, is_core_concept, is_recent_dev,
             is_trap, question_type, tags)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,2,'medium',0,?,?,?,?)
        """, (
            q["id"], q["question"], q["option_a"], q["option_b"],
            q["option_c"], q["option_d"], q["correct_option"],
            q["explanation"], subject, topic, "",
            "trap" if q.get("is_trap") else "definition",
            int(q.get("is_recent_dev", 0)),
            int(q.get("is_trap", 0)),
            "standard",
            json.dumps(["tier2", subject, topic]),
        ))
        inserted += 1

    # Seed mastery rows for newly inserted topics
    topics = conn.execute(
        "SELECT DISTINCT topic, subject FROM rbi_questions WHERE tier=2"
    ).fetchall()
    for topic, subject in topics:
        conn.execute("""
            INSERT OR IGNORE INTO rbi_topic_mastery (user_id, topic, subject)
            VALUES ('rahul', ?, ?)
        """, (topic, subject))

    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM rbi_questions").fetchone()[0]
    conn.close()
    print(f"Migrated {inserted} Tier 2 questions. Total in DB: {total}")


if __name__ == "__main__":
    migrate()
