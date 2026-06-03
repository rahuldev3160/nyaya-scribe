"""
Generate ~355 RBI DEPR Phase 1 MCQs via Haiku Batch API.
Saves batch_id to data/rbi_mcq_batch.txt for safe restart.
Run: python3 scripts/rbi/02_generate_mcq_bank.py

Cost estimate: ~$0.20-0.50 (Haiku batch)
"""
import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

import anthropic

DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"
BATCH_ID_FILE = Path(__file__).parent.parent.parent / "data" / "rbi_mcq_batch.txt"
THEORY_SOURCE = Path(__file__).parent.parent.parent / "data" / "notebooklm" / "rbi_theory_mcq_source.md"

SYSTEM_PROMPT = """You are an expert question author for the RBI Grade B DEPR Phase 1 Economics MCQ exam.

Your task: generate high-quality MCQs that mirror the actual exam style.

EXAM STYLE:
- 4 options (A/B/C/D), exactly one correct
- Tests both definitional recall AND conceptual trap reasoning
- 2024 paper had questions like: "Mundell-Fleming with flexible ER + perfect capital mobility — effect of fiscal policy on output?"
- Trap questions are common: multicollinearity appeared TWICE in 2024 testing the same concept from different angles
- Numerical/calculation questions (Harrod-Domar g=s/v, OLS residuals, price discrimination) appear regularly

OUTPUT FORMAT — return ONLY a valid JSON array, no markdown, no explanation:
[
  {
    "id": "unique_id_here",
    "question": "full question text",
    "option_a": "...",
    "option_b": "...",
    "option_c": "...",
    "option_d": "...",
    "correct_option": "A",
    "explanation": "why correct + why each wrong option is wrong. Include the exam trap if present.",
    "subtopic": "specific concept tested",
    "dimension": "trap|application|definition|calculation|comparison|statement",
    "difficulty": "easy|medium|hard",
    "is_core_concept": 1,
    "is_trap": 1,
    "question_type": "standard|statement_based|scenario|calculation",
    "tags": ["tag1", "tag2"]
  }
]

RULES:
- dimension=trap: question exploits a known exam misconception (e.g., "multicollinearity causes bias" — wrong)
- dimension=calculation: requires a numeric computation (e.g., Harrod-Domar g = s/v = 20/2 = 10%)
- is_core_concept=1: tests a foundational mechanism, not a peripheral fact
- is_trap=1: the wrong options are plausible misconceptions, not obviously wrong
- explanation must say WHY the wrong options are wrong, not just what's right
- For statement_based: "Which of the following statements is/are correct?" with 2 true/false statements
- Hard questions: involve 2-step reasoning or numerical calculation
- Never generate trivially easy questions (direct single-fact recall) — minimum medium difficulty
- IDs must be unique: use format "{subject_code}_{topic_code}_{3-digit-seq}" e.g. "mac_islm_001"
"""


# Supplementary theory for topics not in rbi_theory_mcq_source.md
SUPPLEMENTARY = {
    "mundell_fleming": """
Mundell-Fleming Model (Open Economy IS-LM):
- IS curve: Y = C + I + G + NX. NX depends on exchange rate e (higher e = more exports).
- LM curve: M/P = L(Y,i) — same as closed economy.
- BP curve: BOP = 0 at combinations of Y and i, given capital mobility.
- Perfect capital mobility: BP is horizontal at world interest rate i*.

FIXED EXCHANGE RATE:
- Monetary policy: LM shifts right → i falls → capital outflow → ER pressure → RBI intervenes (buys foreign currency, sells domestic) → LM shifts back. Result: INEFFECTIVE.
- Fiscal policy: IS shifts right → i rises → capital inflow → ER pressure → RBI buys domestic currency → LM shifts right. Result: FULLY EFFECTIVE (crowding-in, not crowding-out).

FLEXIBLE EXCHANGE RATE:
- Monetary policy: LM shifts right → i falls → capital outflow → exchange rate depreciates → NX rises → IS shifts right. Result: FULLY EFFECTIVE.
- Fiscal policy: IS shifts right → i rises → capital inflow → exchange rate appreciates → NX falls → IS shifts back. Result: INEFFECTIVE (complete crowding out via exchange rate).

MCQ trap: Under FLEXIBLE ER + perfect capital mobility, fiscal policy is COMPLETELY crowded out by exchange rate appreciation. Under FIXED ER, monetary policy is completely ineffective.
The 2024 DEPR exam tested this twice: once for fixed ER fiscal policy, once for flexible ER fiscal policy.
""",
    "qtm_monetary": """
Quantity Theory of Money (QTM):
- Fisher equation: MV = PY (V = velocity of money, assumed constant in long run)
- Cambridge: M = kPY (k = proportion of income held as money = 1/V)
- Long-run QTM: Money supply growth = inflation (V and Y fixed in long run)
- Classical Dichotomy: nominal variables (money, price level) do not affect real variables (output, employment) in the long run.
- Money neutrality: a 10% increase in M → 10% increase in P, zero effect on Y or r in long run.

Taylor Rule:
- Policy rate = r* + π + 0.5(π - π*) + 0.5(Y - Y*)/Y*
- r* = neutral real rate, π* = inflation target, Y* = potential output
- Prescribes raising rates by MORE than 1-for-1 with inflation (Taylor principle)
- RBI's MPC broadly follows a Taylor-rule-type framework

Lucas Critique (1976):
- Policy evaluation using historical data is invalid because agents change behaviour in response to the policy itself.
- Implication: macroeconomic models must be built on deep structural parameters (preferences, technology), not reduced-form relationships.
- "If you change the policy rule, the expectations formation process changes too."
- Example: the Phillips curve broke down in the 1970s when policymakers tried to exploit it — agents anticipated inflation.

Money Multiplier:
- m = 1 / (rr + c×(1+c)) where rr = reserve ratio, c = currency-deposit ratio
- Simplified: m = 1/rr (if no currency holdings)
- RBI cut CRR: lower rr → higher multiplier → more money creation per unit of base money
- High-powered money (H) = Currency in circulation + Bank reserves with RBI

Monetary Aggregates (Y.V. Reddy Committee):
- M0 = Currency in circulation + Banker deposits with RBI + 'Other' deposits with RBI
- M1 = Currency with public + Demand deposits + 'Other' deposits with RBI
- M2 = M1 + Savings deposits of post office savings banks
- M3 = M1 + Time deposits of banks (BROAD MONEY — used most in RBI statements)
- M4 = M3 + All deposits of post office savings
- Liquidity aggregates: L1 = M3 + Post office deposits; L2 = L1 + Term deposits of NBFCs; L3 = L2 + Public deposits of NBFCs

MCQ trap: M3 is India's broad money measure, NOT M2. L1/L2/L3 are liquidity aggregates, broader than M-aggregates.
""",
    "mundell_fleming_bis": """Additional Mundell-Fleming facts:
- Named after Robert Mundell (Nobel 1999) and J. Marcus Fleming (IMF economist)
- Small open economy assumption: country faces a fixed world interest rate i*
- Under perfect capital mobility, domestic i = i* in equilibrium
- "Trilemma" (Mundell's Impossible Trinity): cannot simultaneously have (1) fixed ER, (2) free capital mobility, (3) independent monetary policy. Must give up one.
- India: chose managed float (not fully fixed) + capital controls (not full mobility) → retains some monetary independence
""",
    "trade_theories": """
Linder's Overlapping Demand Theory (1961):
- Countries with similar income levels trade MORE with each other (not less, as HO predicts).
- Why: rich countries develop products for domestic high-income consumers; these products appeal to similarly rich consumers abroad.
- Explains intra-industry trade between similar countries (e.g., Germany-France car trade).
- Contrast with HO: HO explains inter-industry trade (labour-intensive vs capital-intensive), Linder explains intra-industry trade.

New Trade Theory (Paul Krugman, 1980):
- Trade can occur even between identical countries (no factor endowment or technology differences).
- Reason: economies of scale + consumer love of variety (Dixit-Stiglitz preferences).
- Companies specialise to exploit increasing returns → become globally competitive.
- Policy implication: "Strategic trade policy" — government subsidies to domestic firms may create comparative advantage.
- Krugman won Nobel 2008 for this model.

McDougall Rule / Intra-Industry Trade Index (Grubel-Lloyd):
- IIT index = 1 - |Xi - Mi| / (Xi + Mi) for sector i
- Index = 1: pure intra-industry trade; Index = 0: pure inter-industry trade
- India's IIT index is relatively low for most sectors (resource/labour-intensive exports, capital-intensive imports)

MCQ trap: Linder's theory predicts more trade between SIMILAR income countries. HO predicts trade between DIFFERENT factor endowment countries. They explain different types of trade (intra-industry vs inter-industry).
""",
    "diagnostic_tests": """
Jarque-Bera Test:
- Tests whether OLS residuals are normally distributed (required for valid t and F tests)
- JB statistic = n/6 × (S² + K²/4) where S = skewness, K = excess kurtosis
- Under H₀ (normality): JB ~ χ²(2)
- If p-value < 0.05: reject normality → t and F test results are unreliable
- Note: Gauss-Markov does NOT require normality for BLUE. Normality is only needed for hypothesis testing (t, F, confidence intervals).

Ramsey RESET Test:
- Tests for functional form misspecification in OLS regression
- Adds fitted values (ŷ², ŷ³) as regressors and tests their joint significance via F-test
- If significant: functional form is wrong (e.g., should use log-linear or quadratic model)
- H₀: model is correctly specified (no omitted nonlinearities)

Durbin-Watson Test:
- Tests for first-order autocorrelation in OLS residuals: eₜ = ρeₜ₋₁ + vₜ
- DW ≈ 2: no autocorrelation. DW < dL: positive autocorrelation. DW > 4-dL: negative autocorrelation.
- Inconclusive zone: dL < DW < dU (or 4-dU < DW < 4-dL)
- Cannot be used for lagged dependent variable models (Durbin-h test used instead)

Chow Test:
- Tests for structural break (parameter stability across two sub-periods)
- Splits sample at break point, estimates 3 regressions, compares residual sum of squares

MCQ trap: Jarque-Bera rejects H₀ of normality when p < 0.05 (REJECT normality, not accept). Gauss-Markov BLUE does NOT need normality. The Durbin-Watson test is INVALID with lagged dependent variables.
""",
    "development_theory": """
Hirschman Unbalanced Growth Theory:
- Growth happens through deliberate imbalances, not balanced across all sectors.
- Create bottlenecks that force investment responses ("forward linkages" and "backward linkages").
- Forward linkage: an activity induces investment in downstream industries (e.g., steel → auto).
- Backward linkage: induces investment in upstream industries (e.g., auto → steel).
- Policy: invest in industries with maximum linkage effects.

Rostow's Stages of Growth:
1. Traditional Society
2. Preconditions for Take-off
3. Take-off (S ≥ 10%, dynamic industries emerge)
4. Drive to Maturity
5. Age of High Mass Consumption

Leibenstein's Critical Minimum Effort Thesis:
- Developing countries are in low-level equilibrium traps (per capita income stagnant).
- To escape, investment must exceed a "critical minimum" threshold.
- Below the threshold: population growth absorbs income gains → back to subsistence.
- Above the threshold: growth is self-sustaining (like Rostow's take-off).

Schumpeter's Creative Destruction:
- Economic development driven by entrepreneurs who introduce innovations.
- "Creative destruction": new products/methods destroy old ones, but generate growth.
- Clusters of innovation explain business cycles (Kondratieff long waves).
- Capitalism is inherently dynamic and unstable — but productively so.

Demographic Transition Theory:
- Stage 1: High birth rate, high death rate → stable low population
- Stage 2: High birth rate, falling death rate (improved health) → rapid population growth
- Stage 3: Falling birth rate, low death rate → slowing growth
- Stage 4: Low birth rate, low death rate → stable high population
- Most developing countries: Stage 2→3. India: late Stage 3.
- MCQ trap: Population explosion occurs in Stage 2 (not Stage 1 or 3).
""",
    "intra_industry": """
Intra-Industry Trade (IIT):
- Trade in similar/differentiated products in the same industry (e.g., Germany imports and exports cars).
- Grubel-Lloyd Index: GL_i = 1 - |Xi - Mi| / (Xi + Mi). Range 0-1. Higher = more IIT.
- Driven by: economies of scale, product differentiation, consumer preference for variety.
- Typical for: manufactured goods trade between similar-income countries.
- Contrasts with Heckscher-Ohlin inter-industry trade (wine vs cloth).

Exchange Rate Pressure Index (ERPI):
- Measures speculative pressure on a currency by combining exchange rate changes and reserve changes.
- High ERPI: either the exchange rate depreciated significantly OR central bank lost reserves defending it.
- India 2024: moderate ERPI due to RBI active forex intervention.

MCQ trap: Higher IIT index = more intra-industry trade (closer to 1 = symmetric trade). Lower = more specialised/inter-industry pattern.
""",
}


TOPIC_SPECS = [
    # (topic, subject, question_count, difficulty_mix, use_theory_source_sections)
    # Macro
    ("is_lm",          "macro",       18, {"easy":2,"medium":10,"hard":6}, [1]),
    ("qtm_monetary",   "macro",       16, {"easy":2,"medium":9,"hard":5}, [1]),
    ("phillips_lucas", "macro",       16, {"easy":2,"medium":10,"hard":4}, [1]),
    ("money_banking",  "macro",       15, {"easy":2,"medium":9,"hard":4}, [1]),
    # International
    ("mundell_fleming","intl_econ",   20, {"easy":2,"medium":10,"hard":8}, [4]),
    ("trade_theories", "intl_econ",   18, {"easy":2,"medium":10,"hard":6}, [4]),
    ("bop_exchange",   "intl_econ",   12, {"easy":2,"medium":7,"hard":3}, [4]),
    ("intra_industry", "intl_econ",   5,  {"easy":1,"medium":3,"hard":1}, [4]),
    # Indian Economy
    ("india_macro_data","indian_econ",15, {"easy":3,"medium":8,"hard":4}, []),
    ("rbi_monetary_data","indian_econ",10,{"easy":2,"medium":6,"hard":2}, []),
    ("schemes_indices","indian_econ", 10, {"easy":3,"medium":5,"hard":2}, []),
    # Growth
    ("classical_growth","growth",     18, {"easy":2,"medium":10,"hard":6}, [2]),
    ("development_theory","growth",   15, {"easy":2,"medium":9,"hard":4}, [2]),
    ("poverty_hdi",    "growth",      8,  {"easy":2,"medium":5,"hard":1}, [2]),
    # Micro
    ("consumer_theory","micro",       15, {"easy":2,"medium":9,"hard":4}, [3]),
    ("market_structures","micro",     15, {"easy":2,"medium":9,"hard":4}, [3]),
    ("welfare_game",   "micro",       10, {"easy":2,"medium":6,"hard":2}, [3]),
    ("production_theory","micro",     8,  {"easy":2,"medium":5,"hard":1}, [3]),
    # Quant
    ("ols_blue",       "quant",       12, {"easy":2,"medium":6,"hard":4}, [6]),
    ("diagnostic_tests","quant",      10, {"easy":1,"medium":6,"hard":3}, [6]),
    ("index_numbers",  "quant",       8,  {"easy":2,"medium":5,"hard":1}, [6]),
    # Public Finance
    ("public_expenditure","pub_finance",12,{"easy":2,"medium":7,"hard":3},[5]),
    ("fiscal_federalism","pub_finance",8, {"easy":2,"medium":5,"hard":1}, [5]),
    ("fiscal_data",    "pub_finance", 5,  {"easy":1,"medium":3,"hard":1}, [5]),
    # Environmental
    ("env_instruments","env_econ",    10, {"easy":2,"medium":6,"hard":2}, [7]),
    ("green_metrics",  "env_econ",    5,  {"easy":1,"medium":3,"hard":1}, [7]),
]

THEORY_SECTION_HEADERS = {
    1: "## 1. Macroeconomics",
    2: "## 2. Growth and Development",
    3: "## 3. Microeconomics",
    4: "## 4. International Economics",
    5: "## 5. Public Finance",
    6: "## 6. Quantitative Methods",
    7: "## 7. Environmental Economics",
}


def load_theory_sections(theory_text: str, section_nums: list[int]) -> str:
    if not section_nums:
        return ""
    lines = theory_text.split("\n")
    sections = []
    current_section = None
    current_num = None
    for line in lines:
        for num, header in THEORY_SECTION_HEADERS.items():
            if line.strip().startswith(header.strip()):
                if current_num in section_nums and current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
                current_num = num
                break
        else:
            if current_section is not None:
                current_section.append(line)
    if current_num in section_nums and current_section:
        sections.append("\n".join(current_section))
    return "\n\n".join(sections)


def build_user_prompt(topic: str, subject: str, count: int,
                      difficulty_mix: dict, theory_context: str) -> str:
    supplement = SUPPLEMENTARY.get(topic, "")
    # For mundell_fleming, also inject the _bis supplement
    if topic == "mundell_fleming":
        supplement += SUPPLEMENTARY.get("mundell_fleming_bis", "")

    context_block = ""
    if theory_context.strip():
        context_block = f"\n\n--- THEORY CONTEXT ---\n{theory_context}\n--- END CONTEXT ---\n"
    if supplement.strip():
        context_block += f"\n\n--- SUPPLEMENTARY CONTEXT ---\n{supplement}\n--- END SUPPLEMENTARY ---\n"

    difficulty_note = ", ".join(f"{v} {k}" for k, v in difficulty_mix.items() if v > 0)

    return f"""Generate exactly {count} MCQs for the RBI DEPR Phase 1 exam.

Topic: {topic} (subject: {subject})
Difficulty distribution: {difficulty_note}

Requirements:
1. Each question must test a DISTINCT concept or angle — no repetition
2. Include at least {max(1, count//4)} trap questions (is_trap=1, dimension=trap)
3. Include at least {max(1, count//5)} calculation questions if the topic supports it
4. Hard questions require 2-step reasoning or numerical computation
5. Use statement_based format for 20-30% of questions: "Which of the following is/are correct?"
6. All IDs must follow pattern: {subject[:3]}_{topic[:4]}_XXX (e.g. mac_islm_001)
7. Explanations must: (a) state why correct option is right, (b) explain why each wrong option is wrong
{context_block}
Return ONLY the JSON array. No prose before or after."""


def build_batch_requests(theory_text: str) -> list[dict]:
    requests = []
    for topic, subject, count, diff_mix, sections in TOPIC_SPECS:
        ctx = load_theory_sections(theory_text, sections)
        user_prompt = build_user_prompt(topic, subject, count, diff_mix, ctx)
        requests.append({
            "custom_id": f"{subject}__{topic}",
            "params": {
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 8192,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        })
    print(f"Built {len(requests)} batch requests")
    return requests


def submit_batch(client: anthropic.Anthropic, requests: list[dict]) -> str:
    batch = client.messages.batches.create(requests=requests)
    print(f"Batch submitted: {batch.id} ({len(requests)} requests)")
    BATCH_ID_FILE.write_text(batch.id)
    return batch.id


def wait_for_batch(client: anthropic.Anthropic, batch_id: str) -> None:
    print("Waiting for batch to complete (polls every 30s)...")
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(f"  {batch.processing_status} | succeeded={counts.succeeded} "
              f"errored={counts.errored} processing={counts.processing}")
        if batch.processing_status == "ended":
            break
        time.sleep(30)


def parse_questions(raw_text: str) -> Optional[list]:
    raw = raw_text.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try extracting JSON array
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                return None
    return None


REQUIRED_FIELDS = {"id", "question", "option_a", "option_b", "option_c", "option_d",
                   "correct_option", "explanation", "subtopic", "dimension",
                   "difficulty", "is_core_concept", "is_trap", "question_type", "tags"}


def validate_question(q: dict, topic: str, subject: str) -> Optional[dict]:
    missing = REQUIRED_FIELDS - set(q.keys())
    if missing:
        return None
    if q.get("correct_option") not in ("A", "B", "C", "D"):
        return None
    q.setdefault("is_recent_dev", 0)
    q["subject"] = subject
    q["topic"] = topic
    q["tags"] = json.dumps(q.get("tags", []))
    q["is_core_concept"] = int(bool(q.get("is_core_concept", 0)))
    q["is_trap"] = int(bool(q.get("is_trap", 0)))
    q["is_recent_dev"] = int(bool(q.get("is_recent_dev", 0)))
    return q


def insert_questions(conn: sqlite3.Connection, client: anthropic.Anthropic,
                     batch_id: str):
    inserted = 0
    errors = 0

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id
        subject, topic = custom_id.split("__", 1)

        if result.result.type == "error":
            print(f"  API ERROR for {custom_id}: {result.result.error}")
            errors += 1
            continue

        raw = result.result.message.content[0].text
        questions = parse_questions(raw)

        if questions is None:
            print(f"  PARSE ERROR for {custom_id}: {repr(raw[:120])}")
            errors += 1
            continue

        topic_inserted = 0
        for q in questions:
            validated = validate_question(q, topic, subject)
            if validated is None:
                errors += 1
                continue
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO rbi_questions
                    (id, question, option_a, option_b, option_c, option_d,
                     correct_option, explanation, subject, topic, subtopic,
                     dimension, tier, difficulty, is_core_concept, is_recent_dev,
                     is_trap, question_type, tags)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?)
                """, (
                    validated["id"],
                    validated["question"],
                    validated["option_a"],
                    validated["option_b"],
                    validated["option_c"],
                    validated["option_d"],
                    validated["correct_option"],
                    validated["explanation"],
                    validated["subject"],
                    validated["topic"],
                    validated.get("subtopic", ""),
                    validated.get("dimension", "definition"),
                    validated.get("difficulty", "medium"),
                    validated["is_core_concept"],
                    validated["is_recent_dev"],
                    validated["is_trap"],
                    validated.get("question_type", "standard"),
                    validated["tags"],
                ))
                topic_inserted += 1
                inserted += 1
            except sqlite3.IntegrityError as e:
                print(f"  DB error for {validated.get('id', '?')}: {e}")
                errors += 1

        conn.commit()
        print(f"  {custom_id}: {topic_inserted} questions inserted")

    return inserted, errors


def seed_topic_mastery(conn: sqlite3.Connection) -> None:
    """Initialise rbi_topic_mastery rows for all topics that have questions."""
    topics = conn.execute(
        "SELECT DISTINCT topic, subject FROM rbi_questions"
    ).fetchall()
    for topic, subject in topics:
        conn.execute("""
            INSERT OR IGNORE INTO rbi_topic_mastery
            (user_id, topic, subject)
            VALUES ('rahul', ?, ?)
        """, (topic, subject))
    conn.commit()
    print(f"Seeded {len(topics)} topic mastery rows")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    theory_text = THEORY_SOURCE.read_text()
    client = anthropic.Anthropic(api_key=api_key)
    conn = sqlite3.connect(DB_PATH)

    # Check for existing batch
    if BATCH_ID_FILE.exists():
        batch_id = BATCH_ID_FILE.read_text().strip()
        print(f"Resuming existing batch: {batch_id}")
    else:
        requests = build_batch_requests(theory_text)
        batch_id = submit_batch(client, requests)

    wait_for_batch(client, batch_id)

    print("\nInserting questions...")
    inserted, errors = insert_questions(conn, client, batch_id)
    seed_topic_mastery(conn)

    total = conn.execute("SELECT COUNT(*) FROM rbi_questions").fetchone()[0]
    per_subject = conn.execute(
        "SELECT subject, COUNT(*) FROM rbi_questions GROUP BY subject ORDER BY COUNT(*) DESC"
    ).fetchall()

    conn.close()
    print(f"\nDone. {inserted} inserted, {errors} errors.")
    print(f"Total in DB: {total}")
    print("\nPer subject:")
    for subj, cnt in per_subject:
        print(f"  {subj}: {cnt}")


if __name__ == "__main__":
    main()
