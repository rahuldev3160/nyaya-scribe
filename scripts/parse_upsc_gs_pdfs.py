"""
parse_upsc_gs_pdfs.py — Extract individual questions from downloaded UPSC GS PDFs.

Input:  data/cache/upsc_gs_pdfs/manifest.json  (from fetch_upsc_gs_pdfs.py)
Output: data/cache/upsc_gs_parsed_{year}_{paper_id}.json  per file

Handles:
- Section headers (SECTION-A / Q1-10: 10m, Q11-20: 15m patterns)
- Multi-line question text
- GS4 case study preambles
- Falls through to pytesseract if pdftotext produces <50 words/page

Run: /opt/homebrew/bin/python3.11 scripts/parse_upsc_gs_pdfs.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / "data" / "cache" / "upsc_gs_pdfs"
PARSED_DIR = ROOT / "data" / "cache"
MANIFEST_PATH = CACHE_DIR / "manifest.json"

# GS Mains: Q1-10 = 10 marks (150w), Q11-20 = 15 marks (250w) for most years
# Actual split varies slightly — detect from question headers or default to this
DEFAULT_MARKS = {
    "Q1":  10, "Q2":  10, "Q3":  10, "Q4":  10, "Q5":  10,
    "Q6":  10, "Q7":  10, "Q8":  10, "Q9":  10, "Q10": 10,
    "Q11": 15, "Q12": 15, "Q13": 15, "Q14": 15, "Q15": 15,
    "Q16": 15, "Q17": 15, "Q18": 15, "Q19": 15, "Q20": 15,
}

# Patterns that appear in PDF headers/footers to strip
JUNK_PATTERNS = [
    re.compile(r"^Page\s+\d+\s+of\s+\d+", re.I),
    re.compile(r"^CIVIL\s+SERVICES.*EXAMINATION", re.I),
    re.compile(r"^GENERAL\s+STUDIES.*PAPER", re.I),
    re.compile(r"^\s*Time\s+Allowed\s*:", re.I),
    re.compile(r"^\s*Maximum\s+Marks\s*:", re.I),
    re.compile(r"^\s*Instructions\s*:", re.I),
    re.compile(r"^SECTION[\s\-]+[AB]", re.I),
    re.compile(r"^\s*\d+\s*$"),  # lone page numbers
]

# GS4 case study pattern: starts with "Case Study" or numbered scenario
CASE_STUDY_HEADER = re.compile(
    r"^(Case\s+Study|CASE\s+STUDY|Situation\s*\d*)\b", re.I
)

# Question start pattern: Q.1 / Q1. / 1. with optional marks annotation
Q_START = re.compile(
    r"^(?:Q\.?\s*|Question\s+)?(\d{1,2})[.)]\s+(.+)", re.S
)

# Marks extraction from question text
MARKS_RE = re.compile(
    r"\((\d{2})\s*(?:marks?|m)\b", re.I
)
WORD_RE = re.compile(
    r"\((\d{2,3})\s*(?:words?|w)\b", re.I
)


def _pdf_to_text(pdf_path: str) -> str:
    """Run pdftotext -layout and return raw text."""
    result = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True, timeout=60
    )
    return result.stdout if result.returncode == 0 else ""


def _ocr_fallback(pdf_path: str) -> str:
    """pytesseract OCR fallback for scanned PDFs."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        pages = convert_from_path(pdf_path, dpi=200)
        texts = [pytesseract.image_to_string(p, lang="eng") for p in pages]
        return "\n".join(texts)
    except ImportError:
        print("  WARN pytesseract/pdf2image not installed — OCR skipped")
        return ""


def _clean_lines(raw_text: str) -> list[str]:
    """Strip junk lines, normalise whitespace."""
    lines = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if any(p.search(line) for p in JUNK_PATTERNS):
            continue
        lines.append(line)
    return lines


def _detect_marks(q_text: str, q_num: int) -> tuple[int, int]:
    """Return (marks, word_limit) from question text or default by question number."""
    m_match = MARKS_RE.search(q_text)
    w_match = WORD_RE.search(q_text)
    if m_match:
        marks = int(m_match.group(1))
        word_limit = int(w_match.group(1)) if w_match else (150 if marks == 10 else 250)
        return marks, word_limit
    # Default by question number
    key = f"Q{q_num}"
    marks = DEFAULT_MARKS.get(key, 10)
    return marks, (150 if marks == 10 else 250)


def _clean_q_text(text: str) -> str:
    """Remove trailing marks annotations from question text."""
    text = re.sub(r"\s*\(\d{2,3}\s*(?:marks?|m)\b[^)]*\)", "", text)
    text = re.sub(r"\s*\(\d{2,3}\s*(?:words?|w)\b[^)]*\)", "", text)
    return text.strip()


def _parse_questions(lines: list[str], paper_id: str, year: int, source_url: str, source_doc: str) -> list[dict]:
    """Parse cleaned lines into question dicts."""
    questions = []
    current_q_num = None
    current_text_parts: list[str] = []
    preamble: str | None = None
    in_preamble = False

    def _flush():
        nonlocal current_q_num, current_text_parts, preamble, in_preamble
        if current_q_num is None or not current_text_parts:
            return
        full_text = " ".join(current_text_parts).strip()
        marks, word_limit = _detect_marks(full_text, current_q_num)
        clean_text = _clean_q_text(full_text)
        if len(clean_text) < 20:
            # Too short — likely noise
            current_q_num = None
            current_text_parts = []
            return
        entry = {
            "paper_id": paper_id,
            "year": year,
            "question_number": current_q_num,
            "question_text": clean_text,
            "marks": marks,
            "word_limit": word_limit,
            "source_url": source_url,
            "source_doc": source_doc,
        }
        if paper_id == "gs4" and preamble:
            entry["case_study_preamble"] = preamble
        questions.append(entry)
        current_q_num = None
        current_text_parts = []
        preamble = None
        in_preamble = False

    for line in lines:
        # GS4: detect case study preamble
        if paper_id == "gs4" and CASE_STUDY_HEADER.match(line):
            _flush()
            in_preamble = True
            preamble = line
            continue

        # New question start
        m = Q_START.match(line)
        if m:
            _flush()
            current_q_num = int(m.group(1))
            rest = m.group(2)
            if in_preamble and preamble:
                # This Q is part of the case study
                current_text_parts = [rest]
            else:
                in_preamble = False
                preamble = None
                current_text_parts = [rest]
            continue

        # Continue preamble
        if in_preamble and current_q_num is None:
            preamble = (preamble or "") + " " + line
            continue

        # Continue current question
        if current_q_num is not None:
            current_text_parts.append(line)

    _flush()
    return questions


def parse_pdf(entry: dict) -> list[dict]:
    """Parse a single manifest entry. Returns list of question dicts."""
    if entry["quality"] == "not_found":
        print(f"  SKIP {entry['paper_id']} {entry['year']} — not downloaded")
        return []

    pdf_path = entry["path"]
    words = entry.get("word_count", 0)

    raw_text = _pdf_to_text(pdf_path)
    actual_words = len(raw_text.split())

    if actual_words < 150:
        print(f"  OCR  {entry['paper_id']} {entry['year']} — pdftotext={actual_words} words, trying OCR")
        raw_text = _ocr_fallback(pdf_path)
        if len(raw_text.split()) < 150:
            print(f"  FAIL {entry['paper_id']} {entry['year']} — OCR also insufficient")
            return []

    lines = _clean_lines(raw_text)
    questions = _parse_questions(
        lines,
        entry["paper_id"],
        entry["year"],
        entry.get("source_url", ""),
        Path(pdf_path).name,
    )
    print(f"  DONE {entry['paper_id']} {entry['year']} — {len(questions)} questions extracted")
    return questions


def main():
    if not MANIFEST_PATH.exists():
        print(f"Manifest not found: {MANIFEST_PATH}")
        print("Run fetch_upsc_gs_pdfs.py first.")
        sys.exit(1)

    manifest = json.loads(MANIFEST_PATH.read_text())
    total = 0

    for entry in manifest:
        questions = parse_pdf(entry)
        if not questions:
            continue
        out_path = PARSED_DIR / f"upsc_gs_parsed_{entry['year']}_{entry['paper_id']}.json"
        out_path.write_text(json.dumps(questions, indent=2, ensure_ascii=False))
        print(f"  SAVE {out_path.name}")
        total += len(questions)

    print(f"\nTotal questions extracted from PDFs: {total}")


if __name__ == "__main__":
    main()
