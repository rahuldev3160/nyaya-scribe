"""
parse_mrunal_pyqs.py — Scrape Mrunal.org for all UPSC Mains GS1-4 PYQs (2013-2025).

Sources:
  GS1: https://mrunal.org/2021/10/download-topicwise-upsc-mains-general-studies-paper-1-gsm1.html
  GS2: https://mrunal.org/gsm2  (redirects to canonical URL)
  GS3: https://mrunal.org/gsm3
  GS4: https://mrunal.org/gsm4

Output: data/cache/upsc_gs_parsed_mrunal_{paper_id}.json per paper

Questions are in <blockquote> tags with inline marks "(10m,150 words)" and year "2024".
Topic sections use <h3>/<h2> headings for grouping (not stored in output — topic assignment
happens in seed_upsc_gs_pyqs.py via keyword matching).

Run: /opt/homebrew/bin/python3.11 scripts/parse_mrunal_pyqs.py
"""
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Mrunal canonical URLs for each GS paper
MRUNAL_URLS = {
    "gs1": "https://mrunal.org/2021/10/download-topicwise-upsc-mains-general-studies-paper-1-gsm1.html",
    "gs2": "https://mrunal.org/gsm2",
    "gs3": "https://mrunal.org/gsm3",
    "gs4": "https://mrunal.org/gsm4",
}

# Year range we care about
YEAR_MIN = 2013
YEAR_MAX = 2025

# --- Regex patterns ---
# Marks: "(10m,150w)" or "(10m, 150 words)" or "(15 marks, 250 words)"
MARKS_RE = re.compile(r"\((\d{1,2})\s*(?:m\b|marks?\b)[,\s]*(\d{2,3})\s*(?:w\b|words?\b)[^)]*\)", re.I)

# Word count only (no marks): "(150w)" "(150 words)"
WORDS_ONLY_RE = re.compile(r"\((\d{2,3})\s*(?:w\b|words?\b)\)", re.I)

# Year: standalone 4-digit year 2013-2025 as word boundary
YEAR_RE = re.compile(r"\b(20(?:1[3-9]|2[0-5]))\b")

# Hindi text (Devanagari block)
HINDI_RE = re.compile(r"[ऀ-ॿ]")

# GS4 case study trigger
CASE_STUDY_RE = re.compile(r"\bcase\s*study\b", re.I)


def _fetch_page(url: str) -> str | None:
    """Fetch a URL with retry on 429/503."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code in (429, 503):
                wait = (attempt + 1) * 5
                print(f"  RATE {resp.status_code} — wait {wait}s then retry")
                time.sleep(wait)
            else:
                print(f"  HTTP {resp.status_code} for {url}")
                return None
        except Exception as e:
            print(f"  ERR  {e} — attempt {attempt + 1}")
            time.sleep(3)
    return None


def _strip_hindi(text: str) -> str:
    """Remove Hindi translation (Devanagari block) from question text."""
    # Hindi usually appears in parentheses after the English text
    text = re.sub(r"\([^)]*[ऀ-ॿ][^)]*\)", "", text)
    # Also strip bare Devanagari words outside parens
    text = re.sub(r"[ऀ-ॿ।॥]+\s*", "", text)
    return text.strip()


def _extract_marks_and_year(text: str) -> tuple[int, int, int | None]:
    """
    Returns (marks, word_limit, year).
    If marks not found, infers from word count (150→10m, 250→15m).
    Year may be None if not found.
    """
    marks, word_limit = 10, 150  # defaults

    m = MARKS_RE.search(text)
    if m:
        marks = int(m.group(1))
        word_limit = int(m.group(2))
    else:
        w = WORDS_ONLY_RE.search(text)
        if w:
            word_limit = int(w.group(1))
            marks = 10 if word_limit <= 150 else 15

    years_found = YEAR_RE.findall(text)
    year = int(years_found[-1]) if years_found else None  # last year in text = exam year

    return marks, word_limit, year


def _clean_question_text(text: str) -> str:
    """Strip marks annotations, year, Hindi, and normalise whitespace."""
    text = _strip_hindi(text)
    text = MARKS_RE.sub("", text)
    text = WORDS_ONLY_RE.sub("", text)
    text = YEAR_RE.sub("", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip(" .,\n")
    return text


def _parse_page(html: str, paper_id: str, source_url: str) -> list[dict]:
    """Extract all questions from Mrunal page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    questions: list[dict] = []

    # Mrunal questions are in <blockquote> tags
    blockquotes = soup.find_all("blockquote")
    print(f"  FOUND {len(blockquotes)} blockquote elements")

    # Also look for questions in <p> tags that match question patterns
    # (older Mrunal pages may not use blockquote consistently)
    # We'll collect all candidate text elements
    candidate_elements = list(blockquotes)

    # If too few blockquotes, also try <li> and <p> containing year patterns
    if len(blockquotes) < 20:
        for tag in soup.find_all(["li", "p"]):
            txt = tag.get_text(" ", strip=True)
            if YEAR_RE.search(txt) and len(txt) > 40:
                candidate_elements.append(tag)

    seen_texts: set[str] = set()
    year_counter: dict[int, int] = {}
    no_year_count = 0

    for elem in candidate_elements:
        raw_text = elem.get_text(" ", strip=True)
        if len(raw_text) < 30:
            continue

        marks, word_limit, year = _extract_marks_and_year(raw_text)

        # Filter: must have a plausible year or be a lengthy question (>80 chars)
        if year is None:
            if len(raw_text) < 80:
                continue
            no_year_count += 1
            # Still include — year=None means we'll need to infer later

        if year is not None and not (YEAR_MIN <= year <= YEAR_MAX):
            continue

        clean_text = _clean_question_text(raw_text)
        if len(clean_text) < 25:
            continue

        # Dedup
        if clean_text in seen_texts:
            continue
        seen_texts.add(clean_text)

        if year is not None:
            year_counter[year] = year_counter.get(year, 0) + 1

        # GS4 case study detection
        is_case_study = paper_id == "gs4" and CASE_STUDY_RE.search(raw_text)

        questions.append({
            "paper_id": paper_id,
            "year": year,
            "question_number": None,  # assigned after sorting by year
            "question_text": clean_text,
            "marks": marks,
            "word_limit": word_limit,
            "source_url": source_url,
            "source_doc": f"mrunal_{paper_id}",
            **({"case_study_preamble": None} if is_case_study else {}),
        })

    # Sort by year (ascending) then assign sequential question numbers per year
    questions_with_year = [q for q in questions if q["year"] is not None]
    questions_without_year = [q for q in questions if q["year"] is None]

    questions_with_year.sort(key=lambda q: (q["year"], questions.index(q)))

    # Renumber: q01, q02, ... per year
    year_seq: dict[int, int] = {}
    for q in questions_with_year:
        yr = q["year"]
        year_seq[yr] = year_seq.get(yr, 0) + 1
        q["question_number"] = year_seq[yr]

    # Questions without year get appended without numbering for manual review
    for i, q in enumerate(questions_without_year, 1):
        q["question_number"] = 1000 + i  # sentinel so they're visually distinct

    all_questions = questions_with_year + questions_without_year

    print(f"  YEARS breakdown: {dict(sorted(year_counter.items()))}")
    if no_year_count:
        print(f"  WARN {no_year_count} questions had no year detected — numbered 1000+")

    return all_questions


def main():
    all_output: dict[str, list] = {}

    for paper_id, url in MRUNAL_URLS.items():
        print(f"\n{'='*60}")
        print(f"Fetching {paper_id.upper()} from {url}")
        html = _fetch_page(url)

        if html is None:
            print(f"  FAIL Could not fetch {url}")
            continue

        # Try redirect — Mrunal short URLs redirect to canonical
        # Check if the HTML has the actual content (look for blockquote density)
        if html.count("<blockquote") < 5:
            # Try alternate URL format
            alt_url = url.replace("mrunal.org/gsm", "mrunal.org/2021/10/download-topicwise-upsc-mains-general-studies-paper-")
            # Map paper num
            paper_num = {"gs1": "1-gsm1", "gs2": "2-gsm2", "gs3": "3-gsm3", "gs4": "4-gsm4"}[paper_id]
            alt_url = f"https://mrunal.org/2021/10/download-topicwise-upsc-mains-general-studies-paper-{paper_num}.html"
            print(f"  ALT  Trying {alt_url}")
            html2 = _fetch_page(alt_url)
            if html2 and html2.count("<blockquote") > html.count("<blockquote"):
                html = html2
                url = alt_url

        questions = _parse_page(html, paper_id, url)
        all_output[paper_id] = questions

        out_path = CACHE_DIR / f"upsc_gs_parsed_mrunal_{paper_id}.json"
        out_path.write_text(json.dumps(questions, indent=2, ensure_ascii=False))
        print(f"  SAVE {len(questions)} questions → {out_path.name}")

        time.sleep(3)  # polite delay

    print("\n" + "="*60)
    print("Mrunal scrape summary:")
    for paper_id, qs in all_output.items():
        yr_qs = [q for q in qs if q.get("year") and 2013 <= q["year"] <= 2024]
        print(f"  {paper_id.upper()}: {len(qs)} total | {len(yr_qs)} in 2013-2024 range")


if __name__ == "__main__":
    main()
