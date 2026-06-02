"""
05_index_source_docs.py
Walk the UPSC Optional PDF directory and register every PDF in source_documents.
Idempotent — safe to re-run (uses INSERT OR IGNORE).
"""

import sqlite3
import hashlib
from pathlib import Path
from collections import defaultdict

import pdfplumber

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path("/Users/rahulsingh/Desktop/UPSC/Mains/Optional")
DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc.db"
EXAM_ID = "upsc_eco_opt"

# ---------------------------------------------------------------------------
# Topic map: filename → (topic_id, paper_id)
# Used for notes files that have a clear subject association.
# ---------------------------------------------------------------------------
NOTES_TOPIC_MAP = {
    # Paper I notes
    "Microeconomics_combined.pdf": ("advanced_micro", "upsc_p1"),
    "MicroeconomicsNumericals,DetailedSolutions.pdf": ("advanced_micro", "upsc_p1"),
    "MACRO ECONOMICS Summary.pdf": ("advanced_macro", "upsc_p1"),
    "TheoriesofMoneyDemand.pdf": ("money_banking_finance", "upsc_p1"),
    "TheoriesofMoneySupply.pdf": ("money_banking_finance", "upsc_p1"),
    "CentralBank.pdf": ("money_banking_finance", "upsc_p1"),
    "CommercialBankinginIndia.pdf": ("money_banking_finance", "upsc_p1"),
    "RBI-CentralBankingofIndia.pdf": ("money_banking_finance", "upsc_p1"),
    "InternationalEconomics(TradeTheories).pdf": ("international_economics", "upsc_p1"),
    "InternationalInstitution.pdf": ("international_economics", "upsc_p1"),
    "REGIONALTRADINGAGREEMENTS.pdf": ("international_economics", "upsc_p1"),
    "Growth&DevelopmentPart-A.pdf": ("growth_development", "upsc_p1"),
    "Growth&DevelopmentPart-B.pdf": ("growth_development", "upsc_p1"),
    "Growth&DevelopmentPartC.pdf": ("growth_development", "upsc_p1"),
    "Growth&DevelopmentPartD.pdf": ("growth_development", "upsc_p1"),
    "InclusiveGrowth.pdf": ("growth_development", "upsc_p1"),
    "Kaldor&SchumpeterGrowthTheory_(Paper-I&IES).pdf": ("growth_development", "upsc_p1"),
    "EnvironmentalEconomics.pdf": ("growth_development", "upsc_p1"),
    "PublicFinance.pdf": ("public_finance_india", "upsc_p2"),
    "FISCALPOLICYPart-1.pdf": ("public_finance_india", "upsc_p2"),
    "FISCALPOLICYPart-2.pdf": ("public_finance_india", "upsc_p2"),
    "FISCALCONSOLIDATION_.pdf": ("public_finance_india", "upsc_p2"),
    # Paper II notes
    "Agriculture.pdf": ("agriculture", "upsc_p2"),
    "IndianEconomybefore1991,LinearTrendsandAgriculture.pdf": ("planning_development", "upsc_p2"),
    "IndianIndustryBetween1947-1991.pdf": ("industry_services", "upsc_p2"),
    "Poverty,InequalityandUnemployment.pdf": ("poverty_unemployment", "upsc_p2"),
    "GlobalisationandGST.pdf": ("growth_composition", "upsc_p2"),
    "INDUSTRYPOLICY.pdf": ("industry_services", "upsc_p2"),
    "INFRASTRUCTURE.pdf": ("industry_services", "upsc_p2"),
    "DrainofWealth.pdf": ("indian_eco_pre1947", "upsc_p2"),
    "CommercialisationofAgriculture.pdf": ("indian_eco_pre1947", "upsc_p2"),
    "LandSettlement.pdf": ("indian_eco_pre1947", "upsc_p2"),
    "RoleofRailways.pdf": ("indian_eco_pre1947", "upsc_p2"),
}

# Official QP filename prefixes (applies at any depth)
QP_PATTERNS = ("ECONOMICS-PAPER I-QP", "ECONOMICS-PAPER II-QP", "QP-CSM-")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_doc_id(filepath: Path) -> str:
    """Short hex doc_id derived from the full path string."""
    h = hashlib.md5(str(filepath).encode()).hexdigest()
    return f"doc_{h[:12]}"


def classify_pdf(filepath: Path) -> dict:
    """
    Return a dict with keys: doc_type, paper_id, topic_id, status_override.
    status_override=True means file should always be 'needs_ocr'.
    """
    rel = filepath.relative_to(BASE_DIR)
    rel_parts = rel.parts  # path components relative to BASE_DIR
    filename = filepath.name

    doc_type = None
    paper_id = None
    topic_id = None
    status_override = False  # force needs_ocr regardless of char count

    # --- PYQ- paper 1 (ecoholics PYQ compilations) ---
    if rel_parts[0] == "PYQ- paper 1":
        # Official QP files inside this folder
        if any(filename.startswith(p) for p in QP_PATTERNS):
            doc_type = "official_qp"
            paper_id = "upsc_p1"
            status_override = True
        else:
            doc_type = "pyq_ecoholics"
            paper_id = "upsc_p1"

    # --- PYQ- Paper 2 (ecoholics PYQ compilations) ---
    elif rel_parts[0] == "PYQ- Paper 2":
        if any(filename.startswith(p) for p in QP_PATTERNS):
            doc_type = "official_qp"
            paper_id = "upsc_p2"
            status_override = True
        else:
            doc_type = "pyq_ecoholics"
            paper_id = "upsc_p2"

    # --- PYQs (solved PYQ documents) ---
    elif rel_parts[0] == "PYQs":
        doc_type = "pyq_solved"

    # --- Topper answers ---
    elif rel_parts[0] == "Topper answers":
        doc_type = "topper"
        status_override = True

    # --- Paper I notes (may be recursive) ---
    elif rel_parts[0] == "Paper I":
        doc_type = "notes"
        paper_id = "upsc_p1"
        mapped = NOTES_TOPIC_MAP.get(filename)
        if mapped:
            topic_id, paper_id = mapped

    # --- Paper II notes (may be recursive) ---
    elif rel_parts[0] == "Paper II":
        doc_type = "notes"
        paper_id = "upsc_p2"
        mapped = NOTES_TOPIC_MAP.get(filename)
        if mapped:
            topic_id, paper_id = mapped

    # --- Root-level files ---
    else:
        # Official question papers at root
        if any(filename.startswith(p) for p in QP_PATTERNS):
            doc_type = "official_qp"
            status_override = True
            fname_upper = filename.upper()
            if "PAPER I" in fname_upper or "PAPER-I" in fname_upper:
                paper_id = "upsc_p1"
            elif "PAPER II" in fname_upper or "PAPER-II" in fname_upper:
                paper_id = "upsc_p2"
        # Topper/tooper notes at root
        elif "tooper" in filename.lower() or "topper" in filename.lower():
            doc_type = "topper"
            status_override = True
        # Everything else at root: treat as notes
        else:
            doc_type = "notes"
            paper_id = None
            mapped = NOTES_TOPIC_MAP.get(filename)
            if mapped:
                topic_id, paper_id = mapped

    return {
        "doc_type": doc_type,
        "paper_id": paper_id,
        "topic_id": topic_id,
        "status_override": status_override,
    }


def analyse_pdf(filepath: Path) -> dict:
    """Open PDF with pdfplumber and collect page/char stats."""
    total_pages = 0
    extracted_pages = 0
    extractable_chars = 0

    try:
        with pdfplumber.open(str(filepath)) as pdf:
            total_pages = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text() or ""
                chars = len(text)
                if chars > 50:
                    extracted_pages += 1
                extractable_chars += chars
    except Exception as e:
        print(f"  [WARN] pdfplumber error on {filepath.name}: {e}")

    return {
        "total_pages": total_pages,
        "extracted_pages": extracted_pages,
        "extractable_chars": extractable_chars,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    summary: dict = defaultdict(lambda: {"count": 0, "total_pages": 0})
    inserted = 0
    skipped = 0
    errors = 0

    pdf_files = sorted(BASE_DIR.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files under {BASE_DIR}\n")

    for filepath in pdf_files:
        # Skip hidden/system files
        if filepath.name.startswith("."):
            continue

        try:
            doc_id = make_doc_id(filepath)

            # Idempotency check — skip if already registered
            cur.execute(
                "SELECT doc_id FROM source_documents WHERE doc_id = ?", (doc_id,)
            )
            if cur.fetchone():
                skipped += 1
                continue

            classification = classify_pdf(filepath)
            doc_type = classification["doc_type"]
            paper_id = classification["paper_id"]
            topic_id = classification["topic_id"]
            status_override = classification["status_override"]

            if doc_type is None:
                print(f"  [SKIP] Cannot classify: {filepath.relative_to(BASE_DIR)}")
                skipped += 1
                continue

            print(
                f"  Analysing [{doc_type}] {filepath.name} ...",
                end="",
                flush=True,
            )
            stats = analyse_pdf(filepath)
            print(f" {stats['total_pages']}p, {stats['extractable_chars']} chars")

            # Determine status
            if status_override or doc_type in ("topper", "official_qp"):
                status = "needs_ocr"
            elif stats["extractable_chars"] < 200:
                status = "needs_ocr"
            else:
                status = "indexed"

            cur.execute(
                """
                INSERT OR IGNORE INTO source_documents
                    (doc_id, exam_id, paper_id, topic_id, filename, doc_type,
                     file_path, total_pages, extracted_pages, extractable_chars, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    doc_id,
                    EXAM_ID,
                    paper_id,
                    topic_id,
                    filepath.name,
                    doc_type,
                    str(filepath),
                    stats["total_pages"],
                    stats["extracted_pages"],
                    stats["extractable_chars"],
                    status,
                ),
            )
            conn.commit()
            inserted += 1

            summary[doc_type]["count"] += 1
            summary[doc_type]["total_pages"] += stats["total_pages"]

        except Exception as e:
            print(f"\n  [ERROR] {filepath.name}: {e}")
            errors += 1

    conn.close()

    # Print summary table
    print("\n" + "=" * 55)
    print(f"{'doc_type':<22} {'count':>6} {'total_pages':>12}")
    print("-" * 55)
    for dt, vals in sorted(summary.items()):
        print(f"{dt:<22} {vals['count']:>6} {vals['total_pages']:>12}")
    print("=" * 55)
    print(f"\nNew records inserted  : {inserted}")
    print(f"Already present (skipped): {skipped}")
    if errors:
        print(f"Errors                : {errors}")


if __name__ == "__main__":
    main()
