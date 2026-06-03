"""RBI DEPR 2026 Prep — Key Data · Phase 1 Drill · Tier 2 Quiz · Progress."""
import json
import logging
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from db import get_user_id, log_event
from styles import apply_theme

st.set_page_config(page_title="RBI Prep · DEPR 2026", layout="wide", page_icon="🏦")
apply_theme()

RBI_DATE = "2026-06-14"
RBI_DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"


def days_to_rbi() -> int:
    return (datetime.strptime(RBI_DATE, "%Y-%m-%d").date() - datetime.today().date()).days


# ── DB connection (single cached resource — avoids connection leak) ─────────────

@st.cache_resource
def get_rbi_conn() -> Optional[sqlite3.Connection]:
    if not RBI_DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(RBI_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ── DB query helpers ───────────────────────────────────────────────────────────

def _answered_ids(conn: sqlite3.Connection) -> set:
    user_id = get_user_id()
    rows = conn.execute(
        "SELECT DISTINCT question_id FROM rbi_attempts WHERE user_id=?", (user_id,)
    ).fetchall()
    return {r[0] for r in rows}


def get_smart_questions(conn: sqlite3.Connection, n: int = 10) -> list:
    """Layer 1: highest flag_impact topics → unanswered questions first."""
    user_id = get_user_id()
    answered = _answered_ids(conn)
    rows = conn.execute("""
        SELECT q.id, q.question, q.option_a, q.option_b, q.option_c, q.option_d,
               q.correct_option, q.explanation, q.topic, q.subject, q.difficulty,
               q.is_trap, q.priority_weight,
               COALESCE(m.flag_impact, tw.base_weight, 0.05) AS topic_priority
        FROM rbi_questions q
        LEFT JOIN rbi_topic_mastery m ON q.topic = m.topic AND m.user_id = ?
        LEFT JOIN rbi_topic_weights tw ON q.topic = tw.topic
        WHERE q.tier = 1
        ORDER BY topic_priority DESC, q.priority_weight DESC
    """, (user_id,)).fetchall()

    unanswered = [dict(r) for r in rows if r["id"] not in answered]
    seen_answered = [dict(r) for r in rows if r["id"] in answered]
    result = unanswered[:n]
    if len(result) < n:
        result += seen_answered[:n - len(result)]
    return result


def get_filtered_questions(conn: sqlite3.Connection, filters: dict, n: int = 10) -> list:
    """Layer 3: user-directed filter override."""
    clauses = ["tier = 1"]
    params: list = []
    if filters.get("subject") and filters["subject"] != "all":
        clauses.append("subject = ?")
        params.append(filters["subject"])
    if filters.get("topic") and filters["topic"] != "all":
        clauses.append("topic = ?")
        params.append(filters["topic"])
    if filters.get("difficulty") and filters["difficulty"] != "all":
        clauses.append("difficulty = ?")
        params.append(filters["difficulty"])
    if filters.get("is_trap"):
        clauses.append("is_trap = 1")
    if filters.get("is_recent"):
        clauses.append("is_recent_dev = 1")

    where = " AND ".join(clauses)
    rows = conn.execute(
        f"SELECT id, question, option_a, option_b, option_c, option_d, "
        f"correct_option, explanation, topic, subject, difficulty, is_trap "
        f"FROM rbi_questions WHERE {where} "
        f"ORDER BY priority_weight DESC LIMIT ?",
        (*params, n),
    ).fetchall()
    return [dict(r) for r in rows]


def save_attempt(conn: sqlite3.Connection, question_id: str, answer_given: str,
                 is_correct: bool, session_id: str, topic: str, subject: str) -> None:
    """Save attempt + update mastery. Uses transaction; toasts on error."""
    user_id = get_user_id()
    try:
        with conn:
            conn.execute(
                "INSERT INTO rbi_attempts (user_id, question_id, answer_given, is_correct, session_id) "
                "VALUES (?,?,?,?,?)",
                (user_id, question_id, answer_given, int(is_correct), session_id),
            )
            _update_mastery(conn, topic, subject, is_correct)
        log_event(conn, "drill_attempt", entity_type="rbi_topic", entity_id=topic,
                  exam_id="rbi_depr_2026",
                  payload={"is_correct": int(is_correct), "question_id": question_id, "session_id": session_id})
    except Exception as exc:
        logging.exception("rbi_attempts insert failed: %s", exc)
        st.toast(f"Could not save attempt: {exc}", icon="⚠")


def _update_mastery(conn: sqlite3.Connection, topic: str, subject: str, is_correct: bool) -> None:
    """INSERT OR REPLACE mastery row — correctly handles both first and subsequent attempts."""
    user_id = get_user_id()
    existing = conn.execute(
        "SELECT attempts, correct FROM rbi_topic_mastery WHERE user_id=? AND topic=?",
        (user_id, topic),
    ).fetchone()

    new_attempts = (existing["attempts"] if existing else 0) + 1
    new_correct = (existing["correct"] if existing else 0) + (1 if is_correct else 0)
    mastery = new_correct / new_attempts

    total_q = conn.execute(
        "SELECT COUNT(*) FROM rbi_questions WHERE topic=?", (topic,)
    ).fetchone()[0] or 1
    attempted_q = conn.execute(
        "SELECT COUNT(DISTINCT question_id) FROM rbi_attempts "
        "WHERE user_id=? AND question_id IN (SELECT id FROM rbi_questions WHERE topic=?)",
        (user_id, topic),
    ).fetchone()[0]

    coverage = attempted_q / total_q
    bw_row = conn.execute("SELECT base_weight FROM rbi_topic_weights WHERE topic=?", (topic,)).fetchone()
    bw = bw_row[0] if bw_row else 0.05
    flag_impact = bw * (1.0 - coverage)
    gap_state = "VERIFIED" if mastery >= 0.75 else "FLAGGED" if mastery < 0.45 else "IN_STUDY"

    conn.execute("""
        INSERT OR REPLACE INTO rbi_topic_mastery
        (user_id, topic, subject, attempts, correct, mastery_score, coverage_pct, flag_impact, gap_state, last_updated)
        VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))
    """, (user_id, topic, subject, new_attempts, new_correct, mastery, coverage, flag_impact, gap_state))


def get_progress_data(conn: sqlite3.Connection) -> dict:
    """Compute formula readiness, true readiness, and top gaps."""
    user_id = get_user_id()
    weights = {r["topic"]: r["base_weight"]
               for r in conn.execute("SELECT topic, base_weight FROM rbi_topic_weights").fetchall()}

    mastery_rows = conn.execute(
        "SELECT topic, subject, attempts, mastery_score, coverage_pct, flag_impact, gap_state "
        "FROM rbi_topic_mastery WHERE user_id=?", (user_id,)
    ).fetchall()

    total_weight = sum(weights.values()) or 1.0
    formula_score = 0.0
    true_penalty = 0.0
    gaps = []

    mastery_map = {r["topic"]: dict(r) for r in mastery_rows}

    for topic, bw in weights.items():
        m = mastery_map.get(topic)
        coverage = m["coverage_pct"] if m else 0.0
        mastery = m["mastery_score"] if m else 0.0

        formula_score += mastery * bw
        if coverage < 0.5:
            true_penalty += bw * (0.5 - coverage)
            gaps.append({
                "topic": topic,
                "subject": m["subject"] if m else "",
                "coverage_pct": coverage,
                "flag_impact": bw * (1.0 - coverage),
            })

    formula_score = formula_score / total_weight
    true_readiness = max(0.0, formula_score - true_penalty / total_weight)
    gaps.sort(key=lambda g: g["flag_impact"], reverse=True)

    by_subject: dict = {}
    for topic, bw in weights.items():
        m = mastery_map.get(topic)
        subj_row = conn.execute("SELECT subject FROM rbi_topic_weights WHERE topic=?", (topic,)).fetchone()
        subj = subj_row[0] if subj_row else "other"
        if subj not in by_subject:
            by_subject[subj] = {"weight": 0.0, "weighted_cov": 0.0, "attempts": 0}
        cov = m["coverage_pct"] if m else 0.0
        att = m["attempts"] if m else 0
        by_subject[subj]["weight"] += bw
        by_subject[subj]["weighted_cov"] += bw * cov
        by_subject[subj]["attempts"] += att

    subject_coverage = {
        s: d["weighted_cov"] / d["weight"] if d["weight"] > 0 else 0.0
        for s, d in by_subject.items()
    }

    return {
        "formula_score": formula_score,
        "true_readiness": true_readiness,
        "gaps": gaps[:10],
        "subject_coverage": subject_coverage,
        "total_attempts": conn.execute(
            "SELECT COUNT(*) FROM rbi_attempts WHERE user_id=?", (user_id,)
        ).fetchone()[0],
    }


# ── Static data ────────────────────────────────────────────────────────────────

KEY_SECTIONS = [
    {
        "label": "LAF Corridor & Policy Rates",
        "color": "#8AB4F8",
        "items": [
            ("Repo Rate", "5.25%", "MPC Feb 2026 kept unchanged. Cumulative 125 bps cuts since Feb 2025 (from 6.50%). MPC stance: Neutral.", False),
            ("SDF Rate", "5.00% (Repo − 25 bps)", "Standing Deposit Facility (Apr 2022). LAF floor. Banks park surplus with RBI collateral-free. Replaced reverse repo as operative floor.", False),
            ("MSF Rate", "5.50% (Repo + 25 bps)", "Marginal Standing Facility. LAF ceiling. Emergency window — banks use up to 3% of NDTL of SLR portfolio.", False),
            ("Bank Rate", "= MSF Rate", "Rate for long-term advances outside LAF. Used as benchmark for penalty/penal rates.", False),
            ("LAF Corridor width", "±25 bps = 50 bps total", "Symmetric: SDF (floor) ↔ Repo (policy signal) ↔ MSF (ceiling). Post-Apr 2022 structure.", False),
            ("Reverse Repo", "3.35% (de facto superseded by SDF)", "Exists in statute but SDF is the operative floor since Apr 2022. Exam trap: SDF ≠ reverse repo.", False),
        ],
    },
    {
        "label": "Reserve Ratios & PSL",
        "color": "#C084FC",
        "items": [
            ("CRR", "4% of NDTL ⚠ verify", "% of NDTL held as cash with RBI. No interest paid. RBI cut CRR injecting ₹2.5 lakh crore in FY26. Standard level 4%.", True),
            ("SLR", "18% of NDTL ⚠ verify", "% of NDTL held in approved G-secs/gold/cash. Banks borrow under MSF against SLR.", True),
            ("Base for both CRR & SLR", "NDTL (Net Demand and Time Liabilities)", "NDTL = Demand liabilities + Time liabilities − Inter-bank liabilities.", False),
            ("PSL — domestic SCBs", "40% of ANBC", "Priority Sector Lending total. Sub-targets: Agriculture 18% (incl. 10% to SMFs), Micro enterprises 7.5%, Weaker sections 12%.", False),
            ("Agriculture PSL sub-target", "18% of ANBC", "Of which ≥10% must go to Small & Marginal Farmers specifically.", False),
        ],
    },
    {
        "label": "Banking Regulation & Asset Quality",
        "color": "#F28B82",
        "items": [
            ("NPA trigger", "90 days overdue", "Interest/installment unpaid for 90 days → Sub-Standard NPA.", False),
            ("NPA categories", "Sub-standard → Doubtful → Loss", "Sub-standard (<12 months NPA) → Doubtful (12–36 months) → Loss (>3 yrs or unrecoverable).", False),
            ("CRAR minimum (India)", "9% (Basel III global: 8%)", "RBI mandates 9%. With Capital Conservation Buffer (CCB = 2.5%) → effective minimum = 11.5%.", False),
            ("Stressed assets", "Gross NPA + Restructured Standard Assets", "Broader than GNPA. Captures restructured loans that avoided NPA classification.", False),
            ("PCA triggers", "Net NPA > 6%; CRAR below threshold; ROA < 0 for 2 yrs", "Prompt Corrective Action. Any one trigger → restrictions on dividends, lending, branches.", False),
            ("IBC CIRP timeline", "180 days + 90 days extension = 270 days max", "Insolvency & Bankruptcy Code 2016. Time-bound NCLT process to maximise creditor recovery.", False),
        ],
    },
    {
        "label": "Payment Infrastructure",
        "color": "#81C995",
        "items": [
            ("RTGS", "Min ₹2 lakh · Real-time · 24×7 · Operated by RBI", "Real Time Gross Settlement. Individual transaction, instant gross settlement. No upper limit.", False),
            ("NEFT", "No minimum · 48 half-hourly batches · 24×7 · Operated by RBI", "Deferred Net Settlement (DNS). Retail payments. Available 24×7 since Dec 2019.", False),
            ("NPCI operates", "UPI, IMPS, RuPay, NACH, FASTag, AePS, BBPS", "Exam trap: RTGS and NEFT are RBI; UPI/IMPS etc. are NPCI.", False),
            ("e-RUPI", "Digital voucher — NOT CBDC", "Person/purpose-specific prepaid e-voucher for targeted DBT. Developed by NPCI. Aug 2021.", False),
            ("Digital Rupee (e₹)", "CBDC — Central Bank Digital Currency", "Legal tender issued by RBI. Retail pilot Nov 2022, Wholesale Dec 2022. Not a cryptocurrency.", False),
            ("NACH", "Bulk recurring: salary / pension / EMI / utilities", "National Automated Clearing House (NPCI). Replaced ECS. Handles bulk credit and debit mandates.", False),
        ],
    },
    {
        "label": "Fiscal Framework",
        "color": "#FDD663",
        "items": [
            ("GFD formula", "Total Expenditure − Revenue Receipts − Non-debt Capital Receipts", "Gross Fiscal Deficit = total borrowing requirement.", False),
            ("GFD — FY26-27 BE", "4.3% of GDP · Rs 16,95,768 cr", "Down from 4.4% (FY25-26 RE) and 4.8% (FY24-25 actual).", False),
            ("Revenue Deficit — FY26-27 BE", "1.5% of GDP", "Revenue Expenditure − Revenue Receipts.", False),
            ("Primary Deficit — FY26-27 BE", "0.7% of GDP", "GFD − Interest Payments. Declining fast (was 2.5% in FY22).", False),
            ("Capital Expenditure — FY26-27 BE", "Rs 12.21 lakh crore (+11.5% over RE)", "Highest ever. Share in total expenditure: 22.1% (FY25). Effective capex = Rs 17.1 lakh crore.", False),
            ("States' share (16th FC)", "41% (unchanged from 15th FC)", "16th FC Chair: Dr Arvind Panagariya. Report tabled Feb 1, 2026.", False),
            ("FRBM / debt anchor", "GFD ≤ 3% of GDP · Debt anchor: 50% ± 1% by 2031", "Centre currently at 4.3%. 16th FC recommends 3.5% by 2030-31.", False),
            ("Interest payments burden", "26% of total expenditure · 40% of revenue receipts", "Rs 14.04 lakh crore in FY26-27 BE.", False),
        ],
    },
    {
        "label": "Indian Economy — Quick Facts",
        "color": "#9AA0A6",
        "items": [
            ("GDP rank by nominal size", "4th largest globally (surpassed Japan)", "Aspiration: 3rd by early 2030s.", False),
            ("Real GDP growth FY26", "7.6% (2nd Advance Estimate, base 2022-23)", "FY25: 7.1%. FY27 projection: 6.8–7.2% (Economic Survey).", False),
            ("GDP base year", "2022-23 (newly revised from 2011-12)", "MoSPI revised base year in FY26. Earlier base was 2011-12 (from 2004-05).", False),
            ("Headline CPI — FY26 (Apr–Dec)", "1.7% · Core CPI: 4.3% (2.9% excl. gold/silver)", "Sharp disinflation from food prices.", False),
            ("CPI base year", "2024 (newly revised from 2012)", "RBI targets CPI Combined at 4% ± 2% under FITF.", False),
            ("MPC inflation target", "4% ± 2% (2%–6%) · FITF ⚠ verify renewal", "FITF was effective until March 31, 2026. Verify if renewed.", True),
            ("Gross NPA ratio", "2.2% (Sep 2025) — multi-decade low", "Peak was 11.2% (March 2018). Bank credit growth: ~11.4% YoY (Nov 2025).", False),
            ("RBI surplus transfer to Govt", "Rs 2.68 lakh crore (FY25 — record)", "27% higher than FY24 transfer. Under revised ECF (2025 review).", False),
            ("FI-Index (RBI)", "67 in 2025 (↑ 24.3% since 2021)", "Scale 0-100. Access (35%), Usage (45%), Quality (20%). Published annually in July.", False),
        ],
    },
]

BUCKETS = {
    "rbi_instruments": {
        "label": "RBI Instruments & Liquidity", "icon": "⚙",
        "qs": [
            {"id": "ri_1", "q": "Which rate serves as the floor of the LAF corridor as of April 2022?",
             "opts": ["A) Reverse Repo Rate", "B) Standing Deposit Facility (SDF) Rate", "C) Bank Rate", "D) Repo Rate"],
             "correct": "B) Standing Deposit Facility (SDF) Rate",
             "exp": "SDF replaced reverse repo as the LAF floor in April 2022. Collateral-free — banks park surplus with RBI without pledging G-secs. SDF = Repo − 25 bps."},
            {"id": "ri_2", "q": "The Marginal Standing Facility (MSF) rate is fixed at:",
             "opts": ["A) Repo − 25 bps", "B) Repo + 50 bps", "C) Repo + 25 bps", "D) Equal to Bank Rate"],
             "correct": "C) Repo + 25 bps",
             "exp": "MSF is the LAF corridor ceiling at Repo + 25 bps. Emergency overnight window; banks can dip into up to 3% of NDTL from their SLR portfolio."},
            {"id": "ri_3", "q": "Both CRR and SLR are computed as a percentage of:",
             "opts": ["A) Total Assets", "B) Risk-Weighted Assets", "C) Gross Advances", "D) Net Demand and Time Liabilities (NDTL)"],
             "correct": "D) Net Demand and Time Liabilities (NDTL)",
             "exp": "NDTL = demand liabilities + time liabilities − inter-bank liabilities. Both CRR and SLR use NDTL as base."},
            {"id": "ri_4", "q": "When RBI conducts OMO by buying G-secs from banks, the primary effect is:",
             "opts": ["A) Liquidity absorption from the system", "B) Liquidity injection into the system", "C) Increase in SLR requirement", "D) Reduction in repo rate"],
             "correct": "B) Liquidity injection into the system",
             "exp": "OMO Purchase → RBI pays banks → money enters system (injection). OMO Sale → absorbs liquidity. Used for durable liquidity management."},
            {"id": "ri_5", "q": "The LAF corridor is bounded by:",
             "opts": ["A) Reverse Repo Rate and MSF Rate", "B) SDF Rate and MSF Rate", "C) Repo Rate and Bank Rate", "D) CRR floor and SLR ceiling"],
             "correct": "B) SDF Rate and MSF Rate",
             "exp": "Post-April 2022: SDF (floor, Repo−25bps) ↔ Repo ↔ MSF (ceiling, Repo+25bps). Symmetric ±25 bps = 50 bps total corridor width."},
            {"id": "ri_6", "q": "Variable Rate Reverse Repo (VRRR) auctions are primarily used by RBI to:",
             "opts": ["A) Inject durable liquidity at a fixed rate", "B) Absorb excess surplus liquidity from banks", "C) Signal a reduction in repo rate", "D) Regulate NBFC borrowings"],
             "correct": "B) Absorb excess surplus liquidity from banks",
             "exp": "VRRR is a market-based absorption tool. Banks bid at market-determined rates, draining surplus liquidity in a calibrated manner."},
        ],
    },
    "banking_norms": {
        "label": "Banking Regulation & NPA", "icon": "🏛",
        "qs": [
            {"id": "bn_1", "q": "A loan account is classified as NPA if interest or installment remains overdue for more than:",
             "opts": ["A) 30 days", "B) 60 days", "C) 90 days", "D) 180 days"],
             "correct": "C) 90 days",
             "exp": "90-day NPA norm: unpaid interest/principal for 90 days → Sub-Standard asset. Applies to term loans and OD/CC accounts (90 days continuously out of order)."},
            {"id": "bn_2", "q": "Under Basel III as implemented by RBI, the minimum CRAR for commercial banks is:",
             "opts": ["A) 8%", "B) 9%", "C) 10%", "D) 11.5%"],
             "correct": "B) 9%",
             "exp": "Basel III global minimum = 8%. RBI mandates 9%. Including Capital Conservation Buffer (CCB = 2.5%), effective minimum CRAR = 11.5%."},
            {"id": "bn_3", "q": "'Stressed assets' in the Indian banking system refers to:",
             "opts": ["A) NPAs alone", "B) Restructured standard assets alone", "C) NPAs + Restructured Standard Assets", "D) Doubtful assets only"],
             "correct": "C) NPAs + Restructured Standard Assets",
             "exp": "Stressed assets = Gross NPAs + Restructured Standard Assets. Captures restructured loans that avoided NPA classification."},
            {"id": "bn_4", "q": "Under IBC 2016, the maximum duration of the CIRP is:",
             "opts": ["A) 90 days", "B) 180 days", "C) 270 days", "D) 365 days"],
             "correct": "C) 270 days",
             "exp": "CIRP: 180 days initial + 90 days NCLT-approved extension = 270 days max. Time-bound to prevent value erosion."},
            {"id": "bn_5", "q": "One of the triggers for RBI's Prompt Corrective Action (PCA) framework is:",
             "opts": ["A) CRAR falls below 12%", "B) Net NPA ratio exceeds 6%", "C) Credit growth exceeds 20% YoY", "D) ROE falls below 8%"],
             "correct": "B) Net NPA ratio exceeds 6%",
             "exp": "PCA triggers (any one): CRAR below threshold; Net NPA > 6%; ROA negative for 2 consecutive years. ROE is not a trigger."},
            {"id": "bn_6", "q": "Gross NPA Ratio is calculated as:",
             "opts": ["A) Net NPA / Net Advances × 100", "B) Gross NPA / Risk-Weighted Assets × 100", "C) Gross NPA / Gross Advances × 100", "D) Total Provisions / Total Assets × 100"],
             "correct": "C) Gross NPA / Gross Advances × 100",
             "exp": "Gross NPA Ratio = Gross NPAs / Gross Advances × 100. Net NPA Ratio uses Net NPAs (after provisions) over Net Advances."},
        ],
    },
    "payment_systems": {
        "label": "Payment Systems & Infra", "icon": "💳",
        "qs": [
            {"id": "ps_1", "q": "RTGS is designed for:",
             "opts": ["A) Retail transactions below ₹2 lakh", "B) High-value real-time transactions with minimum ₹2 lakh", "C) G-sec auction settlements only", "D) Cross-border SWIFT alternative"],
             "correct": "B) High-value real-time transactions with minimum ₹2 lakh",
             "exp": "RTGS: continuous, individual, real-time gross settlement. Min ₹2 lakh, no upper limit. Available 24×7 since Dec 2020. Operated by RBI."},
            {"id": "ps_2", "q": "Which of the following is operated by RBI, NOT by NPCI?",
             "opts": ["A) IMPS", "B) UPI", "C) NEFT", "D) RuPay"],
             "correct": "C) NEFT",
             "exp": "RBI operates: RTGS and NEFT. NPCI operates: UPI, IMPS, RuPay, NACH, FASTag, AePS, BBPS. Classic exam trap — NEFT looks like an NPCI product but is RBI."},
            {"id": "ps_3", "q": "NEFT uses which settlement mechanism?",
             "opts": ["A) Real-time individual gross settlement", "B) Deferred Net Settlement in half-hourly batches", "C) Daily end-of-day batch netting", "D) Weekly bilateral netting"],
             "correct": "B) Deferred Net Settlement in half-hourly batches",
             "exp": "NEFT = Deferred Net Settlement (DNS), 48 half-hourly batches, 24×7 since Dec 2019. No minimum. Operated by RBI."},
            {"id": "ps_4", "q": "e-RUPI (launched August 2021) is best described as:",
             "opts": ["A) India's retail Central Bank Digital Currency", "B) A UPI-based credit facility for BPL households", "C) A person/purpose-specific digital voucher for targeted benefit delivery", "D) A mobile wallet issued by RBI"],
             "correct": "C) A person/purpose-specific digital voucher for targeted benefit delivery",
             "exp": "e-RUPI: digital prepaid voucher — redeemable only by the intended beneficiary for the specified purpose. By NPCI with DFS/NHA. NOT the CBDC (e₹)."},
            {"id": "ps_5", "q": "The Digital Rupee (e₹) introduced by RBI is classified as:",
             "opts": ["A) A private-sector cryptocurrency backed by gold", "B) A Central Bank Digital Currency (CBDC)", "C) An upgraded UPI with offline capability", "D) A SEBI-regulated stablecoin"],
             "correct": "B) A Central Bank Digital Currency (CBDC)",
             "exp": "e₹ is India's CBDC — legal tender, issued and backed by RBI. Retail pilot Nov 2022; Wholesale Dec 2022. Not decentralised."},
            {"id": "ps_6", "q": "NACH (National Automated Clearing House) is primarily used for:",
             "opts": ["A) Large-value real-time interbank settlement", "B) Bulk recurring transactions like salary, pension, EMI, utility bills", "C) Foreign currency trade settlements", "D) Government securities auctions"],
             "correct": "B) Bulk recurring transactions like salary, pension, EMI, utility bills",
             "exp": "NACH (NPCI) replaced ECS. Handles large-volume, recurring, low-value credit (salary) and debit (EMI mandate) flows."},
        ],
    },
    "financial_inclusion": {
        "label": "Financial Inclusion & PSL", "icon": "🤝",
        "qs": [
            {"id": "fi_1", "q": "A key feature of PMJDY basic savings accounts is:",
             "opts": ["A) Mandatory minimum balance of ₹500", "B) Zero balance with ₹10,000 overdraft facility", "C) No overdraft, ₹50,000 accident insurance only", "D) Fixed deposit linked to Aadhaar only"],
             "correct": "B) Zero balance with ₹10,000 overdraft facility",
             "exp": "PMJDY: zero-balance BSBD account, RuPay card, ₹2 lakh accidental insurance, ₹10,000 OD for Aadhaar-seeded accounts active ≥6 months."},
            {"id": "fi_2", "q": "Under MUDRA Yojana, the 'Shishu' category covers loan amounts:",
             "opts": ["A) Up to ₹50,000", "B) ₹50,001 to ₹5 lakh", "C) ₹5 lakh to ₹10 lakh", "D) Up to ₹1 lakh"],
             "correct": "A) Up to ₹50,000",
             "exp": "MUDRA: Shishu ≤ ₹50,000 | Kishore ₹50,001–₹5 lakh | Tarun ₹5–₹10 lakh. No collateral for Shishu/Kishore."},
            {"id": "fi_3", "q": "The PSL sub-target for agriculture for domestic SCBs is:",
             "opts": ["A) 10% of ANBC", "B) 15% of ANBC", "C) 18% of ANBC", "D) 25% of ANBC"],
             "correct": "C) 18% of ANBC",
             "exp": "Agriculture PSL sub-target = 18% of ANBC, of which ≥10% must go to Small & Marginal Farmers. Total PSL = 40% of ANBC."},
            {"id": "fi_4", "q": "The total PSL target for domestic scheduled commercial banks is:",
             "opts": ["A) 32% of ANBC", "B) 35% of ANBC", "C) 40% of ANBC", "D) 45% of ANBC"],
             "correct": "C) 40% of ANBC",
             "exp": "40% of ANBC for domestic SCBs. Sub-targets: Agriculture 18%, Micro 7.5%, Weaker sections 12%."},
            {"id": "fi_5", "q": "RBI's Financial Inclusion Index (FI-Index) is measured on a scale of:",
             "opts": ["A) 0 to 10", "B) 0 to 100", "C) 0 to 1 (decimal)", "D) 0 to 500"],
             "correct": "B) 0 to 100",
             "exp": "FI-Index: 0 = complete exclusion, 100 = full inclusion. Three dimensions: Access (35), Usage (45), Quality (20). Published annually in July by RBI."},
            {"id": "fi_6", "q": "CGTMSE is jointly established by:",
             "opts": ["A) RBI and SEBI", "B) NABARD and World Bank", "C) Government of India and SIDBI", "D) Ministry of Finance and NPCI"],
             "correct": "C) Government of India and SIDBI",
             "exp": "CGTMSE (est. 2000): collateral-free credit guarantees for MSE loans up to ₹5 crore. Set up by MoMSME (GoI) and SIDBI."},
        ],
    },
    "fiscal_framework": {
        "label": "Budget & Fiscal Framework", "icon": "📋",
        "qs": [
            {"id": "ff_1", "q": "Primary Deficit is defined as:",
             "opts": ["A) Revenue Expenditure minus Revenue Receipts", "B) Gross Fiscal Deficit minus Interest Payments", "C) Capital Expenditure minus Capital Receipts", "D) GFD minus Revenue Deficit"],
             "correct": "B) Gross Fiscal Deficit minus Interest Payments",
             "exp": "Primary Deficit = GFD − Interest Payments. Zero PD means borrowing is solely to service past debt."},
            {"id": "ff_2", "q": "Revenue Deficit is:",
             "opts": ["A) Revenue Receipts minus Revenue Expenditure", "B) Revenue Expenditure minus Revenue Receipts", "C) GFD minus Capital Expenditure", "D) Total Expenditure minus Total Receipts"],
             "correct": "B) Revenue Expenditure minus Revenue Receipts",
             "exp": "Revenue Deficit = Revenue Expenditure − Revenue Receipts. Negative = revenue surplus."},
            {"id": "ff_3", "q": "The Chief Economic Adviser (CEA) is responsible for:",
             "opts": ["A) Presenting the Union Budget in Parliament", "B) Chairing the Monetary Policy Committee", "C) Preparing the Economic Survey", "D) Approving the annual credit policy"],
             "correct": "C) Preparing the Economic Survey",
             "exp": "CEA prepares the Economic Survey. Finance Minister presents the Budget. MPC is chaired by RBI Governor."},
            {"id": "ff_4", "q": "The FRBM Act's medium-term Gross Fiscal Deficit target is:",
             "opts": ["A) 2% of GDP", "B) 2.5% of GDP", "C) 3% of GDP", "D) 4% of GDP"],
             "correct": "C) 3% of GDP",
             "exp": "FRBM Act 2003: medium-term GFD target = 3% of GDP. NK Singh Committee 2017 recommended 2.5% as long-run floor."},
            {"id": "ff_5", "q": "Gross Fiscal Deficit (GFD) equals:",
             "opts": ["A) Revenue Expenditure minus Revenue Receipts", "B) Total Expenditure minus Revenue Receipts minus Non-debt Capital Receipts", "C) Capital Expenditure minus Capital Receipts", "D) Total Expenditure minus Total Receipts"],
             "correct": "B) Total Expenditure minus Revenue Receipts minus Non-debt Capital Receipts",
             "exp": "GFD = Total Expenditure − Revenue Receipts − Non-debt Capital Receipts. Non-debt capital receipts include disinvestment. GFD = total net borrowing requirement."},
            {"id": "ff_6", "q": "The Economic Survey is presented to Parliament:",
             "opts": ["A) On April 1 (first day of fiscal year)", "B) On the last working day of February", "C) The day before the Union Budget", "D) Simultaneously with the Union Budget"],
             "correct": "C) The day before the Union Budget",
             "exp": "Economic Survey is presented the day before the Union Budget. Prepared by CEA's office."},
        ],
    },
    "india_economy": {
        "label": "Indian Economy Structure", "icon": "🇮🇳",
        "qs": [
            {"id": "ie_1", "q": "India is currently the _____ largest economy by nominal GDP:",
             "opts": ["A) 3rd largest", "B) 4th largest", "C) 5th largest", "D) 6th largest"],
             "correct": "B) 4th largest",
             "exp": "India surpassed Japan to become the 4th largest economy by nominal GDP. Target: 3rd by early 2030s. Verify ranking before exam as it may change."},
            {"id": "ie_2", "q": "India's services sector contributes approximately what share of GVA?",
             "opts": ["A) About 30%", "B) About 40%", "C) About 50%", "D) Over 55%"],
             "correct": "D) Over 55%",
             "exp": "Services ~57–60% of GVA. Industry ~26–28%. Agriculture ~15–17%. Despite declining GVA share, agriculture still employs ~45% of the workforce."},
            {"id": "ie_3", "q": "India's GDP base year was most recently revised to:",
             "opts": ["A) 2004-05", "B) 2011-12", "C) 2017-18", "D) 2022-23"],
             "correct": "D) 2022-23",
             "exp": "MoSPI revised the GDP base year to 2022-23 in FY26 (replacing 2011-12, which had replaced 2004-05). Growth rates under the new base may differ from earlier estimates. The CPI base was also simultaneously revised to 2024."},
            {"id": "ie_4", "q": "India's merchandise trade deficit is primarily driven by:",
             "opts": ["A) Software and IT service imports", "B) Oil and gold imports", "C) External debt repayment outflows", "D) Capital goods imports only"],
             "correct": "B) Oil and gold imports",
             "exp": "India's CAD is driven by the merchandise deficit, primarily oil (energy import dependent) and gold (structural demand). Partially offset by services surplus (IT/BPO)."},
            {"id": "ie_5", "q": "Consumer Price Index (CPI) in India is published by:",
             "opts": ["A) RBI", "B) MoSPI (Ministry of Statistics & PI)", "C) Labour Bureau, Ministry of Labour", "D) SEBI"],
             "correct": "B) MoSPI (Ministry of Statistics & PI)",
             "exp": "MoSPI releases monthly CPI (Combined). RBI uses CPI as its inflation target under FIT. Trap: RBI uses CPI but does NOT publish it."},
            {"id": "ie_6", "q": "India's official unemployment rate is measured using which survey?",
             "opts": ["A) Census of India", "B) Economic Census", "C) Annual Survey of Industries (ASI)", "D) PLFS (Periodic Labour Force Survey)"],
             "correct": "D) PLFS (Periodic Labour Force Survey)",
             "exp": "PLFS by MoSPI replaced the NSSO Employment-Unemployment Survey. Provides quarterly LFPR, WPR, UR for urban; annual for rural+urban combined."},
        ],
    },
    "external_sector": {
        "label": "External Sector & BoP", "icon": "🌐",
        "qs": [
            {"id": "es_1", "q": "The Balance of Payments (BoP) is divided into:",
             "opts": ["A) Trade Account and Financial Account",
                      "B) Current Account, Capital Account, and Financial Account",
                      "C) Revenue Account and Capital Account",
                      "D) Merchandise Account and Services Account"],
             "correct": "B) Current Account, Capital Account, and Financial Account",
             "exp": "BoP = Current Account (goods, services, income, transfers) + Capital Account (capital transfers, non-produced asset transactions) + Financial Account (FDI, FPI, ECB, forex reserves). A surplus in one component must be offset by a deficit in another — BoP always balances."},
            {"id": "es_2", "q": "India's Current Account Deficit (CAD) is primarily driven by:",
             "opts": ["A) Services trade deficit",
                      "B) High merchandise deficit led by oil and gold imports",
                      "C) Large outflows of foreign portfolio investment",
                      "D) External commercial borrowing repayments"],
             "correct": "B) High merchandise deficit led by oil and gold imports",
             "exp": "India runs a structural merchandise trade deficit driven by oil (energy import dependence) and gold (strong structural demand). This is partially offset by a services surplus (IT/BPO exports) and remittances. India's services account is actually a surplus — the CAD pressure comes from the goods side."},
            {"id": "es_3", "q": "The Real Effective Exchange Rate (REER) measures:",
             "opts": ["A) The nominal exchange rate of rupee against a single currency (USD)",
                      "B) The bilateral exchange rate adjusted for gold prices",
                      "C) The trade-weighted nominal exchange rate adjusted for relative inflation differentials",
                      "D) The interest rate differential between India and its trading partners"],
             "correct": "C) The trade-weighted nominal exchange rate adjusted for relative inflation differentials",
             "exp": "REER = NEER (trade-weighted nominal rate) adjusted for relative price levels (inflation differentials). REER > 100 implies currency overvaluation vs base year; < 100 implies undervaluation. RBI publishes both 6-currency and 40-currency REER indices. NEER alone ignores competitiveness changes from inflation."},
            {"id": "es_4", "q": "India's foreign exchange reserves are managed by:",
             "opts": ["A) Ministry of Finance through a sovereign wealth fund",
                      "B) SEBI, as they include equity and bond holdings",
                      "C) RBI, under the Foreign Exchange Management Act (FEMA) 1999",
                      "D) EXIM Bank as India's official reserve manager"],
             "correct": "C) RBI, under the Foreign Exchange Management Act (FEMA) 1999",
             "exp": "RBI manages India's forex reserves under FEMA 1999. Reserves comprise: foreign currency assets (largest component, ~90%), gold, SDRs allocated by IMF, and reserve tranche position in IMF. India's reserves stood around $650–690 billion in early 2026, among the top 5 globally."},
            {"id": "es_5", "q": "Foreign Portfolio Investment (FPI) differs from Foreign Direct Investment (FDI) primarily because:",
             "opts": ["A) FPI is regulated by RBI while FDI is regulated by SEBI",
                      "B) FDI involves ownership/management control (≥10% stake); FPI is passive portfolio investment",
                      "C) FPI can only be made in government securities; FDI is in equity only",
                      "D) FDI requires prior government approval; FPI does not in any case"],
             "correct": "B) FDI involves ownership/management control (≥10% stake); FPI is passive portfolio investment",
             "exp": "FDI: ≥10% stake with management control, long-term, in real/unlisted sector. FPI: <10% stake, passive, liquid, in listed securities (equity/debt). Regulation: FDI under DPIIT/FEMA; FPI under SEBI registration. Both notified to RBI. FPI flows are more volatile ('hot money') than FDI."},
            {"id": "es_6", "q": "External Commercial Borrowings (ECB) are regulated by:",
             "opts": ["A) SEBI under the SEBI (FPI) Regulations 2019",
                      "B) Ministry of Finance under the FRBM Act",
                      "C) RBI under FEMA, with specified end-use restrictions and eligible borrower categories",
                      "D) EXIM Bank as part of its trade finance mandate"],
             "correct": "C) RBI under FEMA, with specified end-use restrictions and eligible borrower categories",
             "exp": "ECB = overseas borrowings by eligible Indian entities (corporates, PSUs, NBFCs etc.) in foreign currency. Regulated by RBI under FEMA. Key rules: minimum average maturity period, end-use restrictions (cannot use for real estate investment, equity in India, repayment of rupee loans — in most tracks). Two routes: automatic and approval. Cheap foreign financing but exposes borrower to currency risk."},
        ],
    },
    "nbfc_regulation": {
        "label": "NBFC & Regulatory Framework", "icon": "🏢",
        "qs": [
            {"id": "nr_1", "q": "The defining regulatory distinction between an NBFC and a commercial bank is that an NBFC:",
             "opts": ["A) Cannot accept any form of deposits whatsoever",
                      "B) Cannot accept demand deposits and is not part of the payment & settlement system",
                      "C) Is regulated by SEBI instead of RBI",
                      "D) Can only lend to other NBFCs and microfinance institutions"],
             "correct": "B) Cannot accept demand deposits and is not part of the payment & settlement system",
             "exp": "NBFCs cannot: (1) accept demand deposits (current/savings accounts payable on demand), (2) issue cheques drawn on themselves, (3) access DICGC deposit insurance. Some NBFC categories (NBFC-D) can accept public time deposits (fixed deposits). CRR/SLR norms do not apply to most NBFCs. These three exclusions define the NBFC-bank regulatory difference."},
            {"id": "nr_2", "q": "Under RBI's Scale-Based Regulation (SBR) for NBFCs, the 'Upper Layer' consists of:",
             "opts": ["A) All NBFCs with total assets exceeding ₹10,000 crore",
                      "B) Specifically identified NBFCs by RBI using a scoring methodology — typically top ~10",
                      "C) All deposit-taking NBFCs irrespective of asset size",
                      "D) NBFCs operating in more than 5 states"],
             "correct": "B) Specifically identified NBFCs by RBI using a scoring methodology — typically top ~10",
             "exp": "SBR (effective Oct 2022) layers: Base Layer (small NBFCs, <₹1000 cr ND), Middle Layer (≥₹1000 cr ND + all NBFC-D + IFCs + HFCs etc.), Upper Layer (top ~10 by RBI scoring — near-bank regulation applies: CRAR, large exposure limits), Top Layer (empty by design). Upper Layer ≠ simply the largest — it's scored on size + interconnectedness + complexity."},
            {"id": "nr_3", "q": "Regulation of Housing Finance Companies (HFCs) was transferred from NHB to RBI in:",
             "opts": ["A) 2016 — following demonetisation",
                      "B) 2019 — via the National Housing Bank (Amendment) Act",
                      "C) 2021 — following IL&FS systemic crisis resolution",
                      "D) 2023 — as part of HDFC-HDFC Bank merger regulatory harmonisation"],
             "correct": "B) 2019 — via the National Housing Bank (Amendment) Act",
             "exp": "The NHB (Amendment) Act 2019 transferred HFC registration and regulation to RBI. NHB continues as a refinance institution for housing. The transfer was accelerated by the IL&FS/DHFL crisis (2018-19) that exposed regulatory arbitrage and gaps in NBFC/HFC oversight. HFCs now fall under RBI's SBR framework."},
            {"id": "nr_4", "q": "NBFC-Peer to Peer (P2P) lending platforms are characterised as:",
             "opts": ["A) Banks under the Banking Regulation Act 1949",
                      "B) NBFC intermediaries regulated by RBI — they connect borrowers and lenders but do not lend from their own books",
                      "C) Payment System Operators under the Payment and Settlement Systems Act",
                      "D) Unregulated fintech platforms under Ministry of Corporate Affairs"],
             "correct": "B) NBFC intermediaries regulated by RBI — they connect borrowers and lenders but do not lend from their own books",
             "exp": "P2P platforms classified as NBFC-P2P under RBI's 2017 Master Directions. They are pure intermediaries — cannot use their own funds to lend. Key limits: aggregate lender exposure ≤ ₹50 lakh across all P2P platforms; max loan tenure 36 months; platforms cannot guarantee returns or provide credit enhancement."},
            {"id": "nr_5", "q": "The Account Aggregator (AA) framework in India is primarily designed to:",
             "opts": ["A) Aggregate non-performing assets of banks for centralised RBI resolution",
                      "B) Enable consent-based, encrypted sharing of financial data between regulated entities",
                      "C) Consolidate foreign exchange accounts of NRIs under one RBI portal",
                      "D) Track GST compliance across multiple business entities via GSTN"],
             "correct": "B) Enable consent-based, encrypted sharing of financial data between regulated entities",
             "exp": "AAs are NBFC-AAs regulated by RBI. They act as data intermediaries — enabling consent-based sharing of financial information from Financial Information Providers (FIPs: banks, NBFCs, MFs, insurers) to Financial Information Users (FIUs: lenders, wealth managers). AAs cannot read or store the data — it flows encrypted. Enables instant credit underwriting and digital lending."},
            {"id": "nr_6", "q": "RBI's minimum Net Owned Funds (NOF) requirement for registering a new NBFC (general category) was revised to _____ effective 2021:",
             "opts": ["A) ₹2 crore", "B) ₹5 crore", "C) ₹10 crore", "D) ₹25 crore"],
             "correct": "C) ₹10 crore",
             "exp": "RBI raised the minimum NOF for NBFC registration from ₹2 crore to ₹10 crore in October 2021 (for new registrations). Existing NBFCs with ₹2–₹10 crore NOF were given a glide-path. Intermediary NBFCs like NBFC-AA and NBFC-P2P have separate lower thresholds (₹2 crore). The hike ensures only adequately capitalised entities enter the NBFC space, reducing registration of shell or under-capitalised entities."},
        ],
    },
    "intl_finance": {
        "label": "International Finance & Institutions", "icon": "🏛",
        "qs": [
            {"id": "if_1", "q": "The Bank for International Settlements (BIS), which issues Basel norms through the BCBS, is headquartered in:",
             "opts": ["A) Washington D.C., USA", "B) Geneva, Switzerland", "C) Basel, Switzerland", "D) Frankfurt, Germany"],
             "correct": "C) Basel, Switzerland",
             "exp": "BIS (est. 1930) is headquartered in Basel, Switzerland — which is why global bank capital standards are called 'Basel norms.' It serves as a bank for central banks and hosts the Basel Committee on Banking Supervision (BCBS), which produced Basel I (1988), Basel II (2004), and Basel III (2010 onwards). RBI implements Basel III in India."},
            {"id": "if_2", "q": "The IMF's Special Drawing Rights (SDR) basket currently comprises:",
             "opts": ["A) Gold, USD, EUR, GBP, JPY",
                      "B) USD, EUR, CNY, JPY, GBP",
                      "C) USD, EUR, GBP, CHF, JPY",
                      "D) USD, EUR, CNY, INR, GBP"],
             "correct": "B) USD, EUR, CNY, JPY, GBP",
             "exp": "SDR basket (post-2022 review): USD (~43.4%), EUR (~29.3%), CNY (~12.3%), JPY (~7.6%), GBP (~7.4%). Chinese Yuan (CNY/Renminbi) was added in October 2016. India's rupee is NOT an SDR basket currency. SDRs are not a currency — they are reserve assets allocated to IMF members proportional to quota, usable for exchanging freely usable currencies."},
            {"id": "if_3", "q": "Within the World Bank Group, concessional long-term loans to the world's poorest countries are provided by:",
             "opts": ["A) IBRD (International Bank for Reconstruction & Development)",
                      "B) IFC (International Finance Corporation)",
                      "C) MIGA (Multilateral Investment Guarantee Agency)",
                      "D) IDA (International Development Association)"],
             "correct": "D) IDA (International Development Association)",
             "exp": "IDA provides interest-free or near-zero interest loans and grants to countries with GNI per capita below ~$1,335. IBRD lends to middle-income and creditworthy low-income countries at near-market rates. IFC is the private sector arm (equity + loans). MIGA provides investment guarantees against non-commercial risk. India has graduated from IDA eligibility but was historically a major IDA borrower."},
            {"id": "if_4", "q": "The Financial Stability Board (FSB) was established in response to:",
             "opts": ["A) The 1997 Asian Financial Crisis",
                      "B) The 2001 dot-com bubble burst",
                      "C) The 2007–08 Global Financial Crisis",
                      "D) The 2013 Fed Taper Tantrum"],
             "correct": "C) The 2007–08 Global Financial Crisis",
             "exp": "FSB was established in April 2009 at the G20 London Summit to replace the Financial Stability Forum (FSF, est. 1999 after Asian crisis). FSB monitors global financial vulnerabilities, identifies Global Systemically Important Banks (G-SIBs) and Insurers (G-SIIs), and coordinates regulatory reforms. Headquartered in Basel, secretariat hosted by BIS."},
            {"id": "if_5", "q": "The New Development Bank (NDB), established by BRICS nations in 2014, is headquartered in:",
             "opts": ["A) New Delhi, India", "B) Beijing, China", "C) Shanghai, China", "D) Moscow, Russia"],
             "correct": "C) Shanghai, China",
             "exp": "NDB (Fortaleza Declaration, 2014) is headquartered in Shanghai, China. Authorised capital: $100 billion. India is a founding member and major shareholder. NDB focuses on infrastructure and sustainable development finance in emerging markets and developing countries. New members admitted since 2021: Bangladesh, UAE, Egypt, Uruguay, Ethiopia."},
            {"id": "if_6", "q": "IMF financial assistance is typically conditional on recipient countries agreeing to:",
             "opts": ["A) Pegging their currency to the USD or a currency basket",
                      "B) Structural adjustment / economic reform programs (IMF conditionality)",
                      "C) Transferring a portion of central bank reserves to IMF custody",
                      "D) Achieving a minimum real GDP growth target of 3% per annum"],
             "correct": "B) Structural adjustment / economic reform programs (IMF conditionality)",
             "exp": "IMF conditionality: borrowing countries must implement agreed macroeconomic policies — fiscal consolidation, exchange rate adjustment, structural reforms — in exchange for financial support. This is central to IMF's crisis resolution role. India accessed IMF credit in 1991 BoP crisis, which triggered landmark liberalisation under Narasimha Rao/Manmohan Singh. The 1991 episode is a recurring DEPR exam reference."},
        ],
    },
}

BUCKET_KEYS = list(BUCKETS.keys())
BUCKET_LABELS = [f"{BUCKETS[k]['icon']} {BUCKETS[k]['label']}" for k in BUCKET_KEYS]

# ── Session state — all keys initialised here ──────────────────────────────────
_SS_DEFAULTS: dict = {
    # Tier 2 quiz
    "rbi6_bucket": BUCKET_KEYS[0],
    "rbi6_submitted": False,
    "rbi6_answers": {},
    "rbi6_session": str(uuid.uuid4()),
    "rbi6_scores": {},
    # Phase 1 drill
    "rbi_drill_mode": "smart",
    "rbi_drill_session_id": str(uuid.uuid4()),
    "rbi_drill_questions": [],
    "rbi_drill_answers": {},
    "rbi_drill_submitted": False,
    "rbi_drill_n": 10,
    "rbi_drill_filter": {"subject": "all", "topic": "all", "difficulty": "all",
                          "is_trap": False, "is_recent": False},
    "rbi_drill_results": [],
}
for _k, _v in _SS_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏦 RBI Prep")
    d = days_to_rbi()
    color_d = "#F28B82" if d <= 5 else "#FDD663" if d <= 10 else "#81C995"
    st.markdown(
        f'<div class="gem-card" style="text-align:center;border-color:{color_d}33">'
        f'<div style="font-size:2rem;font-weight:700;color:{color_d}">{d}</div>'
        f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Days to RBI DEPR</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.caption("**June 14:** Phase 1 · Economics MCQ (100m) + English (100m)")
    st.divider()

    scores = st.session_state.rbi6_scores
    if scores:
        st.markdown('<div class="section-header">Tier 2 Quiz Progress</div>', unsafe_allow_html=True)
        for bk in BUCKET_KEYS:
            if bk in scores:
                s = scores[bk]
                pct = s["correct"] / s["total"]
                cq = "#81C995" if pct >= 0.8 else "#FDD663" if pct >= 0.5 else "#F28B82"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:4px">'
                    f'<span style="font-size:0.78rem;color:#9AA0A6">{BUCKETS[bk]["icon"]} {BUCKETS[bk]["label"][:22]}…</span>'
                    f'<span style="font-size:0.78rem;font-weight:600;color:{cq}">{s["correct"]}/{s["total"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.caption("Complete Tier 2 buckets to see progress here.")

    st.divider()
    st.caption("⚠ Items marked ⚠ need verification at rbi.org.in before exam")

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown("## 🏦 RBI DEPR 2026 Prep")
st.caption("Key Data · Phase 1 Theory Drill · Tier 2 Current Affairs Quiz · Progress Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 Key Data", "🧠 Phase 1 Drill", "❓ Tier 2 Quiz", "📈 My Progress"]
)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Key Data Cards
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.info("Items marked ⚠ depend on live RBI/MoSPI data — verify at rbi.org.in before exam.", icon="⚠")
    for section in KEY_SECTIONS:
        label = section["label"]
        color = section["color"]
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:24px 0 10px">'
            f'<div style="width:4px;height:20px;background:{color};border-radius:2px"></div>'
            f'<span style="font-size:0.95rem;font-weight:600;color:#E8EAED">{label}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        for name, value, note, verify in section["items"]:
            verify_badge = (
                '<span style="font-size:0.68rem;font-weight:700;color:#F28B82;'
                'background:rgba(242,139,130,0.12);border:1px solid rgba(242,139,130,0.3);'
                'border-radius:10px;padding:1px 7px;margin-left:6px">⚠ VERIFY</span>'
                if verify else ""
            )
            st.markdown(
                f'<div class="gem-card-sm" style="border-left:3px solid {color}40">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:4px">'
                f'<span style="font-size:0.82rem;font-weight:600;color:#E8EAED">{name}{verify_badge}</span>'
                f'<span style="font-size:0.82rem;font-weight:700;color:{color};text-align:right;max-width:55%">{value}</span>'
                f'</div>'
                f'<div style="font-size:0.76rem;color:#9AA0A6;margin-top:5px;line-height:1.4">{note}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Phase 1 Theory Drill
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    conn = get_rbi_conn()

    if conn is None:
        st.warning("rbi.db not found. Run `python3 scripts/rbi/00_init_rbi_db.py` first.", icon="⚠")
    else:
        t1_count = conn.execute("SELECT COUNT(*) FROM rbi_questions WHERE tier=1").fetchone()[0]

        if t1_count == 0:
            st.info(
                "**Question bank is being generated.** "
                "Run `python3 scripts/rbi/02_generate_mcq_bank.py` to populate Phase 1 questions. "
                "While you wait, the Tier 2 Quiz tab has 36 current-affairs MCQs ready.",
                icon="⏳",
            )
            st.caption(f"Tier 2 questions in DB: {conn.execute('SELECT COUNT(*) FROM rbi_questions WHERE tier=2').fetchone()[0]}")
        else:
            # ── Mode selector ──────────────────────────────────────────────
            col_mode, col_info = st.columns([2, 3], gap="large")
            with col_mode:
                mode = st.radio(
                    "Session mode",
                    ["🎯 Smart Serve", "🔍 Filter"],
                    index=0 if st.session_state.rbi_drill_mode == "smart" else 1,
                    horizontal=True,
                    key="rbi_drill_mode_radio",
                )
                st.session_state.rbi_drill_mode = "smart" if "Smart" in mode else "filter"

            with col_info:
                if st.session_state.rbi_drill_mode == "smart":
                    st.caption("Smart Serve picks the highest-gap topics and unanswered questions first, based on your coverage data.")
                else:
                    st.caption("Filter mode lets you target a specific subject, topic, or difficulty.")

            # ── Session controls ───────────────────────────────────────────
            if not st.session_state.rbi_drill_questions or st.session_state.rbi_drill_submitted:
                # Show setup panel when no session is active or previous one ended
                if st.session_state.rbi_drill_submitted:
                    # Show summary from last session
                    results = st.session_state.rbi_drill_results
                    if results:
                        correct = sum(1 for r in results if r["is_correct"])
                        total_r = len(results)
                        pct = correct / total_r
                        c_col = "#81C995" if pct >= 0.8 else "#FDD663" if pct >= 0.5 else "#F28B82"
                        st.markdown(
                            f'<div class="score-card" style="border-color:{c_col}33;margin-bottom:16px">'
                            f'<div class="score-num" style="color:{c_col}">{correct}/{total_r}</div>'
                            f'<div class="score-label">Phase 1 Drill — {int(pct * 100)}% correct</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        # Per-question results — Tier 2 style with option highlighting
                        st.markdown("#### Question-by-question breakdown")
                        for i, r in enumerate(results):
                            q_preview = r["question"]
                            q_label = (q_preview[:80] + "…") if len(q_preview) > 80 else q_preview
                            with st.expander(f"{'✅' if r['is_correct'] else '❌'} Q{i+1}  ·  {q_label}"):
                                for opt in r.get("options", []):
                                    is_opt_correct = opt.strip() == r.get("correct_option_full", "").strip()
                                    is_opt_chosen = opt.strip() == r["answer_given"].strip()
                                    if is_opt_correct and is_opt_chosen:
                                        st.markdown(f"**✓ {opt}** ← your answer ✅")
                                    elif is_opt_correct:
                                        st.markdown(f"**✓ {opt}** ← correct answer")
                                    elif is_opt_chosen:
                                        st.markdown(f"~~{opt}~~ ← your answer ❌")
                                    else:
                                        st.markdown(f"  {opt}")
                                st.info(f"**Why:** {r['explanation']}")

                col_start, col_n = st.columns([2, 1])
                with col_n:
                    n_qs = st.selectbox("Questions per session", [5, 10, 15, 20], index=1, key="rbi_drill_n_select")

                if st.session_state.rbi_drill_mode == "filter":
                    subjects = ["all"] + sorted({
                        r[0] for r in conn.execute("SELECT DISTINCT subject FROM rbi_questions WHERE tier=1").fetchall()
                    })
                    selected_subj = st.selectbox("Subject", subjects, key="rbi_filter_subject")

                    topic_query = "SELECT DISTINCT topic FROM rbi_questions WHERE tier=1"
                    topic_params: list = []
                    if selected_subj != "all":
                        topic_query += " AND subject=?"
                        topic_params.append(selected_subj)
                    topics = ["all"] + sorted({r[0] for r in conn.execute(topic_query, topic_params).fetchall()})
                    selected_topic = st.selectbox("Topic", topics, key="rbi_filter_topic")

                    col_diff, col_traps, col_recent = st.columns(3)
                    with col_diff:
                        difficulty = st.selectbox("Difficulty", ["all", "easy", "medium", "hard"], key="rbi_filter_diff")
                    with col_traps:
                        traps_only = st.checkbox("Traps only", key="rbi_filter_traps")
                    with col_recent:
                        recent_only = st.checkbox("Recent data only", key="rbi_filter_recent")

                    st.session_state.rbi_drill_filter = {
                        "subject": selected_subj, "topic": selected_topic,
                        "difficulty": difficulty, "is_trap": traps_only, "is_recent": recent_only,
                    }

                with col_start:
                    btn_label = "▶ Start Smart Session" if st.session_state.rbi_drill_mode == "smart" else "▶ Load Filtered Questions"
                    if st.button(btn_label, type="primary", use_container_width=True):
                        if st.session_state.rbi_drill_mode == "smart":
                            qs = get_smart_questions(conn, n_qs)
                        else:
                            qs = get_filtered_questions(conn, st.session_state.rbi_drill_filter, n_qs)

                        if not qs:
                            st.warning("No questions match the current filters. Try broadening your selection.")
                        else:
                            st.session_state.rbi_drill_questions = qs
                            st.session_state.rbi_drill_answers = {}
                            st.session_state.rbi_drill_submitted = False
                            st.session_state.rbi_drill_results = []
                            st.session_state.rbi_drill_session_id = str(uuid.uuid4())
                            st.rerun()

            else:
                # ── Active quiz session ────────────────────────────────────
                questions = st.session_state.rbi_drill_questions
                session_id = st.session_state.rbi_drill_session_id

                st.caption(f"{len(questions)} questions · Smart Serve" if st.session_state.rbi_drill_mode == "smart"
                           else f"{len(questions)} questions · Filtered")

                answers: dict = {}
                form_key = f"rbi_drill_form_{session_id}"

                with st.form(form_key):
                    for i, q in enumerate(questions):
                        trap_badge = ' <span style="font-size:0.68rem;color:#F28B82;background:rgba(242,139,130,0.1);border:1px solid rgba(242,139,130,0.25);border-radius:8px;padding:1px 6px">⚡ trap</span>' if q.get("is_trap") else ""
                        diff_color = "#81C995" if q.get("difficulty") == "easy" else "#FDD663" if q.get("difficulty") == "medium" else "#F28B82"
                        st.markdown(
                            f'<div style="font-size:0.72rem;color:{diff_color};margin-bottom:2px;text-transform:uppercase;letter-spacing:.05em">'
                            f'{q.get("subject","").replace("_"," ")} · {q.get("topic","").replace("_"," ")} · {q.get("difficulty","")}{trap_badge}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(f"**Q{i+1}.** {q['question']}")
                        opts = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
                        chosen = st.radio("", opts, index=None,
                                          key=f"rbi_drill_q_{session_id}_{q['id']}",
                                          label_visibility="collapsed")
                        answers[q["id"]] = chosen or ""
                        if i < len(questions) - 1:
                            st.markdown("---")

                    st.markdown("")
                    drill_submitted = st.form_submit_button("Submit Session →", use_container_width=True, type="primary")

                if drill_submitted:
                    unanswered = [i + 1 for i, q in enumerate(questions) if not answers.get(q["id"])]
                    if unanswered:
                        nums = ", ".join(f"Q{n}" for n in unanswered)
                        st.warning(f"Please answer {nums} before submitting.")
                    else:
                        results = []
                        for q in questions:
                            chosen_letter = answers.get(q["id"], "")
                            # Extract letter from "A) ..." format
                            letter = chosen_letter[0] if chosen_letter else ""
                            is_correct = letter == q["correct_option"]
                            save_attempt(conn, q["id"], letter, is_correct, session_id,
                                         q["topic"], q["subject"])
                            correct_key = f"option_{q['correct_option'].lower()}"
                            results.append({
                                "question": q["question"],
                                "answer_given": chosen_letter,
                                "correct_option": q["correct_option"],
                                "correct_option_full": q[correct_key],
                                "options": [q["option_a"], q["option_b"], q["option_c"], q["option_d"]],
                                "explanation": q["explanation"],
                                "is_correct": is_correct,
                            })
                        st.session_state.rbi_drill_results = results
                        st.session_state.rbi_drill_submitted = True
                        st.session_state.rbi_drill_questions = []
                        st.rerun()

                col_cancel, _ = st.columns([1, 3])
                with col_cancel:
                    if st.button("✕ Cancel session", use_container_width=True):
                        st.session_state.rbi_drill_questions = []
                        st.session_state.rbi_drill_submitted = False
                        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Tier 2 Quiz (current affairs, no DB)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    col_left, col_right = st.columns([1, 3], gap="large")

    with col_left:
        st.markdown('<div class="section-header">Topic Bucket</div>', unsafe_allow_html=True)
        selected_label = st.radio(
            "Select bucket",
            BUCKET_LABELS,
            index=BUCKET_KEYS.index(st.session_state.rbi6_bucket),
            key="rbi6_bucket_radio",
            label_visibility="collapsed",
        )
        selected_bucket_key = BUCKET_KEYS[BUCKET_LABELS.index(selected_label)]

        if selected_bucket_key != st.session_state.rbi6_bucket:
            st.session_state.rbi6_bucket = selected_bucket_key
            st.session_state.rbi6_submitted = False
            st.session_state.rbi6_answers = {}
            st.session_state.rbi6_session = str(uuid.uuid4())
            st.rerun()

        st.divider()
        total_done = sum(1 for bk in BUCKET_KEYS if bk in st.session_state.rbi6_scores)
        st.markdown(
            f'<div style="font-size:0.78rem;color:#9AA0A6">Buckets completed: '
            f'<strong style="color:#E8EAED">{total_done}/{len(BUCKET_KEYS)}</strong></div>',
            unsafe_allow_html=True,
        )

    with col_right:
        bucket = BUCKETS[selected_bucket_key]
        questions = bucket["qs"]

        st.markdown(f"### {bucket['icon']} {bucket['label']}")
        st.caption(f"{len(questions)} questions · instant grading · no AI cost")

        # ── RESULT VIEW ────────────────────────────────────────────────────
        if st.session_state.rbi6_submitted:
            answers = st.session_state.rbi6_answers
            correct_count = sum(
                1 for q in questions
                if answers.get(q["id"], "").strip() == q["correct"].strip()
            )
            total = len(questions)
            score_pct = correct_count / total

            sc_color = "#81C995" if score_pct >= 0.8 else "#FDD663" if score_pct >= 0.5 else "#F28B82"
            icon = "🟢" if score_pct >= 0.8 else "🟡" if score_pct >= 0.5 else "🔴"
            st.markdown(
                f'<div class="score-card" style="border-color:{sc_color}33;margin-bottom:16px">'
                f'<div class="score-num" style="color:{sc_color}">{icon} {correct_count}/{total}</div>'
                f'<div class="score-label">{int(score_pct * 100)}% correct</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.markdown("#### Per-question breakdown")
            for i, q in enumerate(questions):
                user_ans = answers.get(q["id"], "")
                is_correct = user_ans.strip() == q["correct"].strip()
                with st.expander(f"{'✅' if is_correct else '❌'} Q{i+1}  ·  {q['q'][:80]}{'…' if len(q['q']) > 80 else ''}"):
                    for opt in q["opts"]:
                        is_opt_correct = opt.strip() == q["correct"].strip()
                        is_opt_chosen = opt.strip() == user_ans.strip()
                        if is_opt_correct and is_opt_chosen:
                            st.markdown(f"**✓ {opt}** ← your answer ✅")
                        elif is_opt_correct:
                            st.markdown(f"**✓ {opt}** ← correct answer")
                        elif is_opt_chosen:
                            st.markdown(f"~~{opt}~~ ← your answer ❌")
                        else:
                            st.markdown(f"  {opt}")
                    st.info(f"**Why:** {q['exp']}")

            curr_idx = BUCKET_KEYS.index(selected_bucket_key)
            all_done = total_done == len(BUCKET_KEYS)

            if all_done:
                # ── Completion handler (was silently looping before) ───────
                total_correct = sum(v["correct"] for v in st.session_state.rbi6_scores.values())
                total_qs = sum(v["total"] for v in st.session_state.rbi6_scores.values())
                agg_pct = total_correct / total_qs if total_qs else 0
                agg_color = "#81C995" if agg_pct >= 0.8 else "#FDD663" if agg_pct >= 0.5 else "#F28B82"

                st.success("All 6 Tier 2 buckets complete!", icon="🎉")
                st.markdown(
                    f'<div class="score-card" style="border-color:{agg_color}33;margin:12px 0">'
                    f'<div class="score-num" style="color:{agg_color}">{total_correct}/{total_qs}</div>'
                    f'<div class="score-label">Overall Tier 2 — {int(agg_pct * 100)}% correct</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                # Show weakest bucket
                weakest = min(
                    st.session_state.rbi6_scores.items(),
                    key=lambda kv: kv[1]["correct"] / kv[1]["total"],
                )
                wk, ws = weakest
                w_pct = ws["correct"] / ws["total"]
                st.warning(
                    f"Weakest bucket: **{BUCKETS[wk]['icon']} {BUCKETS[wk]['label']}** "
                    f"({ws['correct']}/{ws['total']} = {int(w_pct*100)}%). Retry it below.",
                    icon="⚠",
                )
                if st.button("↩ Retry weakest bucket", type="primary"):
                    st.session_state.rbi6_bucket = wk
                    st.session_state.rbi6_submitted = False
                    st.session_state.rbi6_answers = {}
                    st.session_state.rbi6_session = str(uuid.uuid4())
                    # Don't reset scores so progress is preserved
                    st.rerun()
                if st.button("🔄 Restart all buckets"):
                    st.session_state.rbi6_scores = {}
                    st.session_state.rbi6_submitted = False
                    st.session_state.rbi6_answers = {}
                    st.session_state.rbi6_bucket = BUCKET_KEYS[0]
                    st.rerun()
            else:
                col_retry, col_next = st.columns(2)
                with col_retry:
                    if st.button("↩ Retry this bucket", use_container_width=True):
                        st.session_state.rbi6_submitted = False
                        st.session_state.rbi6_answers = {}
                        st.session_state.rbi6_session = str(uuid.uuid4())
                        st.rerun()
                with col_next:
                    next_idx = (curr_idx + 1) % len(BUCKET_KEYS)
                    next_key = BUCKET_KEYS[next_idx]
                    if st.button(f"Next → {BUCKETS[next_key]['label'][:28]}…", use_container_width=True, type="primary"):
                        st.session_state.rbi6_bucket = next_key
                        st.session_state.rbi6_submitted = False
                        st.session_state.rbi6_answers = {}
                        st.session_state.rbi6_session = str(uuid.uuid4())
                        st.rerun()

        # ── QUIZ FORM ──────────────────────────────────────────────────────
        else:
            st.markdown("Answer all questions, then submit.")
            st.caption("Explanations shown after submission · no AI calls")

            answers2: dict = {}
            form_key2 = f"rbi6_form_{selected_bucket_key}_{st.session_state.rbi6_session}"

            with st.form(form_key2):
                for i, q in enumerate(questions):
                    st.markdown(f"**Q{i+1}.** {q['q']}")
                    chosen = st.radio(
                        "", q["opts"], index=None,
                        key=f"rbi6_radio_{q['id']}_{st.session_state.rbi6_session}",
                        label_visibility="collapsed",
                    )
                    answers2[q["id"]] = chosen or ""
                    if i < len(questions) - 1:
                        st.markdown("---")

                st.markdown("")
                submitted2 = st.form_submit_button("Submit →", use_container_width=True, type="primary")

            if submitted2:
                unanswered2 = [i + 1 for i, q in enumerate(questions) if not answers2.get(q["id"])]
                if unanswered2:
                    nums2 = ", ".join(f"Q{n}" for n in unanswered2)
                    st.warning(f"Please answer {nums2} before submitting.")
                else:
                    correct_count2 = sum(
                        1 for q in questions
                        if answers2.get(q["id"], "").strip() == q["correct"].strip()
                    )
                    st.session_state.rbi6_scores[selected_bucket_key] = {
                        "correct": correct_count2,
                        "total": len(questions),
                    }
                    st.session_state.rbi6_answers = answers2
                    st.session_state.rbi6_submitted = True
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — My Progress
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    conn4 = get_rbi_conn()

    if conn4 is None:
        st.warning("rbi.db not found.", icon="⚠")
    else:
        total_attempts = conn4.execute(
            "SELECT COUNT(*) FROM rbi_attempts WHERE user_id=?", (get_user_id(),)
        ).fetchone()[0]

        if total_attempts == 0:
            st.info(
                "No Phase 1 drill attempts yet. Complete sessions in the **Phase 1 Drill** tab to see your coverage and readiness scores here.",
                icon="📊",
            )
            # Still show Tier 2 summary if available
            if st.session_state.rbi6_scores:
                st.markdown("#### Tier 2 Quiz Summary")
                for bk, s in st.session_state.rbi6_scores.items():
                    p = s["correct"] / s["total"]
                    c = "#81C995" if p >= 0.8 else "#FDD663" if p >= 0.5 else "#F28B82"
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #2a2a2a">'
                        f'<span style="font-size:0.82rem">{BUCKETS[bk]["icon"]} {BUCKETS[bk]["label"]}</span>'
                        f'<span style="font-size:0.82rem;font-weight:600;color:{c}">{s["correct"]}/{s["total"]} ({int(p*100)}%)</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        else:
            pd = get_progress_data(conn4)
            formula_pct = pd["formula_score"]
            true_pct = pd["true_readiness"]

            # ── Readiness header ───────────────────────────────────────────
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                fc = "#81C995" if formula_pct >= 0.7 else "#FDD663" if formula_pct >= 0.4 else "#F28B82"
                st.markdown(
                    f'<div class="gem-card" style="text-align:center;border-color:{fc}33">'
                    f'<div style="font-size:1.8rem;font-weight:700;color:{fc}">{int(formula_pct*100)}%</div>'
                    f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Mastery Score (weighted avg)</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with rc2:
                tc = "#81C995" if true_pct >= 0.6 else "#FDD663" if true_pct >= 0.35 else "#F28B82"
                st.markdown(
                    f'<div class="gem-card" style="text-align:center;border-color:{tc}33">'
                    f'<div style="font-size:1.8rem;font-weight:700;color:{tc}">{int(true_pct*100)}%</div>'
                    f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Exam Readiness (gap-adjusted)</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with rc3:
                st.markdown(
                    f'<div class="gem-card" style="text-align:center">'
                    f'<div style="font-size:1.8rem;font-weight:700;color:#8AB4F8">{pd["total_attempts"]}</div>'
                    f'<div style="font-size:0.72rem;color:#9AA0A6;text-transform:uppercase;letter-spacing:.06em">Questions Attempted</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.caption("True Readiness = Formula score minus gap penalty for topics <50% covered.")

            # ── Gap alerts ─────────────────────────────────────────────────
            gaps = pd["gaps"]
            if gaps:
                st.markdown("#### ⚠ Gap Alerts — study these first")
                for g in gaps[:5]:
                    cov = g["coverage_pct"]
                    gi = g["flag_impact"]
                    gcol = "#F28B82" if cov < 0.2 else "#FDD663"
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;align-items:center;'
                        f'padding:8px 12px;background:rgba(255,255,255,0.03);border-left:3px solid {gcol};'
                        f'border-radius:4px;margin-bottom:6px">'
                        f'<div>'
                        f'<span style="font-size:0.84rem;font-weight:600;color:#E8EAED">{g["topic"].replace("_"," ").title()}</span>'
                        f'<span style="font-size:0.72rem;color:#9AA0A6;margin-left:8px">{g["subject"].replace("_"," ")}</span>'
                        f'</div>'
                        f'<div style="text-align:right">'
                        f'<span style="font-size:0.82rem;color:{gcol};font-weight:600">{int(cov*100)}% covered</span>'
                        f'<span style="font-size:0.70rem;color:#9AA0A6;display:block">impact {gi:.3f}</span>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                if st.button("🎯 Start Smart Session on top gap", type="primary"):
                    st.session_state.rbi_drill_mode = "smart"
                    st.session_state.rbi_drill_questions = []
                    st.session_state.rbi_drill_submitted = False
                    st.rerun()
            else:
                st.success("No critical gaps! All topics ≥50% covered.", icon="✅")

            # ── Subject breakdown ──────────────────────────────────────────
            st.markdown("#### Subject Coverage")
            SUBJECT_LABELS = {
                "macro": "Macroeconomics", "intl_econ": "International Economics",
                "growth": "Growth & Development", "micro": "Microeconomics",
                "pub_finance": "Public Finance", "quant": "Quantitative Methods",
                "env_econ": "Environmental Economics", "rbi_banking": "RBI / Banking",
                "indian_econ": "Indian Economy",
            }
            for subj, cov in sorted(pd["subject_coverage"].items(), key=lambda x: x[1]):
                label = SUBJECT_LABELS.get(subj, subj.replace("_", " ").title())
                bar_color = "#81C995" if cov >= 0.7 else "#FDD663" if cov >= 0.4 else "#F28B82"
                bar_w = max(2, int(cov * 100))
                st.markdown(
                    f'<div style="margin-bottom:8px">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
                    f'<span style="font-size:0.78rem;color:#9AA0A6">{label}</span>'
                    f'<span style="font-size:0.78rem;font-weight:600;color:{bar_color}">{int(cov*100)}%</span>'
                    f'</div>'
                    f'<div style="background:#2a2a2a;border-radius:3px;height:5px">'
                    f'<div style="width:{bar_w}%;background:{bar_color};border-radius:3px;height:5px"></div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
