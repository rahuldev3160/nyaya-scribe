"""
Stage 7 (UPSC): Extract key economic data points from Economic Survey, Budget,
and RBI files and store in economic_data_points table.

Sources:
  1. data/rbi_current_data.txt  — parsed directly, no AI
  2. sources/ge_03/*.pdf        — Economic Survey PDFs, Haiku extraction
  3. sources/ge_04/*.pdf        — Budget PDFs, Haiku extraction

Run: python3 scripts/upsc/07_migrate_economic_data.py
"""
import json
import re
import sqlite3
from pathlib import Path

import anthropic
import pdfplumber

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_eco_opt.db"
EXAM_ID = "upsc_eco_opt"

RBI_FILE = Path(__file__).parent.parent.parent / "data" / "rbi_current_data.txt"

SURVEY_PDFS = [
    Path(__file__).parent.parent.parent / "sources" / "ge_03" / "Economic Survey 2024-25.pdf",
    Path(__file__).parent.parent.parent / "sources" / "ge_03" / "Economic Survey 2025-26.pdf",
]

BUDGET_PDFS = [
    Path(__file__).parent.parent.parent / "sources" / "ge_04" / "Budget_Highlights_2026.pdf",
    Path(__file__).parent.parent.parent / "sources" / "ge_04" / "Union_Budget_Analysis-2026-27.pdf",
]

HAIKU_MODEL = "claude-haiku-4-5-20251001"

HAIKU_SYSTEM = (
    "You are an economics data extractor. Return ONLY valid JSON. "
    "No markdown fences, no explanation."
)

HAIKU_PROMPT = (
    "Extract the 25 most important quantitative data points from this text. "
    "Return a JSON array where each item has keys: indicator, value, context, topic_tag. "
    "topic_tag must be one of: growth_composition, poverty_unemployment, agriculture, "
    "external_sector_bop, monetary_banking_india, public_finance_india, industry_services, "
    "current_topics\n\n"
    "Return ONLY the JSON array, no explanation.\n\n"
    "Text:\n__DOCUMENT_TEXT__"
)

VALID_TOPIC_TAGS = {
    "growth_composition",
    "poverty_unemployment",
    "agriculture",
    "external_sector_bop",
    "monetary_banking_india",
    "public_finance_india",
    "industry_services",
    "current_topics",
}


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS economic_data_points (
            data_id      TEXT PRIMARY KEY,
            exam_id      TEXT NOT NULL,
            topic_id     TEXT,
            category     TEXT NOT NULL,
            source       TEXT NOT NULL,
            indicator    TEXT NOT NULL,
            value        TEXT NOT NULL,
            year         INTEGER,
            context_text TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


def insert_data_point(
    conn: sqlite3.Connection,
    data_id: str,
    category: str,
    source: str,
    indicator: str,
    value: str,
    year,
    context_text,
    topic_id=None,
) -> bool:
    """Returns True if inserted (new), False if skipped (already exists)."""
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO economic_data_points
            (data_id, exam_id, topic_id, category, source, indicator, value,
             year, context_text)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (data_id, EXAM_ID, topic_id, category, source, indicator, value,
         year, context_text),
    )
    return cursor.rowcount > 0


# ── API key ───────────────────────────────────────────────────────────────────

def load_api_key() -> str:
    env_path = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("ANTHROPIC_API_KEY not found in Devthorium .env")


# ── JSON fence stripping (L-14) ───────────────────────────────────────────────

def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


# ── Source 1: RBI text file (no AI) ──────────────────────────────────────────

# Map section header keywords to (indicator_name, value_hint, topic_id)
SECTION_MAP = {
    "REPO RATE":               ("Repo Rate", "5.25%", "monetary_banking_india"),
    "SDF/REVERSE REPO":        ("SDF/Reverse Repo Rate", None, "monetary_banking_india"),
    "CRR":                     ("Cash Reserve Ratio (CRR)", None, "monetary_banking_india"),
    "SLR":                     ("Statutory Liquidity Ratio (SLR)", None, "monetary_banking_india"),
    "MPC/INFLATION TARGET":    ("Inflation Target (MPC)", "4% (±2%)", "monetary_banking_india"),
    "GDP GROWTH":              ("GDP Growth Rate", None, "growth_composition"),
    "GVA":                     ("Gross Value Added (GVA)", None, "growth_composition"),
    "CPI INFLATION":           ("CPI Inflation", None, "monetary_banking_india"),
    "WPI":                     ("Wholesale Price Index (WPI)", None, "monetary_banking_india"),
    "IIP":                     ("Index of Industrial Production (IIP)", None, "industry_services"),
    "FISCAL DEFICIT":          ("Fiscal Deficit", "4.4% of GDP (FY26)", "public_finance_india"),
    "REVENUE DEFICIT":         ("Revenue Deficit", "1.5% of GDP", "public_finance_india"),
    "PRIMARY DEFICIT":         ("Primary Deficit", None, "public_finance_india"),
    "CAPITAL EXPENDITURE":     ("Capital Expenditure", None, "public_finance_india"),
    "DISINVESTMENT":           ("Disinvestment Target", None, "public_finance_india"),
    "FRBM":                    ("FRBM Act Target", None, "public_finance_india"),
    "CURRENT ACCOUNT DEFICIT": ("Current Account Deficit", "0.8% of GDP H1FY26", "external_sector_bop"),
    "FOREX RESERVES":          ("Forex Reserves", None, "external_sector_bop"),
    "FDI":                     ("Foreign Direct Investment (FDI)", None, "external_sector_bop"),
    "EXCHANGE RATE":           ("Exchange Rate (INR/USD)", None, "external_sector_bop"),
    "TRADE":                   ("Merchandise Trade Balance", None, "external_sector_bop"),
    "NPA":                     ("Gross NPA (GNPA)", None, "monetary_banking_india"),
    "CREDIT GROWTH":           ("Bank Credit Growth", None, "monetary_banking_india"),
    "CRAR":                    ("Capital to Risk-Weighted Assets Ratio (CRAR)", "9% (RBI norm)", "monetary_banking_india"),
    "JAN DHAN":                ("PM Jan Dhan Beneficiaries", "56 crore", "current_topics"),
    "MUDRA":                   ("MUDRA (PMMY) Loans", None, "current_topics"),
    "UPI":                     ("UPI Transactions", None, "current_topics"),
    "EMPLOYMENT/UNEMPLOYMENT": ("Unemployment Rate (PLFS)", None, "poverty_unemployment"),
}


def _best_value(snippets: list, fallback) -> str:
    """Try to pull a meaningful numeric/percentage value from snippet texts."""
    pct_re = re.compile(r"\d+(?:\.\d+)?\s*(?:%|per\s*cent)", re.IGNORECASE)
    for snip in snippets:
        m = pct_re.search(snip)
        if m:
            return m.group(0).strip()
    inr_re = re.compile(r"[₹Rs\.]+\s*[\d,]+(?:\.\d+)?\s*(?:lakh\s+crore|crore)?", re.IGNORECASE)
    for snip in snippets:
        m = inr_re.search(snip)
        if m:
            return m.group(0).strip()
    if fallback:
        return fallback
    generic_re = re.compile(r"[\d,]+(?:\.\d+)?", re.IGNORECASE)
    for snip in snippets:
        m = generic_re.search(snip)
        if m and m.group(0).strip():
            return m.group(0).strip()
    return "See context"


def parse_rbi_file(path: Path) -> list:
    """Parse the RBI text file into a list of data-point dicts."""
    text = path.read_text(encoding="utf-8", errors="replace")

    # Split on section headers: ── SECTION NAME ───
    section_re = re.compile(r"^── (.+?) ─+$", re.MULTILINE)
    sections = []

    matches = list(section_re.finditer(text))
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        sections.append((header, body))

    records = []
    for header, body in sections:
        # Match header to SECTION_MAP
        matched_key = None
        for key in SECTION_MAP:
            if key in header:
                matched_key = key
                break
        if matched_key is None:
            continue

        indicator_name, value_hint, topic_id = SECTION_MAP[matched_key]

        snippets = [line.strip() for line in body.splitlines() if len(line.strip()) > 20][:3]
        context = " ".join(snippets)[:500] if snippets else body[:500]
        value = _best_value(snippets, value_hint)

        records.append({
            "indicator": indicator_name,
            "value": value,
            "context": context,
            "topic_id": topic_id,
        })

    return records


def migrate_rbi(conn: sqlite3.Connection) -> int:
    if not RBI_FILE.exists():
        print(f"  [RBI] File not found: {RBI_FILE}")
        return 0

    records = parse_rbi_file(RBI_FILE)
    inserted = 0
    source = "RBI DEPR Data 2026"

    for idx, rec in enumerate(records):
        data_id = f"rbi_rbi_depr_data_{idx:04d}"
        ok = insert_data_point(
            conn,
            data_id=data_id,
            category="rbi",
            source=source,
            indicator=rec["indicator"],
            value=rec["value"],
            year=2026,
            context_text=rec["context"],
            topic_id=rec["topic_id"],
        )
        if ok:
            inserted += 1

    conn.commit()
    print(f"  [RBI] Parsed {len(records)} indicators | Inserted {inserted} new")
    return inserted


# ── Source 2 & 3: PDF -> Haiku extraction ────────────────────────────────────

def extract_pdf_text(pdf_path: Path, max_pages: int = 30) -> str:
    """Extract text from the first max_pages of a PDF using pdfplumber."""
    pages_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if i >= max_pages:
                    break
                try:
                    t = page.extract_text() or ""
                    pages_text.append(t)
                except Exception as e:
                    print(f"    [PDF] Page {i+1} extract failed: {e}")
    except Exception as e:
        print(f"  [PDF] Could not open {pdf_path.name}: {e}")
        return ""
    return "\n".join(pages_text)


def call_haiku(client: anthropic.Anthropic, text: str) -> list:
    """Call Haiku to extract data points from text. Returns list of dicts."""
    if not text.strip():
        return []

    # Truncate to avoid exceeding token limits
    text = text[:80_000]

    prompt = HAIKU_PROMPT.replace("__DOCUMENT_TEXT__", text)

    try:
        resp = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=4096,
            system=HAIKU_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text
        raw = strip_fences(raw)
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        # Sometimes wrapped in an object
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
    except json.JSONDecodeError as e:
        print(f"    [Haiku] JSON parse error: {e}")
    except Exception as e:
        print(f"    [Haiku] API error: {e}")
    return []


def migrate_pdfs(
    conn: sqlite3.Connection,
    client: anthropic.Anthropic,
    pdf_paths: list,
    category: str,
    year,
) -> int:
    total_inserted = 0

    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            print(f"  [{category.upper()}] File not found: {pdf_path}")
            continue

        source_stem = pdf_path.stem.replace(" ", "_")[:40]
        source_label = pdf_path.stem

        print(f"  [{category.upper()}] Extracting text from {pdf_path.name}...")
        text = extract_pdf_text(pdf_path, max_pages=30)
        if not text.strip():
            print(f"    Empty text — skipping.")
            continue

        print(f"    Text extracted ({len(text):,} chars). Calling Haiku...")
        records = call_haiku(client, text)
        print(f"    Haiku returned {len(records)} data points.")

        inserted = 0
        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                continue
            indicator = str(rec.get("indicator", "")).strip()
            value = str(rec.get("value", "")).strip()
            context = str(rec.get("context", "")).strip()
            topic_tag = rec.get("topic_tag", "current_topics")

            if not indicator or not value:
                continue

            if topic_tag not in VALID_TOPIC_TAGS:
                topic_tag = "current_topics"

            data_id = f"{category}_{source_stem}_{idx:04d}"
            ok = insert_data_point(
                conn,
                data_id=data_id,
                category=category,
                source=source_label,
                indicator=indicator,
                value=value,
                year=year,
                context_text=context or None,
                topic_id=topic_tag,
            )
            if ok:
                inserted += 1

        conn.commit()
        total_inserted += inserted
        print(f"    Inserted {inserted} new data points from {pdf_path.name}")

    return total_inserted


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT category, source, COUNT(*) as cnt
        FROM economic_data_points
        WHERE exam_id = ?
        GROUP BY category, source
        ORDER BY category, source
    """, (EXAM_ID,)).fetchall()

    print("\n── Economic Data Points Summary ─────────────────────────────────────")
    print(f"  {'category':<15} {'source':<45} {'count':>6}")
    print(f"  {'─'*15} {'─'*45} {'─'*6}")
    for cat, src, cnt in rows:
        print(f"  {cat:<15} {src:<45} {cnt:>6}")

    total = conn.execute(
        "SELECT COUNT(*) FROM economic_data_points WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()[0]
    print(f"\n  Total data points : {total}")
    print("─────────────────────────────────────────────────────────────────────\n")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"DB not found at {DB_PATH}. Run init_db.py first.")
        raise SystemExit(1)

    print("Loading API key...")
    try:
        api_key = load_api_key()
    except Exception as e:
        print(f"Could not load API key: {e}")
        raise SystemExit(1)

    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()

    print("Ensuring economic_data_points table exists...")
    ensure_table(conn)

    # Source 1: RBI (no AI)
    print("\n[1/3] Migrating RBI data (direct parse)...")
    rbi_inserted = migrate_rbi(conn)

    # Source 2: Economic Survey PDFs
    print("\n[2/3] Migrating Economic Survey PDFs (Haiku)...")
    survey_inserted = migrate_pdfs(
        conn, client, SURVEY_PDFS, category="survey", year=None
    )

    # Source 3: Budget PDFs
    print("\n[3/3] Migrating Budget PDFs (Haiku)...")
    budget_inserted = migrate_pdfs(
        conn, client, BUDGET_PDFS, category="budget", year=2026
    )

    print(f"\nDone. RBI={rbi_inserted} | Survey={survey_inserted} | Budget={budget_inserted}")
    print_summary(conn)
    conn.close()
