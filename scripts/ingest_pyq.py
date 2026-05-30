"""
Stage 3: Parse IES PYQ PDFs → pyq_questions table.
Run: python3 scripts/ingest_pyq.py

Parses GE-01 to GE-04 topic-compiled PDFs from ecoholics.in.
Uses structural section detection (topic headers in PDF).
Deduplicates via SHA-256 question_hash.
"""
import hashlib
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parsers.digital_pdf import extract_text

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
PYQ_DIR = Path.home() / "Desktop" / "UPSC" / "IES"
EXAM_ID = "ies_2026"

# Exact topic names from PDF TOCs → topic_id, scoped per paper to avoid cross-paper collisions
# (e.g. "Inflation" appears inside GE-02's employment section header)
PAPER_TOPIC_MAP = {
    "ge_01": {
        "Theory of Consumer Demand": "consumers_demand",
        "Theory of Production": "theory_of_production",
        "Theory of Value": "theory_of_value",
        "Theory of distribution": "theory_of_distribution",
        "Welfare Economics": "welfare_economics",
        "Mathematical/Quantitative methods in Economics": "mathematical_methods",
        "Statistical and Econometric Methods and Income Distribution": "statistical_econometric_methods",
    },
    "ge_02": {
        "Economic Thought": "economic_thought",
        "National Income and Social Accounting": "national_income_accounting",
        "Theory of Employment, Output, Inflation, Money and Finance": "employment_output_inflation_money",
        "Financial and Capital Market": "financial_capital_market",
        "Economic Growth and Development": "economic_growth_development",
        "International Economics": "international_economics",
        "Balance of Payments": "balance_of_payments",
        "Global Institutions": "global_institutions",
    },
    "ge_03": {
        "Public Finance": "public_finance",
        "Environmental Economics": "environmental_economics",
        "Industrial Economics": "industrial_economics",
        "State, Market and Planning": "state_market_planning",
    },
    "ge_04": {
        "History of Development and Planning": "development_planning_history",
        "Federal Finance": "federal_finance",
        "Budgeting and Fiscal Policy": "budgeting_fiscal_policy_india",
        "Poverty, Unemployment and Human Development": "poverty_unemployment_hd",
        "Agriculture and Rural development strategies": "agriculture_rural_development",
        "India’s experience with Urbanization and Migration": "urbanisation_migration",
        "Industry: Strategy of industrial development": "industry_india",
        "Foreign Trade": "foreign_trade_india",
        "Labour": "labour_india",
        "Inflation": "inflation_india",
        "Money and Banking": "money_banking_india",
    },
}

PAPER_FILES = {
    "ge_01": PYQ_DIR / "GE-01" / "GE-01.pdf",
    "ge_02": PYQ_DIR / "GE-02" / "GE-02.pdf",
    "ge_03": PYQ_DIR / "GE-03" / "GE-03.pdf",
    "ge_04": PYQ_DIR / "GE-04" / "GE-04.pdf",
}


def compute_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def parse_marks_info(meta_str: str) -> tuple:
    """Parse total marks and optional word count from metadata string."""
    s = re.sub(r"\s+", " ", meta_str).strip()

    wc_match = re.search(r"(\d+)\s*words?", s, re.I)
    answer_length = int(wc_match.group(1)) if wc_match else None

    # Strip word-count portion then 'marks'/'mark' suffix to isolate numbers
    marks_part = re.sub(r"-?\s*\d+\s*words?.*", "", s, flags=re.I)
    marks_part = re.sub(r",?\s*\d+\s*words?.*", "", marks_part, flags=re.I)
    marks_part = re.sub(r"\s*marks?.*", "", marks_part, flags=re.I).strip()
    marks_part = re.sub(r"\s*mark.*", "", marks_part, flags=re.I).strip()

    if "=" in marks_part:
        # e.g. "3+6=9" or "5 + 3 = 8" — take value after last =
        after_eq = marks_part.rsplit("=", 1)[-1]
        num = re.search(r"\d+", after_eq)
        total = int(num.group()) if num else 0
    elif "+" in marks_part:
        nums = re.findall(r"\d+", marks_part)
        total = sum(int(n) for n in nums) if nums else 0
    else:
        num = re.search(r"\d+", marks_part)
        total = int(num.group()) if num else 0

    return total, answer_length


def extract_sections(text: str, paper_id: str) -> list[tuple[str, str]]:
    """Return [(topic_id, section_text), ...] in document order for this paper only."""
    topic_map = PAPER_TOPIC_MAP[paper_id]
    preamble_end = text.find("BELIEVE IN YOURSELF")
    search_start = text.find("\n", preamble_end + 50) if preamble_end != -1 else 0

    positions: list[tuple[int, str]] = []
    for pdf_name, tid in topic_map.items():
        idx = text.find(pdf_name, search_start)
        if idx != -1:
            positions.append((idx, tid))

    positions.sort(key=lambda x: x[0])

    sections = []
    for i, (pos, tid) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections.append((tid, text[pos:end]))

    return sections


def parse_questions(section_text: str, paper_id: str, topic_id: str) -> list[dict]:
    # Strip ecoholics watermarks and lone page-number lines
    text = re.sub(r"WWW\.ECOHOLICS\.IN\n", "", section_text)
    text = re.sub(r"\n\d{1,3}\n", "\n", text)

    q_start = re.search(r"\nQ\d+[\s.\n]", text)
    if not q_start:
        return []

    questions_chunk = text[q_start.start():]
    # Split into blocks: each new question starts with \nQ\d+
    blocks = re.split(r"(?=\nQ\d+[\s.\n])", questions_chunk)

    questions = []
    for block in blocks:
        block = block.strip()
        if not block or not re.match(r"^Q\d+", block):
            continue

        # Find all (year, marks_info) pairs — handles multi-part questions
        metas = re.findall(r"\((\d{4}),([^)]+)\)", block, re.DOTALL)
        if not metas:
            continue

        year = int(metas[0][0])
        total_marks = 0
        answer_length = None
        for _, marks_info in metas:
            m, wc = parse_marks_info(marks_info)
            total_marks += m
            if wc and answer_length is None:
                answer_length = wc

        # Remove metadata parentheticals from question text
        q_text = re.sub(r"\(\d{4},[^)]+\)", "", block, flags=re.DOTALL)
        q_text = re.sub(r"\s+", " ", q_text).strip()

        if len(q_text) < 20:
            continue

        questions.append(
            {
                "paper_id": paper_id,
                "topic_id": topic_id,
                "year": year,
                "marks": total_marks if total_marks > 0 else None,
                "answer_length": str(answer_length) if answer_length else None,
                "question_text": q_text,
                "question_hash": compute_hash(q_text),
            }
        )

    return questions


def ingest_paper(conn: sqlite3.Connection, paper_id: str, pdf_path: Path) -> int:
    print(f"  Parsing {pdf_path.name}...", end=" ")
    text = extract_text(str(pdf_path))
    sections = extract_sections(text, paper_id)

    all_qs: list[dict] = []
    for tid, section_text in sections:
        all_qs.extend(parse_questions(section_text, paper_id, tid))

    inserted = 0
    skipped = 0
    for i, q in enumerate(all_qs):
        qid = f"{paper_id}_{i+1:04d}"
        conn.execute(
            """
            INSERT OR IGNORE INTO pyq_questions
                (question_id, exam_id, paper_id, year, question_text,
                 topic_id, marks, answer_length, question_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                qid,
                EXAM_ID,
                q["paper_id"],
                q["year"],
                q["question_text"],
                q["topic_id"],
                q["marks"],
                q["answer_length"],
                q["question_hash"],
            ),
        )
        delta = conn.execute("SELECT changes()").fetchone()[0]
        inserted += delta
        skipped += 1 - delta

    conn.commit()
    print(f"{inserted} inserted, {skipped} skipped (dups)")
    return inserted


def verify(conn: sqlite3.Connection) -> None:
    print("\n── Stage 3 Sense Check ──────────────────────────")

    by_paper = conn.execute("""
        SELECT paper_id, COUNT(*) as cnt
        FROM pyq_questions WHERE exam_id=?
        GROUP BY paper_id ORDER BY paper_id
    """, (EXAM_ID,)).fetchall()

    print("Questions by paper:")
    total = 0
    for paper_id, cnt in by_paper:
        print(f"  {paper_id}: {cnt:4d}")
        total += cnt
    print(f"  Total  : {total:4d}")

    year_dist = conn.execute("""
        SELECT year, COUNT(*) FROM pyq_questions
        WHERE exam_id=? GROUP BY year ORDER BY year DESC
    """, (EXAM_ID,)).fetchall()

    print("\nYear distribution (recent 5):")
    for yr, cnt in year_dist[:5]:
        print(f"  {yr}: {cnt}")

    no_topic = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=? AND topic_id IS NULL",
        (EXAM_ID,)
    ).fetchone()[0]

    no_year = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=? AND year IS NULL",
        (EXAM_ID,)
    ).fetchone()[0]

    dups = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT question_hash FROM pyq_questions WHERE exam_id=?
            GROUP BY question_hash HAVING COUNT(*) > 1
        )
    """, (EXAM_ID,)).fetchone()[0]

    topic_coverage = conn.execute("""
        SELECT COUNT(DISTINCT topic_id) FROM pyq_questions WHERE exam_id=?
    """, (EXAM_ID,)).fetchone()[0]

    print(f"\nTopics with at least 1 question : {topic_coverage}/30")
    print(f"Questions without topic_id      : {no_topic}")
    print(f"Questions without year          : {no_year}")
    print(f"Duplicate hashes                : {dups}")

    assert total > 900, f"Expected 900+ questions, got {total}"
    assert no_topic == 0, f"{no_topic} questions missing topic_id"
    assert no_year == 0, f"{no_year} questions missing year"
    assert dups == 0, f"{dups} duplicate question hashes"
    assert topic_coverage == 30, f"Only {topic_coverage}/30 topics covered"

    print("\n✓ All sanity checks passed")
    print("─────────────────────────────────────────────────\n")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print("DB not found. Run init_db.py first.")
        raise SystemExit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")

    print("Ingesting PYQ papers...")
    for paper_id, pdf_path in PAPER_FILES.items():
        if not pdf_path.exists():
            print(f"  MISSING: {pdf_path}")
            continue
        ingest_paper(conn, paper_id, pdf_path)

    verify(conn)
    conn.close()
