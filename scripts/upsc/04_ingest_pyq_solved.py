"""
Script 04: Ingest pre-solved Q+A pairs from PYQs/ subfolder.

Source: ~/Desktop/UPSC/Mains/Optional/PYQs/
Target: data/upsc.db
    - pyq_questions  (INSERT OR IGNORE, deduped by question_hash)
    - reference_answers  (stores answers with link back to question)

Two PDF formats encountered:
  Format A — year as section header, marks in parens, Ans<N>. blocks:
      Development Theory
      2020
      Q1. Explain how... (10)
      Ans1. Answer text...
      Ans2. ...

  Format B — numbered questions, no year per question, no answers:
      Paper 2 (INDIAN ECONOMY)
      Pre- Independence
      1. Comment on the Theory of Drain...

Safe to re-run — idempotent via INSERT OR IGNORE.
"""
import hashlib
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from parsers.digital_pdf import extract_text, get_page_text_quality  # noqa: E402

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc.db"
EXAM_ID = "upsc_eco_opt"

PYQ_SOLVED_DIR = (
    Path.home() / "Desktop" / "UPSC" / "Mains" / "Optional" / "PYQs"
)

# filename → (topic_id, paper_id)
SOLVED_TOPIC_MAP = {
    "DevelopmentTheoryPYQ.pdf":             ("growth_development",     "upsc_p1"),
    "InternationalTradePYQ.pdf":            ("international_economics", "upsc_p1"),
    "MacroPYQs.pdf":                        ("advanced_macro",          "upsc_p1"),
    "MicroPYQs.pdf":                        ("advanced_micro",          "upsc_p1"),
    "PubFinance&MoneyandBankingPYQs.pdf":   ("money_banking_finance",   "upsc_p1"),
    "PYQs(Before1947).pdf":                 ("indian_eco_pre1947",      "upsc_p2"),
    "PYQs1947-1991.pdf":                    ("planning_development",    "upsc_p2"),
    "PYQs_After1991.pdf":                   ("growth_composition",      "upsc_p2"),
    "PAPER-2_ECO OPTIONAL.pdf":             ("planning_development",    "upsc_p2"),
}

# Known scanned / empty PDFs — skip gracefully
KNOWN_SCANNED = {"MicroPYQs.pdf", "MacroPYQs.pdf"}


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

    CREATE TABLE IF NOT EXISTS reference_answers (
        ref_id          TEXT PRIMARY KEY,
        question_id     TEXT,
        exam_id         TEXT NOT NULL,
        source_doc      TEXT,
        question_text   TEXT,
        answer_text     TEXT,
        year            INTEGER,
        topic_id        TEXT,
        paper_id        TEXT,
        quality_flag    TEXT DEFAULT 'unreviewed',
        notes           TEXT,
        created_at      TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def compute_hash(text: str) -> str:
    """SHA-256 of whitespace-normalized, lowercase text."""
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def get_next_question_id(conn: sqlite3.Connection, paper_id: str) -> "list[int]":
    """Return a mutable [counter] starting after the highest existing id for paper."""
    rows = conn.execute(
        "SELECT question_id FROM pyq_questions WHERE exam_id=? AND paper_id=?",
        (EXAM_ID, paper_id),
    ).fetchall()
    max_idx = 0
    for (qid,) in rows:
        parts = qid.split("_")
        try:
            max_idx = max(max_idx, int(parts[-1]))
        except (ValueError, IndexError):
            pass
    return [max_idx + 1]


def lookup_question_id(conn: sqlite3.Connection, question_hash: str) -> Optional[str]:
    """Try to match a question_hash to an existing pyq_questions row."""
    row = conn.execute(
        "SELECT question_id FROM pyq_questions WHERE question_hash=? AND exam_id=?",
        (question_hash, EXAM_ID),
    ).fetchone()
    return row[0] if row else None


# ─────────────────────────────────────────────────────────────
# FORMAT A PARSER  (year-header + QN. + AnsN. blocks)
# ─────────────────────────────────────────────────────────────

# Section header patterns
_YEAR_HEADER = re.compile(r"^\s*((?:19|20)\d{2})\s*$", re.MULTILINE)
_Q_LINE = re.compile(
    r"^\s*Q?\s*(\d+)\.\s+(.+?)(?:\s+\((\d+)\))?\s*$",
    re.MULTILINE | re.DOTALL,
)
_ANS_SPLITTER = re.compile(r"(?:^|\n)\s*[Aa]ns\s*(\d+)\.", re.MULTILINE)


def parse_format_a(text: str) -> list[dict]:
    """
    Parse Format A PDFs: year header sections with Q<N>. and Ans<N>. blocks.

    Returns list of dicts:
        {year, marks, question_text, answer_text (may be None)}
    """
    results = []

    # Split text at year headers to get year-scoped sections
    year_positions = [(m.start(), int(m.group(1))) for m in _YEAR_HEADER.finditer(text)]

    def get_section(start: int, end: int) -> str:
        return text[start:end]

    sections: list[tuple[int | None, str]] = []
    if not year_positions:
        # No year headers — treat entire text as one section with year=None
        sections.append((None, text))
    else:
        for i, (pos, year) in enumerate(year_positions):
            end = year_positions[i + 1][0] if i + 1 < len(year_positions) else len(text)
            sections.append((year, get_section(pos, end)))

    for year, section in sections:
        # Extract questions: Q1. text (marks) pattern
        # Split on question markers
        q_blocks = re.split(r"(?=\n\s*Q\s*\d+\.)", section)

        for block in q_blocks:
            block = block.strip()
            q_match = re.match(r"^Q\s*(\d+)\.\s+(.+?)(?:\s+\((\d+)\))?\s*(?=\n|$)", block, re.DOTALL)
            if not q_match:
                continue

            q_num = int(q_match.group(1))
            # Take question text up to first Ans marker or end of block
            ans_split = _ANS_SPLITTER.split(block, maxsplit=1)
            question_part = ans_split[0]

            # Re-extract question text cleanly
            q_text_match = re.match(
                r"^Q\s*\d+\.\s+(.+?)(?:\s+\(\d+\))?\s*$",
                re.sub(r"\s+", " ", question_part).strip(),
            )
            if q_text_match:
                q_text = q_text_match.group(1).strip()
            else:
                q_text = re.sub(r"^Q\s*\d+\.\s*", "", question_part, count=1)
                q_text = re.sub(r"\s*\(\d+\)\s*$", "", q_text)
                q_text = re.sub(r"\s+", " ", q_text).strip()

            if len(q_text) < 15:
                continue

            # Marks from (N) at end of question line
            marks_match = re.search(r"\((\d+)\)\s*$", re.sub(r"\s+", " ", question_part).strip())
            marks = int(marks_match.group(1)) if marks_match else None

            # Collect answer: look for AnsN. in the section
            answer_text = None
            ans_pattern = re.compile(
                rf"[Aa]ns\s*{q_num}\.\s*(.*?)(?=[Aa]ns\s*\d+\.|Q\s*\d+\.|$)",
                re.DOTALL,
            )
            ans_match = ans_pattern.search(section)
            if ans_match:
                raw_ans = ans_match.group(1).strip()
                answer_text = re.sub(r"\s+", " ", raw_ans).strip() or None

            results.append({
                "year": year,
                "marks": marks,
                "question_text": q_text,
                "answer_text": answer_text,
            })

    return results


# ─────────────────────────────────────────────────────────────
# FORMAT B PARSER  (numbered questions, no year, no answers)
# ─────────────────────────────────────────────────────────────

def parse_format_b(text: str) -> list[dict]:
    """
    Parse Format B PDFs: plain numbered questions without years or answers.

    Returns list of dicts: {year: None, marks: None, question_text, answer_text: None}
    """
    results = []
    # Match "1. text" or "2. text" style numbered questions
    blocks = re.split(r"(?=\n\s*\d+\.\s+[A-Z])", text)

    for block in blocks:
        block = block.strip()
        q_match = re.match(r"^\d+\.\s+(.+)", block, re.DOTALL)
        if not q_match:
            continue
        q_text = re.sub(r"\s+", " ", q_match.group(1)).strip()
        if len(q_text) < 15:
            continue
        results.append({
            "year": None,
            "marks": None,
            "question_text": q_text,
            "answer_text": None,
        })

    return results


# ─────────────────────────────────────────────────────────────
# SMART PARSER (detect format and dispatch)
# ─────────────────────────────────────────────────────────────

def detect_format(text: str) -> str:
    """
    Return 'A' if text has Ans<N>. patterns or year-header sections,
    'B' otherwise.
    """
    if re.search(r"[Aa]ns\s*\d+\.", text):
        return "A"
    if re.search(r"^\s*Q\s*\d+\.", text, re.MULTILINE):
        return "A"
    return "B"


def parse_pdf(text: str) -> list[dict]:
    """Dispatch to the appropriate format parser."""
    fmt = detect_format(text)
    if fmt == "A":
        return parse_format_a(text)
    return parse_format_b(text)


# ─────────────────────────────────────────────────────────────
# INGESTION
# ─────────────────────────────────────────────────────────────

def ingest_solved_pdf(
    conn: sqlite3.Connection,
    pdf_path: Path,
    topic_id: str,
    paper_id: str,
) -> tuple[int, int, int]:
    """
    Parse one solved PYQ PDF and insert questions + reference answers.

    Returns (q_inserted, q_skipped, answers_inserted).
    """
    source_stem = pdf_path.stem

    # Check for known scanned PDFs before expensive extraction
    if pdf_path.name in KNOWN_SCANNED:
        print(f"  SKIPPED: scanned/empty  ({pdf_path.name})")
        return 0, 0, 0

    quality = get_page_text_quality(str(pdf_path))
    if quality < 100:
        print(f"  SKIPPED: scanned/empty (avg {quality:.0f} chars/page)  ({pdf_path.name})")
        return 0, 0, 0

    text = extract_text(str(pdf_path))
    if len(text.strip()) < 100:
        print(f"  SKIPPED: empty text  ({pdf_path.name})")
        return 0, 0, 0

    records = parse_pdf(text)
    if not records:
        print(f"  WARNING: no records parsed from {pdf_path.name}")
        return 0, 0, 0

    id_counter = get_next_question_id(conn, paper_id)
    q_inserted = q_skipped = ans_inserted = 0

    for idx, rec in enumerate(records):
        q_text = rec["question_text"]
        year = rec["year"]
        marks = rec["marks"]
        answer_text = rec.get("answer_text")

        # pyq_questions requires year NOT NULL — use 0 as sentinel when unknown
        db_year = year if year is not None else 0
        q_hash = compute_hash(q_text)

        # Try insert into pyq_questions
        qid = f"{paper_id}_{id_counter[0]:04d}"
        id_counter[0] += 1

        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO pyq_questions
                    (question_id, exam_id, paper_id, year, question_text,
                     topic_id, marks, question_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (qid, EXAM_ID, paper_id, db_year, q_text, topic_id, marks, q_hash),
            )
            delta = conn.execute("SELECT changes()").fetchone()[0]
            q_inserted += delta
            q_skipped += 1 - delta
        except Exception as e:
            print(f"  ERROR inserting question [{source_stem}#{idx}]: {e}")
            q_skipped += 1

        # Always attempt reference_answers insert if there is answer text
        if answer_text:
            # Try to resolve question_id from existing pyq row
            resolved_qid = lookup_question_id(conn, q_hash)

            ref_id = f"ref_{source_stem}_{idx:04d}"
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO reference_answers
                        (ref_id, question_id, exam_id, source_doc,
                         question_text, answer_text, year, topic_id,
                         paper_id, quality_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ref_id,
                        resolved_qid,
                        EXAM_ID,
                        pdf_path.name,
                        q_text,
                        answer_text,
                        year,
                        topic_id,
                        paper_id,
                        "unreviewed",
                    ),
                )
                delta = conn.execute("SELECT changes()").fetchone()[0]
                ans_inserted += delta
            except Exception as e:
                print(f"  ERROR inserting answer [{source_stem}#{idx}]: {e}")

    conn.commit()
    return q_inserted, q_skipped, ans_inserted


# ─────────────────────────────────────────────────────────────
# VERIFICATION
# ─────────────────────────────────────────────────────────────

def verify(conn: sqlite3.Connection) -> None:
    print("\n── Script 04 Verification ───────────────────────")

    # pyq_questions breakdown
    q_rows = conn.execute(
        """
        SELECT topic_id, paper_id, COUNT(*) as cnt
        FROM pyq_questions WHERE exam_id=?
        GROUP BY topic_id, paper_id
        ORDER BY paper_id, topic_id
        """,
        (EXAM_ID,),
    ).fetchall()

    print(f"\n{'topic_id':<35} {'paper':<10} {'q_count':>8}")
    print("-" * 57)
    q_total = 0
    for topic_id, paper_id, cnt in q_rows:
        print(f"{topic_id:<35} {paper_id:<10} {cnt:>8}")
        q_total += cnt
    print("-" * 57)
    print(f"{'TOTAL pyq_questions':<46} {q_total:>8}")

    # reference_answers breakdown
    a_rows = conn.execute(
        """
        SELECT topic_id, paper_id, COUNT(*) as cnt
        FROM reference_answers WHERE exam_id=?
        GROUP BY topic_id, paper_id
        ORDER BY paper_id, topic_id
        """,
        (EXAM_ID,),
    ).fetchall()

    a_total = sum(cnt for _, _, cnt in a_rows)
    print(f"\n{'topic_id':<35} {'paper':<10} {'ref_ans':>8}")
    print("-" * 57)
    for topic_id, paper_id, cnt in a_rows:
        print(f"{topic_id:<35} {paper_id:<10} {cnt:>8}")
    print("-" * 57)
    print(f"{'TOTAL reference_answers':<46} {a_total:>8}")

    print(f"\nOverall status: {'PASS' if q_total > 0 else 'WARN: 0 questions'}")
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

    if not PYQ_SOLVED_DIR.exists():
        print(f"SOURCE DIR MISSING: {PYQ_SOLVED_DIR}")
        raise SystemExit(1)

    print("=== Script 04: Ingesting pre-solved PYQ PDFs ===\n")

    total_q_ins = total_q_skip = total_a_ins = 0
    pdfs_processed = 0

    print(f"{'filename':<45} {'q_ins':>6} {'q_skip':>7} {'ans_ins':>8}")
    print("-" * 70)

    for filename, (topic_id, paper_id) in SOLVED_TOPIC_MAP.items():
        pdf_path = PYQ_SOLVED_DIR / filename
        if not pdf_path.exists():
            print(f"  MISSING: {filename}")
            continue

        q_ins, q_skip, a_ins = ingest_solved_pdf(conn, pdf_path, topic_id, paper_id)
        print(f"{filename:<45} {q_ins:>6} {q_skip:>7} {a_ins:>8}")
        total_q_ins += q_ins
        total_q_skip += q_skip
        total_a_ins += a_ins
        pdfs_processed += 1

    print("-" * 70)
    print(f"{'TOTALS':<45} {total_q_ins:>6} {total_q_skip:>7} {total_a_ins:>8}")
    print(f"\nPDFs processed: {pdfs_processed}")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
