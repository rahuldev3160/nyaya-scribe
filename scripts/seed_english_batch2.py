"""
Seed English practice batch 2 — 15 new questions across 5 types.
Idempotent: skips existing question_ids.
Run: python3 scripts/seed_english_batch2.py
"""
import json
import sys
import uuid
from pathlib import Path

import sqlite3

EXAM_ID = "english_practice"


def kw(canonical, variants, weight=1, ktype="required", threshold=0.82, penalty=None):
    e = {"canonical": canonical, "variants": variants,
         "weight": weight, "keyword_type": ktype, "fuzzy_threshold": threshold}
    if penalty is not None:
        e["penalty"] = penalty
    return e


# ══════════════════════════════════════════════════════════════════════════════
# ESSAYS
# ══════════════════════════════════════════════════════════════════════════════

ESSAY_003 = {
    "question_id": "eng_essay_003",
    "type_id": "essay",
    "source_exam": "rbi_depr_2024",
    "difficulty": "hard",
    "marks": 40,
    "word_guide_json": json.dumps({"intro": 80, "body": 400, "conclusion": 80}),
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "Examine the role of macroprudential policy tools in safeguarding India's financial stability. "
        "Discuss the instruments used by the Reserve Bank of India and assess their effectiveness "
        "in managing systemic risk.\n"
        "(RBI Grade B DEPR — 550–600 words)"
    ),
    "intro_text": (
        "Financial stability — the condition in which the financial system intermediates funds, "
        "manages risk, and supports growth without major disruptions — is increasingly maintained "
        "through macroprudential policy rather than institution-by-institution microprudential supervision alone. "
        "In India, the Reserve Bank of India (RBI) deploys a range of macroprudential instruments to "
        "contain systemic risk, and their record over the past decade warrants careful assessment."
    ),
    "body_text": (
        "India's macroprudential toolkit operates at both the capital and credit levels. "
        "On the capital side, banks must maintain a minimum Capital to Risk-weighted Assets Ratio (CRAR) of 9%, "
        "higher than the Basel III global minimum of 8%, supplemented by a Capital Conservation Buffer (CCB) of 2.5%. "
        "The Countercyclical Capital Buffer (CCyB) — designed to absorb losses during downturns by building capital "
        "in good times — has been set at zero in India, reflecting the RBI's judgment that credit growth has not "
        "yet reached levels warranting activation. Differential risk weights on unsecured retail loans "
        "(raised to 125% in 2023 for consumer credit growing faster than 30%) represent a targeted macroprudential "
        "response to rising household leverage.\n\n"
        "On the credit side, loan-to-value (LTV) ratios for housing loans and debt service coverage ratio (DSCR) "
        "norms contain speculative lending in real estate. The Prompt Corrective Action (PCA) framework triggers "
        "supervisory restrictions — on dividends, lending growth, and branch expansion — when banks breach capital "
        "or NPA thresholds, effectively forcing deleveraging before insolvency risk materialises.\n\n"
        "The effectiveness of these tools is visible in India's banking sector trajectory. Gross NPA ratios peaked "
        "at 11.2% of advances in March 2018 and declined to 2.2% by September 2025 — a multi-decade low — "
        "reflecting both regulatory pressure and the IBC-led resolution of legacy stressed assets. "
        "The Financial Stability and Development Council (FSDC), chaired by the Finance Minister, provides "
        "inter-regulatory coordination across the RBI, SEBI, IRDAI, and PFRDA — a systemic risk governance "
        "structure absent before 2010.\n\n"
        "Nonetheless, significant risks persist. Shadow banking through non-bank financial companies (NBFCs) "
        "operates partly outside the macroprudential perimeter. The IL&FS collapse (2018) and DHFL failure (2019) "
        "exposed how regulatory arbitrage — where risks migrate from banks to less-regulated entities — can "
        "undermine system-wide stability. Crypto-assets, while restricted in India, and fintech lending platforms "
        "represent emerging regulatory perimeter challenges that existing macroprudential frameworks are not yet "
        "fully equipped to address."
    ),
    "conclusion_text": (
        "India's macroprudential framework has demonstrably strengthened the banking system's resilience "
        "since the NPA crisis of 2015–18. However, as financial intermediation migrates to NBFCs, fintechs, "
        "and capital markets, the regulatory perimeter must expand correspondingly. "
        "Effective financial stability requires not merely robust instruments but dynamic perimeter governance "
        "and genuine inter-regulatory coordination through the FSDC."
    ),
    "keywords": {
        "intro": [
            kw("macroprudential", ["macroprudential", "macro-prudential", "macroprudential policy"], weight=2),
            kw("financial stability", ["financial stability", "systemic stability"], weight=2),
            kw("systemic risk", ["systemic risk", "system-wide risk"], weight=1),
        ],
        "body": [
            kw("CRAR", ["CRAR", "capital adequacy ratio", "capital to risk", "capital requirements"], weight=2),
            kw("countercyclical capital buffer", ["countercyclical capital buffer", "CCyB", "capital buffer"], weight=2),
            kw("prompt corrective action", ["prompt corrective action", "PCA"], weight=2),
            kw("NPA", ["NPA", "non-performing assets", "gross NPA", "stressed assets"], weight=2),
            kw("FSDC", ["FSDC", "Financial Stability and Development Council"], weight=1),
            kw("shadow banking", ["shadow banking", "NBFC", "non-bank", "regulatory arbitrage"], weight=1),
            kw("loan-to-value", ["loan to value", "LTV", "debt service coverage", "DSCR"], weight=1, ktype="bonus"),
            kw("risk weights", ["risk weights", "risk-weighted", "consumer credit"], weight=1, ktype="bonus"),
        ],
        "conclusion": [
            kw("regulatory perimeter", ["regulatory perimeter", "perimeter", "regulatory oversight"], weight=2),
            kw("inter-regulatory coordination", ["inter-regulatory", "coordination", "FSDC coordination"], weight=1),
            kw("resilience", ["resilience", "systemic resilience", "banking resilience"], weight=1),
        ],
    },
}

ESSAY_004 = {
    "question_id": "eng_essay_004",
    "type_id": "essay",
    "source_exam": "rbi_depr_2025",
    "difficulty": "medium",
    "marks": 40,
    "word_guide_json": json.dumps({"intro": 80, "body": 400, "conclusion": 80}),
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "India's Digital Public Infrastructure (DPI) — comprising Aadhaar, UPI, and the Account "
        "Aggregator framework — has been described as a new paradigm for financial inclusion and "
        "economic development. Critically evaluate its achievements and the systemic risks it introduces.\n"
        "(RBI Grade B DEPR / IES Economic Service — 550–600 words)"
    ),
    "intro_text": (
        "India's Digital Public Infrastructure (DPI) represents an unprecedented experiment in using "
        "state-built open-layer technology as the foundation for financial and social services. "
        "The convergence of Aadhaar biometric identity, Unified Payments Interface (UPI), and the "
        "Account Aggregator framework has created a data and transaction highway that has fundamentally "
        "altered the economics of financial inclusion. This essay evaluates the achievements of this "
        "approach and examines the systemic risks that concentration and digitalisation introduce."
    ),
    "body_text": (
        "The achievements of India's DPI are quantifiable and substantial. UPI processed over 13 billion "
        "transactions per month by early 2025, with a transaction value exceeding ₹20 lakh crore monthly — "
        "making India the world's largest real-time payments market by volume. Direct Benefit Transfer (DBT) "
        "enabled by the JAM trinity — Jan Dhan accounts, Aadhaar identity verification, and Mobile connectivity — "
        "has transferred over ₹34 lakh crore to beneficiaries since 2013, with estimated leakage savings "
        "of ₹2.7 lakh crore by reducing ghost beneficiaries and intermediary capture. The RBI's Financial "
        "Inclusion Index rose from 53.9 in 2021 to 67 in 2025, reflecting improvements across access, "
        "usage, and quality dimensions.\n\n"
        "The Account Aggregator (AA) framework, operationalised in 2021, enables consent-based financial "
        "data sharing between financial institutions — allowing lenders to access a borrower's complete "
        "financial profile (bank statements, GST returns, mutual fund holdings) with a single digital "
        "consent. This has dramatically reduced information asymmetry in small business and retail lending, "
        "enabling flow-based credit assessment for borrowers who lack collateral.\n\n"
        "However, the risks introduced by DPI are proportional to its scale. Concentration risk is acute: "
        "UPI's architecture makes NPCI a single point of failure for India's payment system — a 2023 "
        "outage lasting several hours underscored this vulnerability. The Digital Personal Data Protection "
        "(DPDP) Act 2023 establishes a consent-based data governance framework, but its implementation "
        "and enforcement are nascent. Digital exclusion — affecting elderly citizens, rural women with "
        "limited digital literacy, and those with biometric matching failures — risks creating a "
        "two-tier economy where the digitally disconnected are structurally excluded from formal services. "
        "Finally, India's DPI has attracted international interest, raising geopolitical questions about "
        "data sovereignty and the security architecture of critical financial infrastructure."
    ),
    "conclusion_text": (
        "India's DPI has achieved genuine scale in financial inclusion and payment infrastructure at "
        "historically unprecedented speed and low cost. The risks of concentration, data privacy, and "
        "digital exclusion are real but addressable through regulatory investment — robust implementation "
        "of the DPDP framework, mandatory interoperability redundancy in payment infrastructure, "
        "and last-mile digital literacy programmes. The DPI model's export potential reflects its "
        "intrinsic strengths; addressing its vulnerabilities determines whether those strengths are durable."
    ),
    "keywords": {
        "intro": [
            kw("digital public infrastructure", ["digital public infrastructure", "DPI"], weight=2),
            kw("UPI", ["UPI", "unified payments interface"], weight=1),
            kw("financial inclusion", ["financial inclusion", "inclusion"], weight=1),
        ],
        "body": [
            kw("JAM trinity", ["JAM trinity", "JAM", "Jan Dhan Aadhaar Mobile"], weight=2),
            kw("Direct Benefit Transfer", ["direct benefit transfer", "DBT", "leakage savings"], weight=2),
            kw("Account Aggregator", ["account aggregator", "AA framework", "consent-based"], weight=2),
            kw("FI-Index", ["FI index", "financial inclusion index"], weight=1),
            kw("concentration risk", ["concentration risk", "single point of failure", "NPCI"], weight=2),
            kw("digital exclusion", ["digital exclusion", "digital divide", "digital literacy"], weight=1),
            kw("data privacy", ["data privacy", "DPDP", "data protection", "data sovereignty"], weight=1),
        ],
        "conclusion": [
            kw("DPDP", ["DPDP", "data protection", "digital personal data protection"], weight=1),
            kw("interoperability", ["interoperability", "redundancy", "resilience"], weight=1),
            kw("digital literacy", ["digital literacy", "last mile", "inclusion"], weight=1),
        ],
    },
}

ESSAY_005 = {
    "question_id": "eng_essay_005",
    "type_id": "essay",
    "source_exam": "ies_2024",
    "difficulty": "medium",
    "marks": 40,
    "word_guide_json": json.dumps({"intro": 80, "body": 400, "conclusion": 80}),
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "Farm loan waivers have been announced by multiple state governments in India over the past decade. "
        "Critically examine whether such measures address the structural causes of agrarian distress "
        "or constitute a moral hazard that undermines formal rural credit culture.\n"
        "(IES Economic Service — 550–600 words)"
    ),
    "intro_text": (
        "Farm loan waivers — state government schemes that extinguish outstanding agricultural credit — "
        "have become a recurring feature of India's electoral and agrarian policy landscape. "
        "Since 2017, states including Uttar Pradesh, Maharashtra, Punjab, and Tamil Nadu have announced "
        "waivers aggregating over ₹4 lakh crore. While these measures provide immediate relief to "
        "distressed farmers, a critical examination reveals that they address the symptoms rather than "
        "the structural causes of agrarian crisis and impose significant long-run costs on rural credit markets."
    ),
    "body_text": (
        "The structural causes of India's agrarian distress are deep-rooted and not addressed by debt relief. "
        "Average farm size has declined to 1.1 hectares, making economies of scale impossible for most farmers. "
        "Terms of trade have historically moved against agriculture: farm input costs (seeds, fertilisers, "
        "machinery) have risen faster than output prices. Minimum Support Price (MSP) procurement covers only "
        "wheat and paddy effectively, leaving most crop varieties — including pulses, oilseeds, and commercial "
        "crops — exposed to market volatility. Irrigation coverage remains below 50% of net sown area, "
        "making output highly dependent on monsoon variability. Farm loan waivers address none of these "
        "structural deficiencies — a farmer whose crop fails due to drought will face the same distress "
        "the next season regardless of debt relief received today.\n\n"
        "The moral hazard consequences are well-documented. Anticipation of future waivers creates strategic "
        "default incentives: surveys of post-waiver periods in Maharashtra and Uttar Pradesh found significant "
        "increases in wilful non-repayment among farmers who expected further relief. Priority Sector "
        "Lending (PSL) NPA ratios for agricultural credit consistently spike after waiver announcements. "
        "Formal lenders — particularly cooperative banks and regional rural banks — face balance sheet stress "
        "that reduces their capacity for fresh credit disbursement, creating a credit drought precisely when "
        "waived farmers need new capital to invest in the next crop cycle.\n\n"
        "The fiscal burden is also substantial. Farm loan waivers typically cost 1–3% of state GDP and are "
        "financed through diversion from productive capital expenditure — roads, irrigation, storage "
        "infrastructure — that would have directly improved farm productivity and long-term income."
    ),
    "conclusion_text": (
        "Farm loan waivers are a politically potent but economically inefficient response to agrarian distress. "
        "A more effective policy architecture would combine direct income support through PM-KISAN, "
        "expanded crop insurance under PMFBY with actuarially fair premiums, investment in post-harvest "
        "cold storage and market infrastructure, and MSP extension to a wider crop basket. "
        "Structural solutions require structural investment, not periodic debt forgiveness that "
        "perpetuates the cycle of distress and relief."
    ),
    "keywords": {
        "intro": [
            kw("farm loan waiver", ["farm loan waiver", "loan waiver", "agricultural debt relief", "debt waiver"], weight=2),
            kw("agrarian distress", ["agrarian distress", "farmer distress", "agricultural distress"], weight=2),
            kw("structural causes", ["structural causes", "structural", "underlying causes"], weight=1),
        ],
        "body": [
            kw("terms of trade", ["terms of trade", "trade terms against agriculture", "input costs"], weight=2),
            kw("MSP", ["MSP", "minimum support price", "procurement"], weight=2),
            kw("moral hazard", ["moral hazard", "strategic default", "wilful default", "anticipation of waivers"], weight=2),
            kw("PSL NPA", ["PSL NPA", "priority sector NPA", "agricultural NPA", "credit default"], weight=2),
            kw("fiscal burden", ["fiscal burden", "state GDP", "capital expenditure diversion"], weight=1),
            kw("credit drought", ["credit drought", "fresh credit", "credit supply"], weight=1, ktype="bonus"),
        ],
        "conclusion": [
            kw("PM-KISAN", ["PM-KISAN", "direct income support", "income support"], weight=1),
            kw("PMFBY", ["PMFBY", "crop insurance", "pradhan mantri fasal bima"], weight=1),
            kw("structural investment", ["structural investment", "structural reform", "post-harvest", "market infrastructure"], weight=1),
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# PRÉCIS
# ══════════════════════════════════════════════════════════════════════════════

PRECIS_002 = {
    "question_id": "eng_precis_002",
    "type_id": "précis",
    "source_exam": "ies_2024",
    "difficulty": "medium",
    "marks": 30,
    "word_guide_json": json.dumps({"intro": 10, "body": 140, "conclusion": 10}),
    "word_count_target": 140,
    "section_weights_json": json.dumps({"intro": 0.10, "body": 0.80, "conclusion": 0.10}),
    "prompt_text": (
        "Read the following passage carefully and write a précis in approximately 140 words. "
        "Give your précis a suitable title.\n\n"
        "---\n\n"
        "India's fiscal consolidation journey has been marked by both progress and persistent tension. "
        "The Fiscal Responsibility and Budget Management (FRBM) Act of 2003 established the foundational "
        "architecture: a statutory commitment to reduce the central government's Gross Fiscal Deficit (GFD) "
        "to 3% of GDP and eliminate the Revenue Deficit over time. For a decade, this framework delivered "
        "tangible results — the GFD fell from 5.9% of GDP in 2001–02 to 2.5% in 2007–08, and the Revenue "
        "Deficit was eliminated by 2007–08. However, the global financial crisis of 2008 forced a deliberate "
        "departure from the consolidation path as countercyclical fiscal expansion became necessary to "
        "support demand.\n\n"
        "The subsequent decade saw persistent overshooting of fiscal targets, driven partly by electoral "
        "pressures, partly by inadequate revenue growth, and partly by the structural rigidity of committed "
        "expenditures — interest payments, salaries, and pension obligations — which leave limited room for "
        "discretionary adjustment. The pandemic of 2020–21 necessitated a further departure, with the GFD "
        "widening to 9.2% of GDP at the Centre alone, reflecting emergency health and welfare expenditures.\n\n"
        "The post-pandemic consolidation has been more credible. The central government reduced the GFD "
        "from 9.2% (FY21) to 4.3% (FY27 Budget Estimate), reflecting disciplined expenditure rationalisation "
        "and strong GST revenue buoyancy. The 16th Finance Commission, chaired by Dr Arvind Panagariya, "
        "has been tasked with recommending a medium-term fiscal framework that balances the need for continued "
        "consolidation with the imperative of sustaining high capital expenditure for infrastructure.\n\n"
        "The deeper challenge is structural. India's tax-to-GDP ratio — at approximately 17% including "
        "states — remains well below peer emerging markets, limiting the revenue headroom available for "
        "deficit reduction without compressing productive expenditure. The twin anchors recommended by the "
        "NK Singh Committee — a GFD target of 3% and a combined public debt anchor of 60% of GDP — "
        "provide a medium-term destination, but the pace and path of convergence remain contested.\n\n"
        "---\n\n"
        "*(Source passage: ~400 words. Your précis should be approximately 140 words. "
        "Write the title in your Introduction section. State your word count at the end of your Body.)*"
    ),
    "intro_text": "India's Fiscal Consolidation: Progress, Setbacks, and the Path Ahead",
    "body_text": (
        "The author traces India's fiscal consolidation trajectory from the FRBM Act of 2003 to the present. "
        "Initial progress was substantial — the Gross Fiscal Deficit fell from 5.9% of GDP (2001–02) to 2.5% (2007–08) — "
        "before the global financial crisis necessitated countercyclical expansion. "
        "The subsequent decade saw persistent target overshooting, driven by revenue shortfalls and structural "
        "expenditure rigidity in committed items such as interest payments and salaries. "
        "The pandemic widened the deficit to 9.2% of GDP before post-pandemic consolidation reduced it to 4.3% by FY27. "
        "The author identifies a structural revenue constraint — India's tax-to-GDP ratio of 17% is well below "
        "peer emerging markets — as the central obstacle to meeting the NK Singh Committee's dual anchors "
        "of a 3% GFD target and a 60% public debt ceiling."
    ),
    "conclusion_text": "[Word count: 138]",
    "keywords": {
        "intro": [
            kw("fiscal consolidation", ["fiscal consolidation", "fiscal deficit", "FRBM"], weight=2),
        ],
        "body": [
            kw("FRBM", ["FRBM", "Fiscal Responsibility and Budget Management", "fiscal responsibility"], weight=2),
            kw("Gross Fiscal Deficit", ["gross fiscal deficit", "GFD", "fiscal deficit"], weight=2),
            kw("countercyclical", ["countercyclical", "countercyclical fiscal", "fiscal expansion"], weight=1),
            kw("tax-to-GDP ratio", ["tax to GDP", "tax GDP ratio", "revenue constraint"], weight=2),
            kw("NK Singh Committee", ["NK Singh", "NK Singh Committee", "dual anchors", "debt anchor"], weight=1),
            kw("pandemic", ["pandemic", "COVID", "2020-21"], weight=1),
        ],
        "conclusion": [
            kw("word count", ["word count", "[word count"], weight=2),
        ],
    },
}

PRECIS_003 = {
    "question_id": "eng_precis_003",
    "type_id": "précis",
    "source_exam": "rbi_depr_2024",
    "difficulty": "medium",
    "marks": 30,
    "word_guide_json": json.dumps({"intro": 10, "body": 140, "conclusion": 10}),
    "word_count_target": 140,
    "section_weights_json": json.dumps({"intro": 0.10, "body": 0.80, "conclusion": 0.10}),
    "prompt_text": (
        "Read the following passage carefully and write a précis in approximately 140 words. "
        "Give your précis a suitable title.\n\n"
        "---\n\n"
        "The intersection of climate change and financial stability has moved from the margins to the "
        "centre of central banking discourse. The Network for Greening the Financial System (NGFS), "
        "now comprising over 130 central banks and supervisors including the Reserve Bank of India, "
        "has established that climate-related financial risks — both physical risks from extreme weather "
        "events and transition risks from the shift to a low-carbon economy — can materialise as "
        "traditional financial risks: credit risk, market risk, and liquidity risk. A bank with "
        "significant lending to coal-dependent industries faces transition risk as carbon pricing "
        "erodes the value of those assets. A coastal infrastructure lender faces physical risk as "
        "sea-level rise and cyclones impair borrower collateral.\n\n"
        "India issued its first Sovereign Green Bonds in January 2023, raising ₹8,000 crore "
        "for government green expenditure in the Union Budget. A second tranche followed in "
        "February 2023, taking the total to ₹16,000 crore for FY2022–23. The proceeds were "
        "earmarked for eligible green projects — solar power, offshore wind, green hydrogen, "
        "and energy-efficient rail transport — as defined under the Sovereign Green Bond Framework "
        "published by the Ministry of Finance. The framework aligned with ICMA's Green Bond Principles, "
        "providing international investor confidence in use-of-proceeds integrity.\n\n"
        "However, India's green finance ecosystem faces structural challenges. The green bond market "
        "remains small relative to the investment needs estimated in India's Nationally Determined "
        "Contributions (NDC) to the Paris Agreement — achieving net zero by 2070 requires an "
        "estimated $10 trillion in transition finance. Taxonomic clarity — a consistent definition "
        "of what constitutes a 'green' activity for Indian regulatory and tax purposes — is still "
        "developing. Greenwashing risk, where financial products are labelled green without substantive "
        "environmental impact, requires robust third-party verification frameworks. "
        "The RBI's regulatory role in climate-risk stress testing of banks remains in early stages "
        "compared to European peers.\n\n"
        "---\n\n"
        "*(Source passage: ~390 words. Your précis should be approximately 140 words. "
        "Write the title in your Introduction section. State your word count at the end of your Body.)*"
    ),
    "intro_text": "Climate Finance in India: Green Bonds, Systemic Risk, and the Road to Net Zero",
    "body_text": (
        "The author argues that climate-related financial risks — physical risks from extreme weather and "
        "transition risks from decarbonisation — now represent mainstream credit, market, and liquidity risks "
        "that central banks can no longer ignore. The RBI's membership of the NGFS reflects this recognition. "
        "India issued its first Sovereign Green Bonds in January 2023, raising ₹16,000 crore in FY2022–23 "
        "for solar, wind, green hydrogen, and energy-efficient rail, with proceeds governed under a framework "
        "aligned to ICMA's Green Bond Principles. However, the author identifies structural gaps: India's "
        "green finance market remains far below the investment scale required by its NDC commitments, "
        "a clear green taxonomy is lacking, greenwashing risk is inadequately supervised, and the RBI's "
        "climate-risk stress testing lags European central bank standards."
    ),
    "conclusion_text": "[Word count: 137]",
    "keywords": {
        "intro": [
            kw("climate finance", ["climate finance", "green finance", "green bonds"], weight=2),
        ],
        "body": [
            kw("NGFS", ["NGFS", "Network for Greening the Financial System"], weight=1),
            kw("physical risk", ["physical risk", "transition risk", "climate risk"], weight=2),
            kw("sovereign green bonds", ["sovereign green bonds", "green bonds", "₹16,000 crore"], weight=2),
            kw("NDC", ["NDC", "nationally determined contributions", "Paris Agreement", "net zero"], weight=1),
            kw("green taxonomy", ["green taxonomy", "taxonomy", "definition of green"], weight=1),
            kw("greenwashing", ["greenwashing", "greenwash"], weight=1),
        ],
        "conclusion": [
            kw("word count", ["word count", "[word count"], weight=2),
        ],
    },
}

PRECIS_004 = {
    "question_id": "eng_precis_004",
    "type_id": "précis",
    "source_exam": "upsc_2024",
    "difficulty": "hard",
    "marks": 30,
    "word_guide_json": json.dumps({"intro": 10, "body": 140, "conclusion": 10}),
    "word_count_target": 140,
    "section_weights_json": json.dumps({"intro": 0.10, "body": 0.80, "conclusion": 0.10}),
    "prompt_text": (
        "Read the following passage carefully and write a précis in approximately 140 words. "
        "Give your précis a suitable title.\n\n"
        "---\n\n"
        "India's labour market is characterised by a fundamental paradox: a young, large, and "
        "growing workforce coexisting with persistently high informality, low productivity, "
        "and inadequate job creation in the formal sector. Approximately 90% of India's workforce "
        "— an estimated 450–470 million workers — is employed in the informal economy, where "
        "earnings are volatile, social protection is absent, and productivity is a fraction of "
        "formal sector levels. This informality is not merely a legacy feature of underdevelopment; "
        "it is actively reproduced by regulatory and fiscal structures that make formalisation costly "
        "for small enterprises.\n\n"
        "The structural drivers of informality are multiple. India's labour laws — historically fragmented "
        "across over 40 central Acts — imposed compliance costs that incentivised small firms to remain "
        "below thresholds that triggered legal obligations. The Labour Codes of 2019–20 consolidated these "
        "into four codes covering wages, social security, industrial relations, and occupational safety, "
        "but their implementation by states remains uneven. Contract labour, which allows firms to access "
        "workers without long-term employment obligations, further entrenches informality within formally "
        "registered enterprises.\n\n"
        "The implications for development are severe. Informal workers cannot access formal credit, "
        "limiting their ability to invest in skill acquisition or productive assets. The informal sector "
        "contributes less than 50% of GDP despite employing 90% of the workforce — an extreme "
        "productivity gap that reflects the misallocation of labour away from high-productivity activities. "
        "Social protection coverage is partial: the Employees' State Insurance (ESI) and Employees' "
        "Provident Fund (EPF) cover only formal employees, leaving the vast majority of workers without "
        "unemployment insurance, healthcare, or pension security.\n\n"
        "Addressing informality requires a dual strategy: reducing the regulatory cost of formalisation "
        "for enterprises, and extending portable social protection to informal workers regardless of "
        "employment status. The e-Shram portal, which registered over 280 million informal workers "
        "by 2024, represents a first step toward the latter. Bridging the formality gap is ultimately "
        "inseparable from the broader objective of structural transformation toward higher-productivity, "
        "higher-wage employment.\n\n"
        "---\n\n"
        "*(Source passage: ~420 words. Your précis should be approximately 140 words. "
        "Write the title in your Introduction section. State your word count at the end of your Body.)*"
    ),
    "intro_text": "India's Informal Labour Market: Structural Causes, Development Costs, and Reform Imperatives",
    "body_text": (
        "The author argues that India's labour market paradox — a young workforce coexisting with 90% informality "
        "— is not merely a legacy of underdevelopment but is actively reproduced by regulatory structures "
        "that make formalisation costly. Historical fragmentation across 40-plus labour Acts incentivised small "
        "firms to avoid compliance thresholds; the 2019–20 Labour Codes consolidate these but face uneven "
        "state-level implementation. The consequences are severe: the informal sector employs 90% of workers "
        "but produces less than 50% of GDP, reflecting a deep productivity misallocation. Informal workers "
        "lack access to formal credit and social protection — ESI and EPF cover formal employees only. "
        "The author prescribes dual reform: lowering formalisation costs for enterprises and extending "
        "portable social protection, citing the e-Shram portal as an initial step toward the latter goal."
    ),
    "conclusion_text": "[Word count: 141]",
    "keywords": {
        "intro": [
            kw("informality", ["informality", "informal labour", "informal economy"], weight=2),
        ],
        "body": [
            kw("informal economy", ["informal economy", "informal sector", "informal workforce"], weight=2),
            kw("Labour Codes", ["labour codes", "2019-20 Labour Codes", "four labour codes"], weight=2),
            kw("formalisation", ["formalisation", "formalization", "formal sector transition"], weight=2),
            kw("productivity gap", ["productivity gap", "productivity misallocation", "GDP gap"], weight=1),
            kw("social protection", ["social protection", "ESI", "EPF", "social security"], weight=1),
            kw("e-Shram", ["e-Shram", "e-shram portal", "portable social protection"], weight=1),
        ],
        "conclusion": [
            kw("word count", ["word count", "[word count"], weight=2),
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# READING COMPREHENSION
# ══════════════════════════════════════════════════════════════════════════════

RC_002 = {
    "question_id": "eng_rc_002",
    "type_id": "rc",
    "source_exam": "rbi_depr_2024",
    "difficulty": "medium",
    "marks": 10,
    "word_guide_json": json.dumps({"intro": 50, "body": 80, "conclusion": 30}),
    "section_weights_json": json.dumps({"intro": 0.25, "body": 0.60, "conclusion": 0.15}),
    "prompt_text": (
        "Read the following passage and answer the question.\n\n"
        "---\n\n"
        "The Insolvency and Bankruptcy Code, enacted in 2016, introduced a time-bound, "
        "creditor-led resolution mechanism to replace India's fragmented and ineffective "
        "pre-existing insolvency framework. The Code's Corporate Insolvency Resolution Process "
        "(CIRP) gives creditors — primarily banks and financial institutions — control over the "
        "resolution of stressed companies within a statutory timeline of 180 days, extendable "
        "to 270 days in exceptional circumstances. A resolution professional appointed by the "
        "National Company Law Tribunal (NCLT) manages the debtor's operations during the process, "
        "and the committee of creditors votes on resolution plans submitted by potential acquirers.\n\n"
        "The Code's operational record has been mixed. By 2024, over 6,000 CIRPs had been admitted, "
        "with approximately 950 cases resolved through approved resolution plans and over 2,000 "
        "ordered for liquidation. The average time taken to resolve cases has exceeded the statutory "
        "limit significantly — the mean time for resolved cases was over 650 days by 2024, nearly "
        "2.5 times the intended 270-day outer limit. Legal challenges, adjudicating authority "
        "capacity constraints, and complex multi-party negotiations have collectively prevented "
        "the Code from achieving its time-bound objective. Creditors have recovered an average of "
        "approximately 32% of admitted claims in resolved cases — a recovery rate that, while "
        "substantially better than pre-IBC liquidation outcomes, falls far short of international "
        "benchmarks of 60–80% recovery in mature insolvency systems.\n\n"
        "---\n\n"
        "**Question:** According to the passage, what has been the primary operational shortcoming "
        "of the Insolvency and Bankruptcy Code, and what factors does the author identify as contributing to it?"
    ),
    "intro_text": (
        "The primary operational shortcoming identified by the author is the failure to resolve cases "
        "within the statutory timeline: the mean resolution time of over 650 days has significantly "
        "exceeded the 270-day outer limit mandated by the Code."
    ),
    "body_text": (
        "According to the passage, three factors have contributed to this delay: legal challenges "
        "to resolution proceedings, capacity constraints in the National Company Law Tribunal (NCLT) "
        "as the adjudicating authority, and the complexity of multi-party negotiations within the "
        "committee of creditors. The author notes that only approximately 950 of over 6,000 admitted "
        "cases were resolved through approved resolution plans, with over 2,000 ordered for liquidation — "
        "an outcome suggesting systemic difficulty in achieving going-concern resolutions."
    ),
    "conclusion_text": (
        "The time overrun therefore undermines the Code's core design principle of time-bound "
        "resolution, reducing creditor confidence and asset preservation."
    ),
    "keywords": {
        "intro": [
            kw("timeline exceeded", ["timeline exceeded", "statutory limit", "270 days", "time limit", "delay", "650 days"], weight=2),
            kw("operational shortcoming", ["operational shortcoming", "primary shortcoming", "failure to resolve"], weight=1),
        ],
        "body": [
            kw("legal challenges", ["legal challenges", "legal disputes", "litigation"], weight=2),
            kw("NCLT capacity", ["NCLT", "adjudicating authority", "capacity constraints", "capacity"], weight=2),
            kw("multi-party negotiations", ["multi-party", "complex negotiations", "committee of creditors"], weight=1),
        ],
        "conclusion": [
            kw("creditor confidence", ["creditor confidence", "time-bound", "asset preservation", "going concern"], weight=1),
        ],
    },
}

RC_003 = {
    "question_id": "eng_rc_003",
    "type_id": "rc",
    "source_exam": "ies_2023",
    "difficulty": "easy",
    "marks": 10,
    "word_guide_json": json.dumps({"intro": 50, "body": 80, "conclusion": 30}),
    "section_weights_json": json.dumps({"intro": 0.25, "body": 0.60, "conclusion": 0.15}),
    "prompt_text": (
        "Read the following passage and answer the question.\n\n"
        "---\n\n"
        "India is often described as possessing a demographic dividend — the economic growth potential "
        "that arises when the working-age population (15–64 years) is large relative to dependants. "
        "India's working-age population is projected to grow by approximately 9 million per year through "
        "2040, while most advanced economies and China face ageing-induced labour force contraction. "
        "This structural advantage creates a window of opportunity, but the dividend is neither "
        "automatic nor permanent.\n\n"
        "Realising the dividend requires two simultaneous conditions. First, sufficient productive "
        "employment must be created to absorb the growing labour force — employment that offers wages "
        "above subsistence, skill development pathways, and social protection. India's record on "
        "formal job creation has been disappointing: the Periodic Labour Force Survey consistently "
        "reports that the overwhelming majority of new employment is informal, low-wage, and "
        "concentrated in agriculture and construction. Second, the human capital of the entering "
        "workforce must be adequate for productive employment in a modern economy. India's learning "
        "outcomes at the school level — measured by ASER surveys — reveal that significant shares of "
        "students completing primary education cannot read a simple sentence or perform basic arithmetic. "
        "A workforce with inadequate foundational skills cannot be productively employed in manufacturing, "
        "services, or technology sectors that drive high-income growth.\n\n"
        "---\n\n"
        "**Question:** What two conditions does the passage identify as necessary for India to "
        "realise its demographic dividend?"
    ),
    "intro_text": (
        "The passage identifies two necessary conditions: the creation of sufficient productive formal employment "
        "to absorb the growing labour force, and adequate human capital development to ensure that "
        "entering workers possess foundational skills for modern economy jobs."
    ),
    "body_text": (
        "According to the author, productive employment must provide wages above subsistence, skill development "
        "pathways, and social protection — conditions that current informal job creation in agriculture and "
        "construction fails to meet. On human capital, the author cites ASER survey evidence showing "
        "that large shares of primary school completers cannot read or perform basic arithmetic, "
        "rendering them unsuitable for manufacturing, services, or technology employment that "
        "generates high-income growth."
    ),
    "conclusion_text": (
        "The author therefore implies that without simultaneous progress on both employment quality "
        "and learning outcomes, India's demographic window will close unrealised."
    ),
    "keywords": {
        "intro": [
            kw("productive employment", ["productive employment", "formal employment", "productive jobs", "sufficient employment"], weight=2),
            kw("human capital", ["human capital", "skill development", "foundational skills", "education"], weight=2),
        ],
        "body": [
            kw("informal employment", ["informal employment", "informal jobs", "informal"], weight=2),
            kw("ASER", ["ASER", "ASER survey", "learning outcomes", "foundational learning"], weight=2),
            kw("social protection", ["social protection", "wages above subsistence"], weight=1),
        ],
        "conclusion": [
            kw("demographic window", ["demographic window", "window of opportunity", "unrealised", "dividend"], weight=1),
        ],
    },
}

RC_004 = {
    "question_id": "eng_rc_004",
    "type_id": "rc",
    "source_exam": "upsc_2024",
    "difficulty": "medium",
    "marks": 10,
    "word_guide_json": json.dumps({"intro": 50, "body": 80, "conclusion": 30}),
    "section_weights_json": json.dumps({"intro": 0.25, "body": 0.60, "conclusion": 0.15}),
    "prompt_text": (
        "Read the following passage and answer the question.\n\n"
        "---\n\n"
        "The Goods and Services Tax, introduced in July 2017, constitutes the most significant "
        "indirect tax reform in India since independence. By subsuming over a dozen central and "
        "state taxes into a unified framework with a common base, it eliminated cascading tax-on-tax "
        "effects, created a national market for goods and services, and improved compliance through "
        "the invoice-matching mechanism of the GST Network (GSTN). The GST Council — a constitutional "
        "body comprising the Union Finance Minister and state Finance Ministers — governs rate and "
        "policy decisions by consensus, representing an experiment in cooperative fiscal federalism "
        "without precedent in India's constitutional history.\n\n"
        "However, the design embeds a structural tension in Centre-state fiscal relations. "
        "States surrendered their independent power to levy sales taxes — their largest own-tax revenue "
        "source — in exchange for a constitutionally guaranteed compensation mechanism for five years "
        "(July 2017 to June 2022). When GST revenue underperformed relative to the 14% projected growth "
        "rate during 2019–22, particularly due to the pandemic-induced collapse in consumption, "
        "the Centre's obligation to compensate states became a source of significant fiscal and "
        "political conflict. Several states accused the Centre of delayed compensation payments "
        "and contested the borrowing arrangements proposed as an alternative. "
        "The expiry of the compensation mechanism in June 2022 has left states structurally more "
        "dependent on central transfers and less fiscally autonomous than before GST's introduction.\n\n"
        "---\n\n"
        "**Question:** What is the primary structural tension in Centre-state fiscal relations embedded "
        "in the GST framework, according to the passage?"
    ),
    "intro_text": (
        "The primary structural tension identified by the author is that states surrendered their "
        "largest source of own-tax revenue — the power to levy independent sales taxes — in exchange "
        "for a compensation mechanism that was temporary and has now expired, leaving them "
        "fiscally less autonomous than before GST."
    ),
    "body_text": (
        "According to the passage, this tension became acute during 2019–22 when GST revenue "
        "underperformed the projected 14% growth rate, triggering disputes over delayed compensation "
        "payments and the Centre's proposed borrowing alternatives. The expiry of the compensation "
        "mechanism in June 2022 has made states structurally more dependent on central transfers, "
        "compounding the loss of fiscal autonomy that resulted from surrendering their independent "
        "sales tax powers."
    ),
    "conclusion_text": (
        "The author therefore implies that cooperative fiscal federalism through the GST Council "
        "coexists with a structural asymmetry that favours Centre over states in revenue sharing."
    ),
    "keywords": {
        "intro": [
            kw("surrendered sales tax", ["surrendered", "sales tax", "own-tax revenue", "tax autonomy", "independent taxing power"], weight=2),
            kw("compensation mechanism", ["compensation mechanism", "compensation guarantee", "five year compensation"], weight=2),
        ],
        "body": [
            kw("14% projected growth", ["14%", "14 percent", "projected growth rate", "revenue shortfall"], weight=1),
            kw("delayed compensation", ["delayed compensation", "compensation dispute", "borrowing arrangement"], weight=2),
            kw("fiscal autonomy", ["fiscal autonomy", "fiscal dependence", "central transfers"], weight=2),
        ],
        "conclusion": [
            kw("cooperative federalism", ["cooperative federalism", "fiscal federalism", "structural asymmetry"], weight=1),
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# LETTERS
# ══════════════════════════════════════════════════════════════════════════════

LETTER_001 = {
    "question_id": "eng_letter_001",
    "type_id": "letter",
    "source_exam": "rbi_depr_2024",
    "difficulty": "medium",
    "marks": 20,
    "word_guide_json": json.dumps({"intro": 70, "body": 140, "conclusion": 50}),
    "word_count_target": 250,
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "You are a Senior Economist at the Indian Economic Policy Research Institute, New Delhi. "
        "Write a formal letter to the Governor, Reserve Bank of India, recommending two specific "
        "measures to improve monetary policy transmission in India.\n"
        "(RBI Grade B DEPR / IES Economic Service — ~250 words)"
    ),
    "intro_text": (
        "Indian Economic Policy Research Institute\n"
        "New Delhi — 110 001\n"
        "6 June 2026\n\n"
        "The Governor\n"
        "Reserve Bank of India\n"
        "Mumbai — 400 001\n\n"
        "Subject: Recommendations to Strengthen Monetary Policy Transmission in India\n\n"
        "Dear Sir/Madam,\n\n"
        "I write to draw your attention to the structural impediments limiting the effectiveness "
        "of monetary policy transmission in India and to recommend two measures that could meaningfully "
        "address them."
    ),
    "body_text": (
        "First, I respectfully recommend accelerating the migration of bank loan pricing from "
        "internal benchmarks to external benchmarks linked to the repo rate or Treasury bill yields. "
        "Despite the RBI's 2019 mandate requiring all new floating-rate retail and MSME loans to be "
        "linked to external benchmarks, a significant share of the corporate loan book remains priced "
        "at marginal cost of funds-based rates (MCLR) or older base rates, insulating large borrowers "
        "from policy rate movements. Extending external benchmark linkage mandatorily to all new "
        "corporate loans above a defined threshold would transmit rate changes more completely to "
        "the broad economy.\n\n"
        "Second, I recommend targeted measures to reduce the structural excess liquidity in the banking "
        "system that has caused the overnight rate to persistently trade below the repo rate. "
        "When banks hold surplus cash that they park in the SDF rather than lending it, the effective "
        "floor for market rates falls below the intended policy signal. A more active use of "
        "open market operations to absorb surplus liquidity — combined with clear communication "
        "of the intended operating target — would narrow the repo-market rate corridor and "
        "improve the fidelity of monetary signal transmission."
    ),
    "conclusion_text": (
        "These measures would enhance the RBI's operational effectiveness without requiring legislative "
        "change. I trust that the above recommendations merit consideration in the Bank's ongoing "
        "monetary policy framework review.\n\n"
        "Yours faithfully,\n"
        "(Signature)\n"
        "Senior Economist\n"
        "Indian Economic Policy Research Institute"
    ),
    "keywords": {
        "intro": [
            kw("subject line", ["subject:", "subject line", "recommendations", "monetary policy transmission"], weight=2),
            kw("salutation", ["dear sir", "dear madam", "governor"], weight=1),
        ],
        "body": [
            kw("external benchmark", ["external benchmark", "repo rate linked", "MCLR", "benchmark lending rate"], weight=2),
            kw("monetary policy transmission", ["monetary policy transmission", "rate transmission", "policy transmission"], weight=2),
            kw("excess liquidity", ["excess liquidity", "surplus liquidity", "SDF", "overnight rate"], weight=2),
            kw("open market operations", ["open market operations", "OMO", "liquidity absorption"], weight=1),
        ],
        "conclusion": [
            kw("yours faithfully", ["yours faithfully", "yours sincerely"], weight=2),
            kw("designation", ["senior economist", "designation", "signature"], weight=1),
        ],
    },
}

LETTER_002 = {
    "question_id": "eng_letter_002",
    "type_id": "letter",
    "source_exam": "ies_2024",
    "difficulty": "medium",
    "marks": 20,
    "word_guide_json": json.dumps({"intro": 70, "body": 140, "conclusion": 50}),
    "word_count_target": 250,
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "You are the Finance Secretary of a major Indian state. Write a formal letter to "
        "the Chairperson, 16th Finance Commission, expressing your state's concerns about "
        "the vertical devolution formula and recommending an increase in the states' share "
        "of the divisible pool.\n"
        "(IES Economic Service — ~250 words)"
    ),
    "intro_text": (
        "Office of the Finance Secretary\n"
        "Government of [State]\n"
        "State Capital — [PIN]\n"
        "6 June 2026\n\n"
        "Dr Arvind Panagariya\n"
        "Chairperson, 16th Finance Commission\n"
        "New Delhi — 110 001\n\n"
        "Subject: Recommendations on Vertical Devolution and States' Share in the Divisible Pool\n\n"
        "Dear Sir,\n\n"
        "I write on behalf of the Government of [State] to place before the Commission our concerns "
        "regarding the adequacy of the current 41% share of states in the central divisible pool "
        "and to recommend its upward revision."
    ),
    "body_text": (
        "States bear the primary constitutional responsibility for delivering social and physical "
        "infrastructure — health, education, roads, water supply, and rural employment programmes. "
        "Concurrent list subjects in practice impose expenditure mandates on states that are largely "
        "unfunded by the Centre. The introduction of GST in 2017 further constrained state fiscal "
        "autonomy by replacing variable-yield state taxes with a pooled revenue stream subject to "
        "GST Council consensus. With the expiry of the GST compensation mechanism in June 2022, "
        "states have lost a significant revenue buffer precisely when post-pandemic expenditure "
        "pressures on health and welfare remain elevated.\n\n"
        "We respectfully submit that the states' share in the divisible pool should be enhanced "
        "from the current 41% — unchanged since the 15th Finance Commission — to at least 44%. "
        "Additionally, the horizontal distribution formula should assign greater weight to the "
        "income-distance criterion to compensate states that have made demographic investments "
        "in fertility reduction and human capital, which the current tax-effort criterion "
        "inadequately recognises."
    ),
    "conclusion_text": (
        "We are confident the Commission will give these representations full consideration in "
        "designing a devolution framework that strengthens both allocative efficiency and "
        "sub-national fiscal capacity.\n\n"
        "Yours faithfully,\n"
        "(Signature)\n"
        "Finance Secretary\n"
        "Government of [State]"
    ),
    "keywords": {
        "intro": [
            kw("subject line", ["subject:", "vertical devolution", "divisible pool"], weight=2),
            kw("16th Finance Commission", ["16th Finance Commission", "Finance Commission"], weight=1),
        ],
        "body": [
            kw("divisible pool", ["divisible pool", "states share", "41%", "devolution"], weight=2),
            kw("GST compensation", ["GST compensation", "compensation mechanism", "GST autonomy"], weight=2),
            kw("fiscal autonomy", ["fiscal autonomy", "state fiscal", "expenditure mandate"], weight=1),
            kw("income-distance criterion", ["income distance", "income-distance", "horizontal distribution", "demographic dividend"], weight=1),
        ],
        "conclusion": [
            kw("yours faithfully", ["yours faithfully", "yours sincerely"], weight=2),
            kw("designation", ["finance secretary", "government of"], weight=1),
        ],
    },
}

LETTER_003 = {
    "question_id": "eng_letter_003",
    "type_id": "letter",
    "source_exam": "rbi_depr_2025",
    "difficulty": "easy",
    "marks": 20,
    "word_guide_json": json.dumps({"intro": 70, "body": 140, "conclusion": 50}),
    "word_count_target": 250,
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "You are the Executive Director of a micro-enterprise development foundation. "
        "Write a formal letter to the Secretary, Department of Financial Services, "
        "Ministry of Finance, recommending reforms to Priority Sector Lending (PSL) "
        "guidelines to improve formal credit access for micro and small enterprises.\n"
        "(RBI Grade B DEPR — ~250 words)"
    ),
    "intro_text": (
        "Micro Enterprise Development Foundation\n"
        "New Delhi — 110 003\n"
        "6 June 2026\n\n"
        "The Secretary\n"
        "Department of Financial Services\n"
        "Ministry of Finance, Government of India\n"
        "New Delhi — 110 001\n\n"
        "Subject: Recommendations for Reforming Priority Sector Lending Guidelines for Micro and Small Enterprises\n\n"
        "Dear Sir/Madam,\n\n"
        "I write to bring to your attention the persistent credit gap facing micro and small enterprises (MSEs) "
        "and to recommend targeted reforms to the Priority Sector Lending framework that could "
        "substantially improve formal credit access for this segment."
    ),
    "body_text": (
        "Despite micro and small enterprises comprising over 99% of India's MSME sector and "
        "employing more than 110 million workers, their share in scheduled commercial bank "
        "credit remains disproportionately low — concentrated in urban areas and accessible "
        "primarily to enterprises with formal accounting records and collateral. We recommend "
        "three reforms.\n\n"
        "First, the current PSL sub-target for micro enterprises (7.5% of Adjusted Net Bank Credit) "
        "should be raised to 10% and made separately reportable from the small enterprise sub-target "
        "to prevent cross-substitution. Second, RBI should formalise cash-flow-based lending norms "
        "for enterprises with six or more months of verifiable digital transaction history through "
        "UPI or GST, removing the collateral barrier for the smallest enterprises. Third, "
        "co-lending arrangements between scheduled banks and registered NBFC-MFIs should be "
        "incentivised through preferential PSL classification to leverage the latter's last-mile "
        "origination capacity in semi-urban and rural clusters."
    ),
    "conclusion_text": (
        "These reforms are administratively feasible within the existing regulatory framework "
        "and would meaningfully expand formal credit access without compromising prudential standards. "
        "I remain available to provide any additional data or analysis the Ministry may require.\n\n"
        "Yours faithfully,\n"
        "(Signature)\n"
        "Executive Director\n"
        "Micro Enterprise Development Foundation"
    ),
    "keywords": {
        "intro": [
            kw("subject line", ["subject:", "priority sector lending", "PSL", "micro enterprises"], weight=2),
            kw("credit gap", ["credit gap", "formal credit access", "credit access"], weight=1),
        ],
        "body": [
            kw("PSL sub-target", ["PSL sub-target", "7.5%", "adjusted net bank credit", "ANBC"], weight=2),
            kw("cash-flow-based lending", ["cash flow based lending", "cash-flow", "digital transaction history", "UPI-based"], weight=2),
            kw("co-lending", ["co-lending", "co lending", "NBFC-MFI", "last mile"], weight=1),
            kw("collateral barrier", ["collateral barrier", "collateral free", "without collateral"], weight=1),
        ],
        "conclusion": [
            kw("yours faithfully", ["yours faithfully", "yours sincerely"], weight=2),
            kw("designation", ["executive director", "foundation"], weight=1),
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════════════════════

REPORT_001 = {
    "question_id": "eng_report_001",
    "type_id": "report",
    "source_exam": "rbi_depr_2024",
    "difficulty": "hard",
    "marks": 20,
    "word_guide_json": json.dumps({"intro": 60, "body": 180, "conclusion": 80}),
    "word_count_target": 300,
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "You are a Research Officer in the Department of Economic and Policy Research (DEPR), "
        "Reserve Bank of India. Write a report to the Deputy Governor (Monetary Policy) on the "
        "key structural challenges to monetary policy transmission in India "
        "and recommend measures to address them.\n"
        "(RBI Grade B DEPR — ~300 words)"
    ),
    "intro_text": (
        "To      : Deputy Governor (Monetary Policy), Reserve Bank of India\n"
        "From    : Research Officer, Department of Economic and Policy Research\n"
        "Date    : 6 June 2026\n"
        "Subject : Structural Challenges to Monetary Policy Transmission in India\n\n"
        "1. OBJECTIVE\n"
        "This report examines the structural features of India's financial system that limit "
        "the speed and completeness of monetary policy transmission from the repo rate to "
        "lending and deposit rates across the economy."
    ),
    "body_text": (
        "2. KEY CHALLENGES\n\n"
        "(i) Incomplete external benchmark migration: Despite the 2019 mandate, a substantial "
        "portion of corporate lending remains priced at MCLR or older base-rate benchmarks, "
        "which adjust with a lag of 3–6 months or more. The effective repo-rate pass-through "
        "to the broad credit market is consequently incomplete and delayed.\n\n"
        "(ii) Structural excess liquidity: Persistent surplus liquidity in the banking system "
        "causes the weighted average call rate to trade closer to the SDF rate (floor) than "
        "the repo rate (policy signal), weakening the intended rate signal. The RBI's OMO "
        "absorption has been reactive rather than systematic.\n\n"
        "(iii) High NPA legacy: Banks with elevated NPA ratios face constrained capital "
        "and higher funding costs, reducing their capacity to cut lending rates even when "
        "the policy rate falls. Credit risk pricing embeds a floor that monetary easing "
        "cannot fully dislodge.\n\n"
        "(iv) Large informal sector: Approximately 90% of India's labour force and a "
        "substantial share of SME financing operate outside formal bank credit channels, "
        "remaining insulated from policy rate movements entirely.\n\n"
        "3. RECOMMENDATIONS\n"
        "(i) Mandate external benchmark linkage for all new corporate loans above ₹5 crore by Q1 FY28.\n"
        "(ii) Establish a systematic OMO programme to maintain system liquidity within a narrow "
        "band around the repo rate, reducing SDF-repo corridor variability.\n"
        "(iii) Accelerate PCA exit for compliant banks to restore full credit intermediation capacity."
    ),
    "conclusion_text": (
        "4. CONCLUSION\n"
        "Strengthening monetary policy transmission requires complementary action on benchmark "
        "migration, liquidity management, and bank balance sheet repair. "
        "The recommendations above are administratively feasible within the current regulatory "
        "framework and would materially improve the fidelity of monetary policy signalling "
        "to the real economy.\n\n"
        "Submitted for consideration.\n"
        "(Signature)\n"
        "Research Officer, DEPR"
    ),
    "keywords": {
        "intro": [
            kw("To/From header", ["to :", "from :", "deputy governor", "research officer"], weight=2),
            kw("objective section", ["objective", "1. objective", "examines"], weight=1),
        ],
        "body": [
            kw("MCLR", ["MCLR", "external benchmark", "base rate", "benchmark migration"], weight=2),
            kw("excess liquidity", ["excess liquidity", "surplus liquidity", "SDF rate", "call rate"], weight=2),
            kw("NPA", ["NPA", "non-performing assets", "bank capital", "credit risk"], weight=1),
            kw("informal sector", ["informal sector", "outside formal bank", "SME financing"], weight=1),
            kw("numbered findings", ["(i)", "(ii)", "(iii)"], weight=1),
        ],
        "conclusion": [
            kw("conclusion section", ["4. conclusion", "conclusion", "submitted"], weight=2),
            kw("signature", ["signature", "research officer", "DEPR"], weight=1),
        ],
    },
}

REPORT_002 = {
    "question_id": "eng_report_002",
    "type_id": "report",
    "source_exam": "ies_2024",
    "difficulty": "medium",
    "marks": 20,
    "word_guide_json": json.dumps({"intro": 60, "body": 180, "conclusion": 80}),
    "word_count_target": 300,
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "You are a Deputy Secretary in the Department of Economic Affairs, Ministry of Finance. "
        "Write a report to the Finance Secretary on the recent trends in India's current account "
        "deficit and its macroeconomic implications, with policy recommendations.\n"
        "(IES Economic Service — ~300 words)"
    ),
    "intro_text": (
        "To      : Finance Secretary, Department of Economic Affairs, Ministry of Finance\n"
        "From    : Deputy Secretary (External Sector Division)\n"
        "Date    : 6 June 2026\n"
        "Subject : Recent Trends in India's Current Account Deficit and Macroeconomic Implications\n\n"
        "1. OBJECTIVE\n"
        "This report examines the widening of India's current account deficit (CAD) in FY2024–25, "
        "its principal drivers, and the macroeconomic implications for exchange rate stability "
        "and reserve adequacy."
    ),
    "body_text": (
        "2. FINDINGS\n\n"
        "(i) India's CAD widened to approximately 1.1% of GDP in Q2 FY2025–26, from a near-balanced "
        "position in FY2023–24, driven primarily by a widening goods trade deficit.\n"
        "(ii) The merchandise trade deficit was ₹8.5 lakh crore in H1 FY2025–26, with crude oil "
        "and gold imports (₹3.4 lakh crore combined) accounting for 40% of the import bill. "
        "Electronics imports have also grown sharply, reflecting strong domestic demand and "
        "an import-intensive consumer durables sector.\n"
        "(iii) Services exports (particularly IT and financial services) continue to generate "
        "a substantial surplus — approximately $150 billion annually — which partially offsets "
        "the goods deficit. Private remittances, at approximately $120 billion in FY25, "
        "provide a further stable offset.\n"
        "(iv) Foreign exchange reserves stand at approximately $675 billion (May 2026), "
        "providing import cover of approximately 11 months — adequate by international standards.\n\n"
        "3. ANALYSIS\n"
        "The current widening is cyclical rather than structural and is unlikely to breach 2% of GDP "
        "in the near term. However, a sustained crude price spike above $100/barrel or a "
        "global risk-off episode reducing capital inflows could create financing pressure "
        "on the rupee."
    ),
    "conclusion_text": (
        "4. RECOMMENDATIONS\n"
        "(i) Maintain the PLI scheme's focus on electronics and green technology exports to "
        "structurally diversify the export basket.\n"
        "(ii) Monitor gold import volumes and consider targeted duty calibration if the "
        "CAD trajectory worsens.\n"
        "(iii) Maintain adequate forex reserve buffer to manage tail-risk capital flow episodes.\n\n"
        "Submitted for consideration.\n"
        "(Signature)\n"
        "Deputy Secretary (External Sector Division)"
    ),
    "keywords": {
        "intro": [
            kw("To/From header", ["to :", "from :", "finance secretary", "deputy secretary"], weight=2),
            kw("current account deficit", ["current account deficit", "CAD", "external sector"], weight=1),
        ],
        "body": [
            kw("goods trade deficit", ["goods trade deficit", "merchandise trade deficit", "trade deficit"], weight=2),
            kw("crude oil imports", ["crude oil", "oil imports", "petroleum imports"], weight=2),
            kw("services exports", ["services exports", "IT exports", "service surplus"], weight=1),
            kw("remittances", ["remittances", "private remittances", "inward remittances"], weight=1),
            kw("forex reserves", ["forex reserves", "foreign exchange reserves", "$675 billion", "import cover"], weight=1),
        ],
        "conclusion": [
            kw("PLI scheme", ["PLI scheme", "PLI", "production linked incentive", "export diversification"], weight=1),
            kw("recommendations section", ["recommendations", "4. recommendations"], weight=2),
            kw("signature", ["submitted", "deputy secretary", "signature"], weight=1),
        ],
    },
}

REPORT_003 = {
    "question_id": "eng_report_003",
    "type_id": "report",
    "source_exam": "rbi_depr_2025",
    "difficulty": "easy",
    "marks": 20,
    "word_guide_json": json.dumps({"intro": 60, "body": 180, "conclusion": 80}),
    "word_count_target": 300,
    "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
    "prompt_text": (
        "You are a Senior Development Manager at NABARD. Write a report to the Chairman, NABARD "
        "on the status of financial inclusion in rural India and recommend measures to bridge "
        "the rural credit gap, with particular reference to agricultural and allied sector financing.\n"
        "(RBI Grade B DEPR — ~300 words)"
    ),
    "intro_text": (
        "To      : Chairman, National Bank for Agriculture and Rural Development (NABARD)\n"
        "From    : Senior Development Manager, Rural Credit Division\n"
        "Date    : 6 June 2026\n"
        "Subject : Financial Inclusion Status in Rural India and Measures to Bridge the Credit Gap\n\n"
        "1. OBJECTIVE\n"
        "This report assesses the current state of financial inclusion in rural India, identifies "
        "structural barriers to agricultural and allied sector credit, and recommends targeted "
        "measures to bridge the rural credit gap."
    ),
    "body_text": (
        "2. CURRENT STATUS\n\n"
        "(i) Despite progress in account ownership under PMJDY (over 500 million accounts), "
        "rural credit penetration remains low: only 14% of rural households report access to "
        "formal agricultural credit, against a stated PSL agricultural target of 18% of ANBC.\n"
        "(ii) The rural credit gap is concentrated among: small and marginal farmers (SMFs) "
        "with landholdings below 2 hectares; tenant farmers and sharecroppers lacking formal "
        "land title; and allied sector enterprises (dairy, fisheries, poultry) with limited "
        "collateral.\n"
        "(iii) Microfinance penetration through SHGs and JLGs has improved, but average loan "
        "sizes (₹25,000–50,000) are insufficient for productive investment in mechanisation "
        "or input purchase at scale.\n\n"
        "3. KEY BARRIERS\n"
        "Collateral requirements, inadequate rural branch density, and weak credit history for "
        "informal farmers prevent formal lenders from extending credit at acceptable risk levels. "
        "Climate risk — increasingly severe rainfall variability — raises agricultural credit "
        "risk, making banks more conservative in rural lending."
    ),
    "conclusion_text": (
        "4. RECOMMENDATIONS\n"
        "(i) Expand Kisan Credit Card (KCC) coverage to tenant farmers using revenue records "
        "and crop inspection certificates as surrogate collateral.\n"
        "(ii) Scale NABARD's Rural Infrastructure Development Fund disbursement toward cold "
        "chain and rural market infrastructure to reduce post-harvest losses and improve "
        "farmer creditworthiness.\n"
        "(iii) Integrate digital crop monitoring data from PM-FASAL into credit assessment "
        "models to price agricultural credit risk more accurately and reduce lender conservatism.\n\n"
        "Submitted for consideration.\n"
        "(Signature)\n"
        "Senior Development Manager, Rural Credit Division, NABARD"
    ),
    "keywords": {
        "intro": [
            kw("NABARD header", ["NABARD", "chairman", "senior development manager"], weight=2),
            kw("rural credit gap", ["rural credit gap", "financial inclusion", "rural India"], weight=1),
        ],
        "body": [
            kw("PMJDY", ["PMJDY", "Jan Dhan", "500 million accounts"], weight=1),
            kw("small and marginal farmers", ["small and marginal farmers", "SMF", "tenant farmers", "sharecroppers"], weight=2),
            kw("PSL agricultural target", ["PSL", "18% of ANBC", "agricultural target", "priority sector"], weight=2),
            kw("SHG", ["SHG", "self help group", "JLG", "microfinance"], weight=1),
            kw("climate risk", ["climate risk", "rainfall variability", "agricultural credit risk"], weight=1),
        ],
        "conclusion": [
            kw("Kisan Credit Card", ["KCC", "Kisan Credit Card", "tenant farmers"], weight=1),
            kw("RIDF", ["RIDF", "rural infrastructure development fund", "cold chain"], weight=1),
            kw("recommendations", ["4. recommendations", "recommendations", "submitted"], weight=2),
        ],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# ALL QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════

ALL_QUESTIONS = [
    ESSAY_003, ESSAY_004, ESSAY_005,
    PRECIS_002, PRECIS_003, PRECIS_004,
    RC_002, RC_003, RC_004,
    LETTER_001, LETTER_002, LETTER_003,
    REPORT_001, REPORT_002, REPORT_003,
]


def _ensure_tables(conn) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS english_question_types (
            type_id              TEXT NOT NULL,
            exam_id              TEXT NOT NULL DEFAULT 'english_practice',
            type_name            TEXT NOT NULL,
            description          TEXT,
            section_labels_json  TEXT,
            section_weights_json TEXT,
            rubric_type          TEXT,
            sort_order           INTEGER DEFAULT 0,
            PRIMARY KEY (type_id, exam_id)
        );
        CREATE TABLE IF NOT EXISTS english_questions (
            question_id          TEXT NOT NULL,
            exam_id              TEXT NOT NULL DEFAULT 'english_practice',
            type_id              TEXT NOT NULL,
            prompt_text          TEXT NOT NULL,
            marks                INTEGER,
            word_guide_json      TEXT,
            word_count_target    INTEGER,
            section_weights_json TEXT,
            intro_text           TEXT,
            body_text            TEXT,
            conclusion_text      TEXT,
            difficulty           TEXT DEFAULT 'medium',
            source_exam          TEXT,
            created_at           TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (question_id, exam_id)
        );
        CREATE TABLE IF NOT EXISTS english_keywords (
            keyword_id        TEXT NOT NULL,
            question_id       TEXT NOT NULL,
            exam_id           TEXT NOT NULL DEFAULT 'english_practice',
            section           TEXT NOT NULL CHECK(section IN ('intro','body','conclusion')),
            keyword           TEXT NOT NULL,
            variants_json     TEXT,
            weight            INTEGER DEFAULT 1,
            keyword_type      TEXT DEFAULT 'required'
                              CHECK(keyword_type IN ('required','bonus','negative','phrase')),
            fuzzy_threshold   REAL DEFAULT 0.82,
            penalty           REAL,
            PRIMARY KEY (keyword_id, exam_id)
        );
        CREATE TABLE IF NOT EXISTS english_attempts (
            attempt_id               TEXT NOT NULL,
            exam_id                  TEXT NOT NULL DEFAULT 'english_practice',
            user_id                  TEXT NOT NULL,
            question_id              TEXT NOT NULL,
            user_answer_intro        TEXT,
            user_answer_body         TEXT,
            user_answer_conclusion   TEXT,
            word_count_intro         INTEGER DEFAULT 0,
            word_count_body          INTEGER DEFAULT 0,
            word_count_conclusion    INTEGER DEFAULT 0,
            score_intro              REAL DEFAULT 0.0,
            score_body               REAL DEFAULT 0.0,
            score_conclusion         REAL DEFAULT 0.0,
            auto_score               REAL DEFAULT 0.0,
            self_assess_score        REAL DEFAULT 0.0,
            keywords_matched_json    TEXT,
            keywords_missed_json     TEXT,
            self_assess_json         TEXT,
            session_id               TEXT,
            created_at               TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (attempt_id, exam_id)
        );
        CREATE INDEX IF NOT EXISTS idx_english_attempts_user
            ON english_attempts(user_id, exam_id, created_at DESC);
    """)
    conn.commit()


def _seed_into(conn) -> tuple[int, int]:
    _ensure_tables(conn)
    inserted = 0
    skipped = 0
    for q in ALL_QUESTIONS:
        existing = conn.execute(
            "SELECT 1 FROM english_questions WHERE question_id=? AND exam_id=?",
            (q["question_id"], EXAM_ID),
        ).fetchone()
        if existing:
            print(f"  ~ skip {q['question_id']}")
            skipped += 1
            continue

        conn.execute(
            "INSERT INTO english_questions "
            "(question_id,exam_id,type_id,prompt_text,marks,word_guide_json,"
            "word_count_target,section_weights_json,intro_text,body_text,conclusion_text,"
            "difficulty,source_exam) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                q["question_id"], EXAM_ID, q["type_id"], q["prompt_text"],
                q.get("marks"), q.get("word_guide_json"), q.get("word_count_target"),
                q.get("section_weights_json"),
                q.get("intro_text"), q.get("body_text"), q.get("conclusion_text"),
                q.get("difficulty", "medium"), q.get("source_exam"),
            ),
        )

        for section, kw_list in q.get("keywords", {}).items():
            for kwd in kw_list:
                if not kwd.get("canonical"):
                    continue
                conn.execute(
                    "INSERT INTO english_keywords "
                    "(keyword_id,question_id,exam_id,section,keyword,variants_json,"
                    "weight,keyword_type,fuzzy_threshold,penalty) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        uuid.uuid4().hex[:12],
                        q["question_id"], EXAM_ID, section,
                        kwd["canonical"],
                        json.dumps(kwd.get("variants", [kwd["canonical"]])),
                        kwd.get("weight", 1),
                        kwd.get("keyword_type", "required"),
                        kwd.get("fuzzy_threshold", 0.82),
                        kwd.get("penalty"),
                    ),
                )

        conn.commit()
        print(f"  + {q['question_id']}  ({q['type_id']})")
        inserted += 1
    return inserted, skipped


def main():
    root = Path(__file__).parent.parent
    dbs = [root / "data" / "ies.db", root / "seeds" / "ies_seed.db"]
    for db_path in dbs:
        if not db_path.exists():
            print(f"  ! skipping {db_path.name} — not found")
            continue
        print(f"\n=== {db_path.name} ===")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            ins, skp = _seed_into(conn)
            print(f"  → {ins} inserted, {skp} skipped")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
