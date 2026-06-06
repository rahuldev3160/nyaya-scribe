"""
Seed initial English practice content into ies.db.
Run once: python3 scripts/seed_english_content.py
Idempotent — skips existing question_ids.
"""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "web"))
from db import get_conn

EXAM_ID = "english_practice"


def _kw(canonical, variants, weight=1, ktype="required", threshold=0.82, penalty=None):
    e = {"canonical": canonical, "variants": variants, "weight": weight,
         "keyword_type": ktype, "fuzzy_threshold": threshold}
    if penalty is not None:
        e["penalty"] = penalty
    return e


QUESTION_TYPES = [
    {
        "type_id": "essay",
        "type_name": "Essay",
        "description": "Extended analytical prose. Hook → Thesis → PEEL body → Counterargument → Conclusion.",
        "section_labels_json": json.dumps({"intro": "Introduction", "body": "Body", "conclusion": "Conclusion"}),
        "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
        "rubric_type": "essay",
        "sort_order": 1,
    },
    {
        "type_id": "précis",
        "type_name": "Précis",
        "description": "Compress a passage to 1/3 length. Title in Intro, précis text in Body. Third person, no lifted phrases.",
        "section_labels_json": json.dumps({"intro": "Title", "body": "Précis Text", "conclusion": "Word Count Declaration"}),
        "section_weights_json": json.dumps({"intro": 0.10, "body": 0.80, "conclusion": 0.10}),
        "rubric_type": "précis",
        "sort_order": 2,
    },
    {
        "type_id": "rc",
        "type_name": "Reading Comprehension",
        "description": "Answer a question based on the passage. Direct answer first. Passage content only — no external knowledge.",
        "section_labels_json": json.dumps({"intro": "Direct Answer", "body": "Supporting Evidence", "conclusion": "Implication / Inference"}),
        "section_weights_json": json.dumps({"intro": 0.25, "body": 0.60, "conclusion": 0.15}),
        "rubric_type": "rc",
        "sort_order": 3,
    },
]


QUESTIONS = [
    # ── ESSAY 1 ────────────────────────────────────────────────────────────────
    {
        "question_id": "eng_essay_001",
        "type_id": "essay",
        "prompt_text": (
            "Analyse the causes of India's current account deficit and suggest policy measures to contain it. "
            "(RBI Grade B / IES Economic Service — 550–600 words)"
        ),
        "marks": 40,
        "word_guide_json": json.dumps({"intro": 80, "body": 400, "conclusion": 80}),
        "word_count_target": None,
        "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
        "difficulty": "medium",
        "source_exam": "rbi_2024",
        "intro_text": (
            "India's current account deficit (CAD) reflects the gap between national savings and investment, "
            "manifesting as a net import of goods and services. Persistently elevated CAD weakens the rupee, "
            "depletes foreign exchange reserves, and signals structural imbalances in the economy. "
            "This essay examines the structural and cyclical drivers of India's CAD and proposes a multi-pronged policy response."
        ),
        "body_text": (
            "India's CAD is driven by three primary structural factors. First, the energy import bill remains the largest contributor — "
            "crude oil and petroleum products account for nearly one-third of total import value. Any upward spike in global oil prices "
            "directly widens the deficit. Second, gold imports, driven by cultural demand and inflation hedging, add 2–3% of GDP to import costs annually. "
            "The third driver is weak export competitiveness: India's merchandise exports remain concentrated in low-value-added segments "
            "(textiles, gems, leather), with limited diversification into electronics and machinery.\n\n"
            "Cyclically, a depreciating rupee exacerbates the CAD in the short run by raising import costs in rupee terms before export competitiveness gains materialise. "
            "The fiscal deficit also contributes through the twin deficit hypothesis: high government borrowing raises domestic interest rates, "
            "attracting foreign capital that appreciates the rupee and discourages exports.\n\n"
            "Policy measures must address both the demand and supply sides. On the import side, rationalising gold import duty, "
            "expanding domestic gold monetisation schemes, and accelerating the energy transition to reduce oil dependence are essential. "
            "On the export side, implementing the Production-Linked Incentive (PLI) scheme in high-potential sectors, improving trade facilitation through "
            "single-window clearances, and negotiating free trade agreements (FTAs) with the EU and UK can boost merchandise exports. "
            "Service exports — particularly IT, healthcare, and education — should be leveraged through liberalised visa regimes and digital infrastructure investment."
        ),
        "conclusion_text": (
            "India's current account deficit is structural in origin and requires sustained policy commitment beyond short-term exchange rate management. "
            "A combination of export diversification, energy transition, fiscal consolidation, and import compression can move India towards "
            "a more sustainable external balance position over the medium term."
        ),
        "keywords": {
            "intro": [
                _kw("current account deficit", ["current account deficit", "CAD", "external deficit"], weight=2),
                _kw("foreign exchange reserves", ["foreign exchange reserves", "forex reserves", "forex"], weight=1),
                _kw("structural imbalance", ["structural imbalance", "structural", "external imbalance"], weight=1),
            ],
            "body": [
                _kw("oil imports", ["oil imports", "crude oil", "petroleum imports", "energy imports"], weight=2),
                _kw("gold imports", ["gold imports", "gold demand", "gold import"], weight=2),
                _kw("export competitiveness", ["export competitiveness", "merchandise exports", "export diversification"], weight=2),
                _kw("twin deficit", ["twin deficit", "fiscal deficit", "fiscal-current account"], weight=1),
                _kw("rupee depreciation", ["rupee depreciation", "depreciating rupee", "exchange rate", "currency depreciation"], weight=1),
                _kw("PLI scheme", ["production linked incentive", "PLI scheme", "PLI"], weight=1, ktype="bonus"),
                _kw("free trade agreement", ["free trade agreement", "FTA"], weight=1, ktype="bonus"),
            ],
            "conclusion": [
                _kw("export diversification", ["export diversification", "diversification"], weight=1),
                _kw("fiscal consolidation", ["fiscal consolidation", "fiscal discipline"], weight=1),
                _kw("energy transition", ["energy transition", "renewable energy", "import compression"], weight=1),
            ],
        },
    },

    # ── ESSAY 2 ────────────────────────────────────────────────────────────────
    {
        "question_id": "eng_essay_002",
        "type_id": "essay",
        "prompt_text": (
            "Critically evaluate the effectiveness of India's flexible inflation targeting framework in achieving price stability. "
            "(RBI Grade B — 550–600 words)"
        ),
        "marks": 40,
        "word_guide_json": json.dumps({"intro": 80, "body": 400, "conclusion": 80}),
        "word_count_target": None,
        "section_weights_json": json.dumps({"intro": 0.15, "body": 0.70, "conclusion": 0.15}),
        "difficulty": "hard",
        "source_exam": "rbi_2023",
        "intro_text": (
            "India adopted the flexible inflation targeting (FIT) framework in 2016, establishing the Monetary Policy Committee (MPC) "
            "to target a 4% Consumer Price Index (CPI) inflation rate with a ±2% tolerance band. "
            "This framework represented a paradigm shift from multiple-indicator monetary policy to a rule-based, transparent system. "
            "This essay critically evaluates FIT's record on price stability and identifies its structural limitations."
        ),
        "body_text": (
            "FIT has yielded notable achievements. Between 2016 and 2020, inflation remained largely within the tolerance band, "
            "anchoring inflation expectations and reducing the long-run inflation premium in bond yields. "
            "The MPC's institutional credibility — with an independent composition and published voting records — enhanced policy transparency "
            "and improved the RBI's communication effectiveness.\n\n"
            "However, the framework has faced significant stress tests. Supply-side shocks, particularly food price volatility driven by "
            "erratic monsoons and global commodity price spikes, pushed headline CPI above the upper tolerance band of 6% in multiple quarters. "
            "Since monetary policy cannot address supply-side inflation — it cannot grow more vegetables or reduce global oil prices — "
            "FIT's effectiveness is inherently constrained by India's inflation architecture.\n\n"
            "A deeper structural challenge is the monetary policy transmission mechanism. The large informal sector, dominated by cash transactions, "
            "reduces the efficacy of interest rate signals. Banks' reluctance to pass on repo rate cuts fully — due to high non-performing assets (NPAs) "
            "and structural funding costs — creates a weak transmission channel. The growth-inflation tradeoff has also created MPC voting disagreements, "
            "revealing tension between price stability and supporting economic recovery, particularly post-pandemic.\n\n"
            "Complementary fiscal policy remains critical. Fiscal dominance — when large government borrowing needs crowd out private credit and create "
            "upward pressure on yields — can undermine the disinflationary intent of tight monetary policy. "
            "Without fiscal consolidation, monetary policy alone cannot fully achieve its price stability mandate."
        ),
        "conclusion_text": (
            "India's FIT framework has strengthened monetary policy credibility and anchored inflation expectations in normal conditions. "
            "However, supply-side inflation drivers, weak transmission mechanisms, and fiscal-monetary coordination gaps remain structural challenges. "
            "Complementary agricultural supply chain reforms, financial deepening, and coordinated fiscal consolidation are needed to enhance FIT's effectiveness."
        ),
        "keywords": {
            "intro": [
                _kw("flexible inflation targeting", ["flexible inflation targeting", "FIT", "inflation targeting framework"], weight=2),
                _kw("Monetary Policy Committee", ["MPC", "Monetary Policy Committee"], weight=2),
                _kw("CPI", ["CPI", "consumer price index", "headline inflation"], weight=1),
            ],
            "body": [
                _kw("inflation expectations", ["inflation expectations", "anchoring expectations", "anchor expectations"], weight=2),
                _kw("supply-side inflation", ["supply side inflation", "supply-side inflation", "food price inflation", "cost push"], weight=2),
                _kw("monetary transmission", ["monetary transmission", "transmission mechanism", "rate transmission", "pass through"], weight=2),
                _kw("non-performing assets", ["non performing assets", "NPAs", "NPA"], weight=1),
                _kw("growth-inflation tradeoff", ["growth inflation tradeoff", "tradeoff", "growth inflation"], weight=1),
                _kw("fiscal dominance", ["fiscal dominance", "government borrowing", "crowding out"], weight=1),
            ],
            "conclusion": [
                _kw("supply chain reforms", ["supply chain reform", "agricultural reform", "supply side reform"], weight=1),
                _kw("fiscal consolidation", ["fiscal consolidation", "fiscal discipline", "fiscal monetary"], weight=1),
                _kw("credibility", ["monetary credibility", "policy credibility", "credibility"], weight=1),
            ],
        },
    },

    # ── PRÉCIS 1 ───────────────────────────────────────────────────────────────
    {
        "question_id": "eng_precis_001",
        "type_id": "précis",
        "prompt_text": (
            "Read the following passage carefully and write a précis in approximately 170 words. "
            "Give your précis a suitable title.\n\n"
            "---\n\n"
            "Financial inclusion has emerged as a critical policy objective for developing economies, including India. "
            "The premise is straightforward: when individuals and small businesses have access to affordable financial services — "
            "savings accounts, credit, insurance, and payments — they can smooth consumption, invest in productive assets, and "
            "build resilience against economic shocks. Yet, despite the dramatic expansion of bank account ownership under the "
            "Pradhan Mantri Jan Dhan Yojana (PMJDY), which opened over 500 million accounts by 2023, the gap between account ownership "
            "and active financial participation remains alarming. Studies indicate that nearly 40% of Jan Dhan accounts remained "
            "dormant within two years of opening, suggesting that proximity to financial infrastructure alone is insufficient.\n\n"
            "The deeper barriers to financial inclusion are behavioural and structural. Low financial literacy prevents individuals "
            "from understanding product terms, recognising fraud, or making informed borrowing decisions. Informal employment means "
            "irregular income streams that are incompatible with the rigid repayment schedules of formal credit products. "
            "Women, who make up a disproportionate share of the financially excluded, face additional constraints: limited mobility, "
            "social norms restricting independent financial decision-making, and digital access gaps.\n\n"
            "Addressing these barriers requires a multi-pronged approach. Digital financial infrastructure — including mobile banking, "
            "UPI, and Aadhaar-linked payments — has dramatically lowered transaction costs and extended reach. "
            "But infrastructure must be complemented by demand-side interventions: financial literacy campaigns, simplified product design "
            "tailored to irregular income earners, and gender-responsive financial services. "
            "The objective is not merely to open accounts but to enable meaningful participation in the formal financial system — "
            "a distinction that policymakers must keep central to the financial inclusion agenda."
            "\n\n---\n\n"
            "*(Source passage: ~420 words. Your précis should be approximately 140 words. "
            "Write the title in your Introduction section and the précis text in your Body section. "
            "State your word count at the end of your Body.)*"
        ),
        "marks": 30,
        "word_guide_json": json.dumps({"intro": 10, "body": 140, "conclusion": 10}),
        "word_count_target": 140,
        "section_weights_json": json.dumps({"intro": 0.10, "body": 0.80, "conclusion": 0.10}),
        "difficulty": "medium",
        "source_exam": "upsc_2023",
        "intro_text": "Financial Inclusion: Beyond Account Ownership",
        "body_text": (
            "The author argues that financial inclusion, while a critical policy goal, requires more than expanding access to bank accounts. "
            "The PMJDY's success in opening 500 million accounts has not translated into active financial participation, "
            "with nearly 40% of accounts remaining dormant. "
            "The author identifies behavioural and structural barriers as the deeper impediments: low financial literacy, "
            "informal employment with irregular incomes incompatible with formal credit products, and gender-specific constraints "
            "limiting women's financial autonomy. "
            "The author contends that digital infrastructure — mobile banking, UPI, and Aadhaar-linked payments — has reduced transaction costs, "
            "but must be complemented by demand-side interventions including simplified product design, "
            "financial literacy campaigns, and gender-responsive services. "
            "The author concludes that meaningful financial inclusion requires enabling active participation in the formal financial system, "
            "not merely account creation."
        ),
        "conclusion_text": "[Word count: 140]",
        "keywords": {
            "intro": [
                _kw("financial inclusion", ["financial inclusion", "financial access", "financial exclusion"], weight=2),
            ],
            "body": [
                _kw("financial inclusion", ["financial inclusion"], weight=2),
                _kw("Jan Dhan", ["Jan Dhan", "PMJDY", "Jan Dhan Yojana", "account ownership"], weight=2),
                _kw("dormant accounts", ["dormant", "dormant accounts", "inactive accounts"], weight=2),
                _kw("financial literacy", ["financial literacy", "literacy"], weight=2),
                _kw("informal employment", ["informal employment", "irregular income", "irregular incomes"], weight=1),
                _kw("digital infrastructure", ["digital infrastructure", "UPI", "mobile banking", "aadhaar"], weight=1),
                _kw("gender", ["gender", "women", "gender responsive"], weight=1),
                _kw("third person", [], weight=0, ktype="negative", penalty=0.2),  # placeholder for third-person check
            ],
            "conclusion": [
                _kw("word count", ["word count", "[word count"], weight=2),
            ],
        },
    },

    # ── RC 1 ───────────────────────────────────────────────────────────────────
    {
        "question_id": "eng_rc_001",
        "type_id": "rc",
        "prompt_text": (
            "Read the following passage and answer the question.\n\n"
            "---\n\n"
            "The Reserve Bank of India's shift to the flexible inflation targeting framework in 2016 marked a decisive break "
            "from the era of multiple-indicator monetary policy. Under the new framework, the Monetary Policy Committee is "
            "mandated to maintain consumer price inflation at 4%, with a tolerance band of ±2 percentage points. "
            "Breaching the upper or lower bound for three consecutive quarters triggers a statutory obligation to explain "
            "the reasons and the corrective action plan to the central government. This accountability mechanism was "
            "deliberately designed to balance operational autonomy with democratic accountability — a tension that "
            "lies at the heart of central bank independence globally.\n\n"
            "Critics argue that the framework's singular focus on inflation creates a bias toward excessive tightening "
            "during supply shocks, which monetary policy is ill-equipped to resolve. When food prices surge due to an "
            "erratic monsoon or global oil prices spike due to geopolitical factors, raising interest rates penalises "
            "borrowers and dampens investment without addressing the supply-side source of inflation. "
            "Proponents counter that by anchoring inflation expectations, the framework prevents supply shocks from "
            "becoming entrenched inflation through second-round effects — a benefit that justifies the short-run growth cost."
            "\n\n---\n\n"
            "**Question:** What is the accountability mechanism built into India's flexible inflation targeting framework, "
            "and what tension does it seek to address?"
        ),
        "marks": 10,
        "word_guide_json": json.dumps({"intro": 50, "body": 80, "conclusion": 30}),
        "word_count_target": None,
        "section_weights_json": json.dumps({"intro": 0.25, "body": 0.60, "conclusion": 0.15}),
        "difficulty": "easy",
        "source_exam": "rbi_2024",
        "intro_text": (
            "The accountability mechanism requires the MPC to explain to the central government if CPI inflation breaches "
            "the ±2% tolerance band for three consecutive quarters, along with a corrective action plan."
        ),
        "body_text": (
            "According to the passage, this statutory obligation was deliberately designed to balance the RBI's operational autonomy "
            "with democratic accountability — a tension the author identifies as central to central bank independence globally. "
            "The MPC thus retains independence in day-to-day policy decisions but remains answerable to the government when "
            "inflation consistently falls outside the mandated range."
        ),
        "conclusion_text": (
            "The mechanism therefore resolves the classic tension between technocratic autonomy and political oversight in central banking."
        ),
        "keywords": {
            "intro": [
                _kw("breach tolerance band", ["breach", "breaching", "tolerance band", "±2", "upper band", "three consecutive quarters"], weight=2),
                _kw("explain corrective action", ["corrective action", "explain", "statutory obligation", "central government"], weight=2),
            ],
            "body": [
                _kw("operational autonomy", ["operational autonomy", "autonomy", "independence"], weight=2),
                _kw("democratic accountability", ["democratic accountability", "accountability", "answerable"], weight=2),
                _kw("central bank independence", ["central bank independence", "central bank"], weight=1),
            ],
            "conclusion": [
                _kw("autonomy and oversight", ["autonomy", "oversight", "technocratic", "political oversight", "tension"], weight=1),
            ],
        },
    },
]


def ensure_tables(conn) -> None:
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


def seed_into(conn) -> tuple[int, int]:
    ensure_tables(conn)
    inserted = 0
    skipped = 0

    for qt in QUESTION_TYPES:
        existing = conn.execute(
            "SELECT 1 FROM english_question_types WHERE type_id=? AND exam_id=?",
            (qt["type_id"], EXAM_ID)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO english_question_types "
                "(type_id,exam_id,type_name,description,section_labels_json,section_weights_json,rubric_type,sort_order) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (qt["type_id"], EXAM_ID, qt["type_name"], qt["description"],
                 qt["section_labels_json"], qt["section_weights_json"],
                 qt["rubric_type"], qt["sort_order"])
            )
    conn.commit()

    for q in QUESTIONS:
        existing = conn.execute(
            "SELECT 1 FROM english_questions WHERE question_id=? AND exam_id=?",
            (q["question_id"], EXAM_ID)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        conn.execute(
            "INSERT INTO english_questions "
            "(question_id,exam_id,type_id,prompt_text,marks,word_guide_json,"
            "word_count_target,section_weights_json,intro_text,body_text,conclusion_text,"
            "difficulty,source_exam) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (q["question_id"], EXAM_ID, q["type_id"], q["prompt_text"],
             q.get("marks"), q.get("word_guide_json"), q.get("word_count_target"),
             q.get("section_weights_json"), q.get("intro_text"),
             q.get("body_text"), q.get("conclusion_text"),
             q.get("difficulty", "medium"), q.get("source_exam"))
        )

        for section, kw_list in q.get("keywords", {}).items():
            for kw in kw_list:
                if not kw.get("canonical"):
                    continue
                conn.execute(
                    "INSERT INTO english_keywords "
                    "(keyword_id,question_id,exam_id,section,keyword,variants_json,"
                    "weight,keyword_type,fuzzy_threshold,penalty) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        uuid.uuid4().hex[:12],
                        q["question_id"], EXAM_ID, section,
                        kw["canonical"],
                        json.dumps(kw.get("variants", [kw["canonical"]])),
                        kw.get("weight", 1),
                        kw.get("keyword_type", "required"),
                        kw.get("fuzzy_threshold", 0.82),
                        kw.get("penalty"),
                    )
                )
        conn.commit()
        print(f"  + {q['question_id']}")
        inserted += 1

    return inserted, skipped


def main():
    import sqlite3 as _sqlite3
    root = Path(__file__).parent.parent
    for db_path in [root / "data" / "ies.db", root / "seeds" / "ies_seed.db"]:
        if not db_path.exists():
            print(f"  ! skipping {db_path.name} — not found")
            continue
        print(f"\n=== {db_path.name} ===")
        conn = _sqlite3.connect(db_path)
        conn.row_factory = _sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            ins, skp = seed_into(conn)
            print(f"  → {ins} inserted, {skp} skipped")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
