"""
ingest_gs2_pyqs_docx.py — Ingest real GS Mains Paper-II (GS2) PYQs, 2016-2025, from the
already-transcribed compilation at ~/Downloads/upsc-gs2-pyq-compilation.docx.

Context (BUG-035): gs1/gs2/gs3's pyq_questions rows were deleted 2026-09-16 as scraper junk.
gs4 (81 rows) is untouched and remains the only clean paper before this script runs.

Source verification (done manually before writing this script, not re-checked here):
  - .docx read via stdlib zipfile + xml.etree (no python-docx available in any local Python).
  - Real structure: 10 Word tables (one per year, 2025 down to 2016 in document order), each
    21 rows = 1 header row ("Q. No." / "Question Description..." / "Marks" / "Word Limit")
    + 20 question rows. No prose paragraphs contain question text — it is 100% table-only.
  - Spot-checked word-for-word against the real scanned papers: 2016 (all 20/20 questions),
    2025 (Q1-14), 2020 (Q1-4) — all matched exactly, including the 2016 outlier marking
    scheme (12.5 marks x 20, 200-word limit, vs. the 10/15-mark x 20, 150/250-word pattern
    used 2017-2025).

Topic assignment: starts from scripts/seed_upsc_gs_pyqs.py's existing KEYWORD_TOPIC_MAP (the
same one already used for gs4's 81 rows) — no new topic_id invented, only the 8 top-level
gs2_* ids already seeded in `topics`. That shared map alone left 96/200 (48%) of real GS2
questions unmatched, all dumped into one fallback bucket (gs2_constitution) — too coarse for
a topic-coverage tool (many were IR/governance/social-justice questions whose UPSC phrasing
just didn't hit the shared map's keywords, e.g. "Comptroller and Auditor General" without the
"(CAG)" abbreviation, "Non-Governmental Organizations" not containing the substring "ngo",
"Article 356" not matching the shared map's "art 356"). GS2_SUPPLEMENT below is a judgment
call, flagged explicitly for Rahul: additional keyword rules, manually derived by reading all
96 originally-unmatched questions, mapped only onto the same 7 top-level gs2_* topic_ids the
shared map itself uses (topic_level='topic' rows only — deliberately never a subtopic id like
gs2_fed_panchayati, because `upsc_bp.py`'s `_get_topics()` only lists topic_level='topic' rows
in the browse dropdown; a subtopic-tagged question would be unreachable from the normal UI).
It only fires when the shared map returns nothing. Cut the true fallback rate from 48% to 1.5%
(3/200, all of which are themselves a reasonable constitution-topic fit: Financial Emergency/
Art 360, Right of Movement/Art 19, one genuinely generic governance-discourse question) —
see script output for the exact final breakdown.

Run: /opt/homebrew/bin/python3.11 scripts/ingest_gs2_pyqs_docx.py [--dry-run]
"""
import hashlib
import re
import sqlite3
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "upsc_gs.db"
DOCX_PATH = Path.home() / "Downloads" / "upsc-gs2-pyq-compilation.docx"

sys.path.insert(0, str(Path(__file__).parent))
from seed_upsc_gs_pyqs import _assign_topic, _FALLBACK_TOPIC  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

# Table order in the document is 2025 -> 2016 (verified by walking body children in order).
YEARS_IN_DOC_ORDER = list(range(2025, 2015, -1))

EXAM_ID = "upsc_gs_mains"
PAPER_ID = "gs2"
SOURCE_TYPE = "official_pyq"

# Manually derived by reading all 96 questions the shared KEYWORD_TOPIC_MAP left unmatched.
# Only maps onto topic_ids that already exist in `topics` for paper_id='gs2'. First match wins.
GS2_SUPPLEMENT = [
    (["representation of the people act", "corrupt practice", "president's power to pardon",
      "preemptive pardon", "party system", "one nation - one election", "one nation one election",
      "electoral reform", "election commission", "model code of conduct", "electronic voting machine",
      "disqualif", "attorney-general", "attorney general", "president of india and france",
      "election of the president", "presidents of india and france"], "gs2_parliament_exec"),
    (["quasi-judicial", "national legal services authority", "legal aid", "human rights commission",
      "judicial systems in india", "converging as well as diverging"], "gs2_judiciary"),
    (["urban local bodies", "functions, functionaries and funds", "local institutions",
      "article 356", "regional parties", "state autonomy", "nature of federation",
      "cooperation, competition and confrontation"], "gs2_federalism"),
    (["civil society", "non-governmental organization", "non-governmental organisation",
      "pressure group", "central bureau of investigation", "comptroller and auditor general",
      "auditor general", "public charitable trust", "charitable trust", "gati-shakti", "gati shakti",
      "direct benefit transfer", "citizens' charter", "citizen's charter", "citizens charter",
      "public examination", "competition commission", "donor agenc", "community participation",
      "digital illiteracy", "liberalization", "liberalisation", "privatization", "privatisation",
      "bureaucra", "decision-making and problem-solving", "farmers' organisation",
      "farmers organisation", "policy-makers", "prevention of degradation", "neo-liberal paradigm",
      "multi-level planning"], "gs2_governance"),
    (["amartya sen", "primary education", "primary health", "national child policy", "child rights",
      "demographic dividend", "self-help group", "self help group", "microfinanc", "micro-finance",
      "poverty alleviation", "hunger", "malnutrition", "human resource development",
      "skill development", "vocational education", "earn while you learn", "women's social capital",
      "gender equity", "national commission for women", "reservation of seats for women",
      "rights of persons with disabilities", "free and compulsory education", "healthcare",
      "health for all", "geriatric", "maternal health", "sanitation and hygiene",
      "national education policy", "sustainable development goal", "human development",
      "social expenditure", "inequality in the ownership pattern", "paradox of poverty",
      "multidimensional poverty"], "gs2_social_justice"),
    (["shanghai cooperation organisation", "shanghai cooperation organization",
      "quadrilateral security dialogue", "central asian republic", "central asia",
      "maldives", "israel", "nuclear pact", "look east", "energy security", "japan",
      "globalization", "globalisation", "post-cold war", "sovereign nationalism",
      "leader of the oppressed", "counter terrorism", "counter-terrorism",
      "international maritime organisation", "international maritime organization",
      "geopolitical", "geostrategic", "india-africa", "digital partnership",
      "economic and social council", "africa's", "growth story"], "gs2_ir"),
]

# Short acronyms/tokens that need word-boundary matching to avoid false substring hits
# (e.g. bare "cag" would match inside unrelated words without \b).
GS2_SUPPLEMENT_TOKENS = [
    (["cbi"], "gs2_governance"),
    (["nhrc"], "gs2_governance"),
    (["ict"], "gs2_governance"),
    (["shg"], "gs2_social_justice"),
    (["rte"], "gs2_social_justice"),
    (["sco"], "gs2_ir"),
    (["quad"], "gs2_ir"),
    (["nato"], "gs2_ir"),
    (["i2u2"], "gs2_ir"),
    (["unsc"], "gs2_ir"),
    (["imo"], "gs2_ir"),
    (["who"], "gs2_ir"),
    (["cars"], "gs2_ir"),
]


def _gs2_supplement_topic(text: str, valid_topic_ids: set[str]) -> str | None:
    text_lower = text.lower()
    for keywords, topic_id in GS2_SUPPLEMENT:
        if topic_id in valid_topic_ids and any(kw in text_lower for kw in keywords):
            return topic_id
    for tokens, topic_id in GS2_SUPPLEMENT_TOKENS:
        if topic_id not in valid_topic_ids:
            continue
        if any(re.search(rf"\b{re.escape(tok)}\b", text_lower) for tok in tokens):
            return topic_id
    return None


def _cell_text(tc: ET.Element) -> str:
    parts = []
    for p in tc.findall("w:p", NS):
        ptext = "".join(t.text or "" for t in p.iter(W + "t"))
        parts.append(ptext)
    return "\n".join(parts).strip()


def parse_docx(path: Path) -> dict[int, list[dict]]:
    """Returns {year: [ {qno, text, marks, word_limit}, ... 20 entries ... ]}"""
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find("w:body", NS)
    tables = body.findall("w:tbl", NS)

    if len(tables) != len(YEARS_IN_DOC_ORDER):
        raise ValueError(
            f"Expected {len(YEARS_IN_DOC_ORDER)} tables (one per year), found {len(tables)}. "
            "Docx structure changed — re-verify before parsing."
        )

    result = {}
    for year, tbl in zip(YEARS_IN_DOC_ORDER, tables):
        rows = tbl.findall("w:tr", NS)
        header = [_cell_text(tc) for tc in rows[0].findall("w:tc", NS)]
        if header[:2] != ["Q. No.", "Question Description (English Transcribed Text)"]:
            raise ValueError(f"Unexpected header for year {year}: {header}")

        questions = []
        for tr in rows[1:]:
            cells = [_cell_text(tc) for tc in tr.findall("w:tc", NS)]
            if len(cells) != 4:
                raise ValueError(f"Year {year}: expected 4 cells, got {len(cells)}: {cells}")
            qno_raw, text, marks_raw, wl_raw = cells
            if not text:
                continue  # no fabrication — skip rather than invent
            questions.append({
                "qno": qno_raw,
                "text": text,
                "marks_raw": marks_raw.strip() or None,
                "word_limit_raw": wl_raw.strip() or None,
            })
        if len(questions) != 20:
            raise ValueError(f"Year {year}: expected 20 questions, parsed {len(questions)}.")
        result[year] = questions

    return result


def _parse_marks(marks_raw: str | None):
    """Return a numeric value (int or float) or None. Never guesses a value that isn't
    literally present in the source cell."""
    if not marks_raw:
        return None
    try:
        f = float(marks_raw)
    except ValueError:
        return None
    return int(f) if f.is_integer() else f


def build_rows(parsed: dict[int, list[dict]], valid_topic_ids: set[str],
               topic_meta: dict[str, tuple[str, str | None]]) -> list[tuple]:
    """topic_meta: {topic_id: (topic_level, subtopic_of)} for every gs2 topic_id in `topics`.

    Normalizes any subtopic-level assignment (topic_level='subtopic') up to its parent
    topic_id. Required because upsc_bp.py's _get_topics() only lists topic_level='topic'
    rows in the browse dropdown — a question left tagged with a subtopic id (e.g.
    gs2_fed_panchayati, which the *shared* KEYWORD_TOPIC_MAP itself targets for panchayat/ULB
    keywords, not just this script's supplement) would be real data but unreachable from the
    normal /upsc/mains UI flow. Applies uniformly regardless of which map produced the id.
    """
    rows = []
    stats = {"topic_assigned": 0, "topic_supplement": 0, "topic_fallback": 0, "subtopic_normalized": 0}
    for year, questions in sorted(parsed.items()):
        for seq, q in enumerate(questions, 1):
            question_id = f"{PAPER_ID}_{year}_q{seq:02d}"
            text = q["text"]
            marks = _parse_marks(q["marks_raw"])
            answer_length = q["word_limit_raw"]  # already "150 words" etc. verbatim from source

            topic_id = _assign_topic(text, PAPER_ID, valid_topic_ids)
            if topic_id:
                stats["topic_assigned"] += 1
            else:
                topic_id = _gs2_supplement_topic(text, valid_topic_ids)
                if topic_id:
                    stats["topic_supplement"] += 1
                else:
                    topic_id = _FALLBACK_TOPIC[PAPER_ID]
                    stats["topic_fallback"] += 1

            level, parent = topic_meta.get(topic_id, ("topic", None))
            if level == "subtopic" and parent:
                topic_id = parent
                stats["subtopic_normalized"] += 1

            q_hash = hashlib.sha256(text.encode()).hexdigest()

            rows.append((
                question_id, EXAM_ID, PAPER_ID, year, text, topic_id,
                marks, answer_length, q_hash, SOURCE_TYPE,
            ))
    return rows, stats


def main(dry_run: bool = False):
    if not DOCX_PATH.exists():
        print(f"Source docx not found: {DOCX_PATH}")
        sys.exit(1)
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        sys.exit(1)

    parsed = parse_docx(DOCX_PATH)
    print(f"Parsed {sum(len(v) for v in parsed.values())} questions across {len(parsed)} years: "
          f"{sorted(parsed.keys())}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row

    existing = conn.execute(
        "SELECT COUNT(*) c FROM pyq_questions WHERE exam_id=? AND paper_id=?",
        (EXAM_ID, PAPER_ID),
    ).fetchone()["c"]
    if existing:
        print(f"REFUSING: {existing} existing gs2 rows found — this script is additive-only "
              "and expects gs2 to be empty (per BUG-035). Investigate before re-running.")
        sys.exit(1)

    topic_rows = conn.execute(
        "SELECT topic_id, topic_level, subtopic_of FROM topics WHERE exam_id=? AND paper_id=?",
        (EXAM_ID, PAPER_ID),
    ).fetchall()
    valid_topic_ids = {r["topic_id"] for r in topic_rows}
    topic_meta = {r["topic_id"]: (r["topic_level"], r["subtopic_of"]) for r in topic_rows}
    print(f"Loaded {len(valid_topic_ids)} gs2 topic_ids from DB")

    rows, stats = build_rows(parsed, valid_topic_ids, topic_meta)

    print(f"\nBy year:")
    by_year_count = {}
    for r in rows:
        by_year_count[r[3]] = by_year_count.get(r[3], 0) + 1
    for yr in sorted(by_year_count):
        print(f"  {yr}: {by_year_count[yr]}")

    print(f"\nTopic assignment: {stats['topic_assigned']} shared-map keyword-matched, "
          f"{stats['topic_supplement']} gs2-supplement keyword-matched, "
          f"{stats['topic_fallback']} fell back to '{_FALLBACK_TOPIC[PAPER_ID]}' "
          f"({stats['subtopic_normalized']} of the above were subtopic ids normalized up to "
          f"their parent topic_id for dropdown reachability)")

    if dry_run:
        print("\n[DRY RUN] No rows written.")
        conn.close()
        return

    conn.executemany(
        "INSERT INTO pyq_questions "
        "(question_id, exam_id, paper_id, year, question_text, topic_id, "
        "marks, answer_length, question_hash, source_type) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()

    final_count = conn.execute(
        "SELECT COUNT(*) c FROM pyq_questions WHERE exam_id=? AND paper_id=?",
        (EXAM_ID, PAPER_ID),
    ).fetchone()["c"]
    print(f"\nInserted. gs2 now has {final_count} rows in pyq_questions.")
    conn.close()


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
