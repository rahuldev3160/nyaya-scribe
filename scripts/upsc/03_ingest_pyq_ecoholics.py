"""
Script 03: Ingest UPSC Economics Optional PYQs from Ecoholics-format topic-wise PDFs.

Source: ~/Desktop/UPSC/Mains/Optional/PYQ- paper 1/  and  PYQ- Paper 2/
Target: data/upsc_eco_opt.db  →  pyq_questions table

PDF format (Ecoholics topic-wise):
    IAS-MAINS
    ECONOMICS (Optional)
    Previous years Question Paper (Topic wise)
    TOPIC HEADER
    1. Question text here... (2025)
    2. Next question (2024)
    (1) Question text (2025)

Year always in parentheses at end. Marks may appear as (8+7=15) before year.
Safe to re-run — idempotent via INSERT OR IGNORE + question_hash dedup.
"""
import hashlib
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

# Allow import of parsers package from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))
from parsers.digital_pdf import extract_text, get_page_text_quality  # noqa: E402

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_eco_opt.db"
EXAM_ID = "upsc_eco_opt"

PYQ_P1_DIR = Path.home() / "Desktop" / "UPSC" / "Mains" / "Optional" / "PYQ- paper 1"
PYQ_P2_DIR = Path.home() / "Desktop" / "UPSC" / "Mains" / "Optional" / "PYQ- Paper 2"

PAPER1_TOPIC_MAP = {
    "ADVANCED MICRO (Markets Structure).pdf": "advanced_micro",
    "Welfare & Marshallian & Alternative Distribution.pdf": "welfare_distribution",
    "ADVANCED MACRO ECONOMICS.pdf": "advanced_macro",
    "MONEY BANKING AND FINANCE.pdf": "money_banking_finance",
    "INTERNATIONAL ECONOMICS.pdf": "international_economics",
    "GROWTH AND DEVELOPMENT..pdf": "growth_development",
}

PAPER2_TOPIC_MAP = {
    "INDIAN ECONOMY IN PRE-INDEPENDENCE ERA.pdf": "indian_eco_pre1947",
    "PLANING & DEVELOPMENT.pdf": "planning_development",
    "GROWTH COMPOSITION & TREND.pdf": "growth_composition",
    "INDUSTRY & SERVICES.pdf": "industry_services",
    "POVERTY, UNEMPLOYMENT, INEQUALITY & POLUTION.pdf": "poverty_unemployment",
    "AGRICULTURE.pdf": "agriculture",
    "EXTERNAL SECTOR & BOP & EXCHANGE RATE.pdf": "external_sector_bop",
    "MONETARY SYSTEM & BANKING.pdf": "monetary_banking_india",
    "PUBLIC FINANCE.pdf": "public_finance_india",
    "CURRENT TOPICS PROGRAMME & SCHEME.pdf": "current_topics",
}


# ─────────────────────────────────────────────────────────────
# DB BOOTSTRAP
# ─────────────────────────────────────────────────────────────

def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist (idempotent)."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS pyq_questions (
        question_id     TEXT NOT NULL,
        exam_id         TEXT NOT NULL,
        paper_id        TEXT NOT NULL,
        year            INTEGER NOT NULL,
        question_text   TEXT NOT NULL,
        topic_id        TEXT NOT NULL,
        subtopic_id     TEXT,
        marks           INTEGER DEFAULT 10,
        answer_length   TEXT,
        key_concepts    TEXT,
        question_hash   TEXT UNIQUE,
        PRIMARY KEY (question_id, exam_id)
    );
    """)
    conn.commit()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def compute_hash(text: str) -> str:
    """SHA-256 of whitespace-normalized, lowercase question text."""
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def parse_marks(marks_str: str) -> Optional[int]:
    """Extract integer marks from strings like '8+7=15', '20', '10+5'."""
    if not marks_str:
        return None
    s = marks_str.strip()
    if "=" in s:
        after_eq = s.rsplit("=", 1)[-1]
        m = re.search(r"\d+", after_eq)
        return int(m.group()) if m else None
    if "+" in s:
        nums = re.findall(r"\d+", s)
        return sum(int(n) for n in nums) if nums else None
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def strip_watermarks(text: str) -> str:
    """Remove Ecoholics watermark lines and lone page-number lines."""
    text = re.sub(r"(?i)www\.ecoholics\.in\s*\n?", "", text)
    text = re.sub(r"\n\s*\d{1,3}\s*\n", "\n", text)
    return text


# ─────────────────────────────────────────────────────────────
# PARSER
# ─────────────────────────────────────────────────────────────

# Matches question starters: "1." "2." "(1)" "(2)"
Q_SPLIT_PATTERN = re.compile(
    r"(?=(?:^|\n)\s*(?:\(?\d+\)\.?|\d+\.)\s+\S)",
    re.MULTILINE,
)

# Year at end of question: (2025) — must be final token
YEAR_AT_END = re.compile(r"\(\s*(\d{4})\s*\)\s*$")

# Marks expression immediately before year: (8+7=15) (2025)
MARKS_BEFORE_YEAR = re.compile(r"\(([^)]+)\)\s*\(\s*\d{4}\s*\)\s*$")


def parse_questions_from_text(text: str, paper_id: str, topic_id: str) -> list[dict]:
    """
    Parse individual questions from a topic PDF's full text.

    Returns list of dicts with keys:
        paper_id, topic_id, year, marks, question_text, question_hash
    """
    text = strip_watermarks(text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    questions = []
    blocks = Q_SPLIT_PATTERN.split(text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Block must start with a numeric question marker
        if not re.match(r"^\s*[\(]?\d+[\).]", block):
            continue

        # Flatten whitespace for uniform parsing
        flat = re.sub(r"\s+", " ", block).strip()

        year_match = YEAR_AT_END.search(flat)
        if not year_match:
            continue

        year = int(year_match.group(1))
        if year < 1979 or year > 2026:
            continue

        # Detect optional marks expression before year
        marks = None
        marks_match = MARKS_BEFORE_YEAR.search(flat)
        if marks_match:
            candidate = marks_match.group(1).strip()
            if re.match(r"^[\d\s\+\=]+$", candidate):
                marks = parse_marks(candidate)

        # Build clean question text
        q_text = flat
        q_text = re.sub(r"\(\s*\d{4}\s*\)\s*$", "", q_text).strip()
        if marks is not None:
            q_text = re.sub(r"\([^)]+\)\s*$", "", q_text).strip()
        # Strip leading question number marker
        q_text = re.sub(r"^\s*[\(]?\d+[\)\.]\s*", "", q_text).strip()

        if len(q_text) < 15:
            continue

        questions.append({
            "paper_id": paper_id,
            "topic_id": topic_id,
            "year": year,
            "marks": marks,
            "question_text": q_text,
            "question_hash": compute_hash(q_text),
        })

    return questions


# ─────────────────────────────────────────────────────────────
# INGESTION
# ─────────────────────────────────────────────────────────────

def ingest_topic_pdf(
    conn: sqlite3.Connection,
    pdf_path: Path,
    paper_id: str,
    topic_id: str,
    id_counter: "list[int]",
) -> "tuple[int, int, Optional[str]]":
    """
    Parse one topic PDF and insert its questions.

    Returns (inserted, skipped, skip_reason).
    skip_reason is non-None when the entire PDF is skipped.
    """
    quality = get_page_text_quality(str(pdf_path))
    if quality < 100:
        return 0, 0, f"scanned/empty (avg {quality:.0f} chars/page)"

    text = extract_text(str(pdf_path))
    if len(text.strip()) < 100:
        return 0, 0, "empty text extracted"

    questions = parse_questions_from_text(text, paper_id, topic_id)

    inserted = 0
    skipped = 0
    for q in questions:
        qid = f"{paper_id}_{id_counter[0]:04d}"
        id_counter[0] += 1
        conn.execute(
            """
            INSERT OR IGNORE INTO pyq_questions
                (question_id, exam_id, paper_id, year, question_text,
                 topic_id, marks, question_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                qid,
                EXAM_ID,
                q["paper_id"],
                q["year"],
                q["question_text"],
                q["topic_id"],
                q["marks"],
                q["question_hash"],
            ),
        )
        delta = conn.execute("SELECT changes()").fetchone()[0]
        inserted += delta
        skipped += 1 - delta

    conn.commit()
    return inserted, skipped, None


def ingest_paper(
    conn: sqlite3.Connection,
    paper_id: str,
    topic_map: "dict[str, str]",
    source_dir: Path,
) -> "dict[str, tuple[int, int]]":
    """
    Ingest all topic PDFs for one paper.

    Returns {topic_id: (inserted, skipped)}.
    """
    # Find highest existing index to avoid PK collisions on re-run
    existing = conn.execute(
        """
        SELECT question_id FROM pyq_questions
        WHERE exam_id=? AND paper_id=?
        ORDER BY question_id
        """,
        (EXAM_ID, paper_id),
    ).fetchall()
    max_idx = 0
    for (qid,) in existing:
        parts = qid.split("_")
        if parts:
            try:
                idx = int(parts[-1])
                max_idx = max(max_idx, idx)
            except ValueError:
                pass

    id_counter = [max_idx + 1]
    results: dict[str, tuple[int, int]] = {}

    for filename, topic_id in topic_map.items():
        pdf_path = source_dir / filename
        if not pdf_path.exists():
            print(f"  MISSING: {pdf_path.name}")
            results[topic_id] = (0, 0)
            continue

        inserted, skipped, skip_reason = ingest_topic_pdf(
            conn, pdf_path, paper_id, topic_id, id_counter
        )
        if skip_reason:
            print(f"  SKIPPED [{topic_id}] {pdf_path.name}: {skip_reason}")
        results[topic_id] = (inserted, skipped)

    return results


# ─────────────────────────────────────────────────────────────
# VERIFICATION
# ─────────────────────────────────────────────────────────────

def verify(conn: sqlite3.Connection) -> None:
    print("\n── Script 03 Verification ───────────────────────")

    rows = conn.execute(
        """
        SELECT topic_id, paper_id, COUNT(*) as cnt
        FROM pyq_questions
        WHERE exam_id=?
        GROUP BY topic_id, paper_id
        ORDER BY paper_id, topic_id
        """,
        (EXAM_ID,),
    ).fetchall()

    print(f"{'topic_id':<35} {'paper':<10} {'count':>6}")
    print("-" * 55)
    total = 0
    for topic_id, paper_id, cnt in rows:
        print(f"{topic_id:<35} {paper_id:<10} {cnt:>6}")
        total += cnt
    print("-" * 55)
    print(f"{'TOTAL':<46} {total:>6}")

    no_topic = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id=? AND topic_id IS NULL",
        (EXAM_ID,),
    ).fetchone()[0]

    dups = conn.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT question_hash FROM pyq_questions WHERE exam_id=?
            GROUP BY question_hash HAVING COUNT(*) > 1
        )
        """,
        (EXAM_ID,),
    ).fetchone()[0]

    print(f"\nquestions without topic_id : {no_topic}")
    print(f"duplicate hashes           : {dups}")

    status = "PASS"
    if total < 200:
        print(f"WARNING: only {total} questions (expected >200)")
        status = "WARN"
    if no_topic > 0:
        print(f"FAIL: {no_topic} questions missing topic_id")
        status = "FAIL"

    print(f"\nOverall status: {status}")
    print("─────────────────────────────────────────────────\n")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main() -> None:
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Run the upsc init_db script first.")
        raise SystemExit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    ensure_schema(conn)

    summary: dict[str, dict[str, tuple[int, int]]] = {}

    print("=== Script 03: Ingesting Ecoholics topic-wise PYQ PDFs ===\n")

    print("-- Paper 1 (upsc_p1) --")
    if PYQ_P1_DIR.exists():
        summary["upsc_p1"] = ingest_paper(conn, "upsc_p1", PAPER1_TOPIC_MAP, PYQ_P1_DIR)
    else:
        print(f"  SOURCE DIR MISSING: {PYQ_P1_DIR}")

    print("\n-- Paper 2 (upsc_p2) --")
    if PYQ_P2_DIR.exists():
        summary["upsc_p2"] = ingest_paper(conn, "upsc_p2", PAPER2_TOPIC_MAP, PYQ_P2_DIR)
    else:
        print(f"  SOURCE DIR MISSING: {PYQ_P2_DIR}")

    # Summary table
    print("\n── Ingestion Summary ────────────────────────────")
    print(f"{'topic_id':<35} {'paper':<10} {'inserted':>9} {'skipped':>8}")
    print("-" * 65)
    grand_ins = grand_skip = 0
    for paper_id, topic_results in summary.items():
        p_ins = p_skip = 0
        for topic_id, (ins, skip) in topic_results.items():
            print(f"{topic_id:<35} {paper_id:<10} {ins:>9} {skip:>8}")
            p_ins += ins
            p_skip += skip
        print(f"  {'Subtotal':<33} {paper_id:<10} {p_ins:>9} {p_skip:>8}")
        grand_ins += p_ins
        grand_skip += p_skip
        print()

    print(f"  {'GRAND TOTAL':<33} {'':10} {grand_ins:>9} {grand_skip:>8}")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
