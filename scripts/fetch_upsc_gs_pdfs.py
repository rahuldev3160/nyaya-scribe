"""
fetch_upsc_gs_pdfs.py — Phase A: Discover and attempt download of UPSC GS PDFs 2019-2024.

Primary: tries known upsc.gov.in URL patterns.
Falls through gracefully — marks quality=0 if PDF is scanned/unreadable.
Outputs: data/cache/upsc_gs_pdfs/manifest.json

Run: /opt/homebrew/bin/python3.11 scripts/fetch_upsc_gs_pdfs.py
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
CACHE_DIR = ROOT / "data" / "cache" / "upsc_gs_pdfs"
MANIFEST_PATH = CACHE_DIR / "manifest.json"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Known UPSC official PDF URL patterns to try for each paper × year.
# Pattern discovery: upsc.gov.in/sites/default/files/<filename>.pdf
# Multiple filename conventions are tried in order.
def _upsc_url_candidates(paper_num: int, year: int) -> list[str]:
    base = "https://upsc.gov.in/sites/default/files"
    # Common filename patterns observed in the wild
    candidates = [
        f"{base}/QP-CS-GS-{paper_num}-{year}.pdf",
        f"{base}/QP-CS-GS-I{'I' * (paper_num - 1)}-{year}.pdf",  # GS-I, GS-II, GS-III, GS-IV
        f"{base}/CS-GS{paper_num}-QP-{year}.pdf",
        f"{base}/CS-GS-{paper_num}-{year}.pdf",
        f"{base}/Mains-{year}-GS-{'I' * paper_num}.pdf",
        f"{base}/CSM-{year}-GS-{paper_num}.pdf",
    ]
    # Roman-numeral variants
    roman = ["I", "II", "III", "IV"][paper_num - 1]
    candidates += [
        f"{base}/QP-GS-{roman}-{year}.pdf",
        f"{base}/CS-Main-{year}-GS-Paper-{roman}.pdf",
        f"{base}/GS-{roman}-{year}.pdf",
    ]
    return candidates


PAPERS = [1, 2, 3, 4]
YEARS = list(range(2019, 2025))  # 2019-2024 inclusive


def _count_words_from_pdf(pdf_path: Path) -> int:
    """Run pdftotext and count words. Returns 0 if pdftotext unavailable or fails."""
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return 0
        return len(result.stdout.split())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 0


def _try_download(url: str, dest: Path) -> bool:
    """Download URL to dest. Returns True if file is a real PDF (starts with %PDF)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        if resp.status_code != 200:
            return False
        if not resp.content.startswith(b"%PDF"):
            return False
        dest.write_bytes(resp.content)
        return True
    except Exception:
        return False


def main():
    manifest = []
    existing = {}
    if MANIFEST_PATH.exists():
        for entry in json.loads(MANIFEST_PATH.read_text()):
            existing[(entry["paper_id"], entry["year"])] = entry

    paper_id_map = {1: "gs1", 2: "gs2", 3: "gs3", 4: "gs4"}

    for year in YEARS:
        for paper_num in PAPERS:
            paper_id = paper_id_map[paper_num]
            key = (paper_id, year)

            # Skip if already successfully downloaded
            if key in existing and existing[key].get("quality") == "text":
                print(f"  SKIP {paper_id} {year} — already have text-layer copy")
                manifest.append(existing[key])
                continue

            pdf_name = f"{paper_id}_{year}_official.pdf"
            dest = CACHE_DIR / pdf_name
            found = False

            for url in _upsc_url_candidates(paper_num, year):
                print(f"  TRY  {url}")
                if dest.exists():
                    dest.unlink()
                ok = _try_download(url, dest)
                if ok:
                    word_count = _count_words_from_pdf(dest)
                    # UPSC GS papers are 3 pages. <50 words/page = scanned
                    quality = "text" if word_count >= 150 else "scanned"
                    entry = {
                        "paper_id": paper_id,
                        "year": year,
                        "path": str(dest),
                        "source_url": url,
                        "quality": quality,
                        "word_count": word_count,
                    }
                    print(f"  GOT  {paper_id} {year} | {word_count} words | quality={quality}")
                    manifest.append(entry)
                    found = True
                    time.sleep(2)
                    break

            if not found:
                entry = {
                    "paper_id": paper_id,
                    "year": year,
                    "path": None,
                    "source_url": None,
                    "quality": "not_found",
                    "word_count": 0,
                }
                print(f"  MISS {paper_id} {year} — no URL pattern worked")
                manifest.append(entry)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written → {MANIFEST_PATH}")

    found_count = sum(1 for e in manifest if e["quality"] != "not_found")
    text_count  = sum(1 for e in manifest if e["quality"] == "text")
    print(f"Found: {found_count}/{len(manifest)} | Text-layer: {text_count}")


if __name__ == "__main__":
    main()
