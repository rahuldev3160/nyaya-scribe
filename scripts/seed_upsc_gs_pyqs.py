"""
seed_upsc_gs_pyqs.py — Load all parsed PYQ JSONs into pyq_questions table in upsc_gs.db.

Input:  data/cache/upsc_gs_parsed_*.json  (from parse_mrunal_pyqs.py + parse_upsc_gs_pdfs.py)
Output: rows in data/upsc_gs.db pyq_questions table

Topic assignment: keyword matching against topics table.
  - topic_id=NULL is preferred over wrong assignment.
  - A Haiku batch pass (Phase 3) will refine assignments later.

Run: /opt/homebrew/bin/python3.11 scripts/seed_upsc_gs_pyqs.py
"""
import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "upsc_gs.db"
CACHE_DIR = ROOT / "data" / "cache"

# ---- Keyword → topic_id mapping ----
# Each entry: (list_of_keywords, topic_id)
# Keywords are matched case-insensitively against question_text.
# More-specific patterns are listed first; first match wins.
# topic_ids must exist in the topics table.

KEYWORD_TOPIC_MAP = [
    # === GS1 History ===
    (["art ", "culture", "painting", "sculpture", "architecture", "cave", "temple",
      "dance", "music", "theatre", "literature", "stupa", "gandhar", "chola",
      "mughal architecture", "indo-islamic", "craft", "handicraft", "folk art",
      "textile", "mural", "fresco", "harappan art", "mauryan art",
      "rajput painting", "miniature"], "gs1_culture"),
    (["colonial administration", "british expansion", "land revenue", "ryotwari",
      "mahalwari", "zamindari", "permanent settlement", "deindustrialisation",
      "drain of wealth", "economic impact of british", "british policy"], "gs1_mh_colonial"),
    (["revolt of 1857", "sepoy mutiny", "1857", "sipoy"], "gs1_mh_1857"),
    (["reform movement", "socio-religious", "brahmo", "arya samaj", "ram mohan",
      "ramakrishna", "dayananda", "vivekananda impact", "social reform",
      "widow remarriage", "sati", "child marriage", "depressed class"], "gs1_mh_socioreligious"),
    (["national movement", "freedom struggle", "independence movement",
      "congress", "swadeshi", "partition of bengal", "non-cooperation",
      "civil disobedience", "quit india", "salt march", "dandi"], "gs1_freedom_struggle"),
    (["gandhi", "gandhian", "satyagraha", "non-violence", "ahimsa",
      "civil disobedience movement", "non-cooperation movement"], "gs1_fs_gandhi"),
    (["women in freedom struggle", "women's role", "sarojini", "aruna",
      "peasant movement", "labour movement", "tribal revolt"], "gs1_fs_women"),
    (["bhagat singh", "revolutionary", "ina ", "subhas bose", "netaji",
      "azad hind", "revolutionary nationalism"], "gs1_fs_revolutionary"),
    (["partition", "communalism", "transfer of power", "mountbatten",
      "two-nation theory", "communal"], "gs1_fs_communalism"),
    (["princely states", "integration", "sardar patel", "hyderabad",
      "accession", "reorganisation of states", "linguistic states"], "gs1_post1947"),
    (["world war", "cold war", "non-alignment", "decolonisation",
      "imperialism", "colonialism", "fascism", "nazism", "communism",
      "russian revolution", "industrial revolution"], "gs1_world_history"),
    (["physiograph", "himalayas", "deccan", "western ghats", "eastern ghats",
      "coastal plain", "island", "relief feature", "landform"], "gs1_geo_physiography"),
    (["monsoon", "climate", "rainfall", "cyclone", "drought", "flood",
      "el nino", "la nina", "weather", "temperature", "season"], "gs1_geo_climate"),
    (["river", "drainage", "basin", "tributary", "himalayan river",
      "peninsular river", "ganga", "brahmaputra", "godavari", "krishna",
      "kaveri", "indus", "watershed"], "gs1_geo_drainage"),
    (["soil", "vegetation", "forest", "wildlife", "biome", "natural resource",
      "soil erosion", "soil type"], "gs1_geo_soils_veg"),
    (["earthquake", "tsunami", "volcanic", "seismic", "vulnerability"], "gs1_geo_disasters"),
    (["mineral", "energy resource", "oil", "coal", "natural gas",
      "renewable energy location", "mining", "distribution of resources"], "gs1_egeo_resources"),
    (["industry location", "industrial region", "iron steel", "textile industry",
      "industrial corridor"], "gs1_egeo_industries"),
    (["world geography", "ocean current", "plate tectonics", "coral reef",
      "climate zone", "biome world", "geomorphology", "erosion landform",
      "glacier", "continent", "globe"], "gs1_world_geo"),
    (["caste", "reservation", "social mobility", "sc st", "backward class",
      "untouchability", "jati"], "gs1_soc_caste"),
    (["women", "gender", "empowerment", "feminist", "patriarchy", "female",
      "girl child", "maternity"], "gs1_soc_women"),
    (["urbanisation", "population", "migration", "slum", "demographic",
      "fertility", "mortality", "poverty urban"], "gs1_soc_poverty_urban"),
    (["globalisation", "globalization", "cultural change", "westernisation",
      "modernisation", "secularism", "diversity"], "gs1_soc_diversity"),

    # === GS2 Polity ===
    (["constitution", "constitutional", "fundamental right", "dpsp",
      "fundamental duty", "basic structure", "amendment", "preamble",
      "directive principle", "article 21", "article 19", "part iii", "part iv"], "gs2_constitution"),
    (["parliament", "lok sabha", "rajya sabha", "legislative", "bill",
      "money bill", "budget session", "anti-defection", "parliamentary committee",
      "speaker", "zero hour", "question hour"], "gs2_parliament_exec"),
    (["judiciary", "supreme court", "high court", "judicial review",
      "pil ", "public interest litigation", "tribunal", "judicial independence",
      "collegium", "ngt ", "national green tribunal", "adr ", "lok adalat"], "gs2_judiciary"),
    (["federalism", "centre-state", "governor", "president's rule", "art 356",
      "finance commission", "gst council", "concurrent list", "state list",
      "union list", "cooperative federalism", "zonal council", "isc "], "gs2_federalism"),
    (["panchayat", "urban local body", "municipality", "ward", "73rd amendment",
      "74th amendment", "gram sabha", "devolution"], "gs2_fed_panchayati"),
    (["governance", "transparency", "accountability", "rti ", "right to information",
      "whistleblower", "grievance", "e-governance", "digital india", "dbt ",
      "cag ", "cvc ", "cec ", "regulatory body", "ombudsman", "civil service"], "gs2_governance"),
    (["welfare scheme", "social sector", "mgnrega", "pm-kisan", "ayushman",
      "nfsa", "pds ", "food security", "midday meal", "social justice",
      "vulnerable section", "disability", "minority", "obc",
      "health scheme", "education scheme", "nep "], "gs2_social_justice"),
    (["international relation", "foreign policy", "diplomacy", "bilateral",
      "neighbourhood first", "act east", "indo-pacific", "china", "pakistan",
      "bangladesh", "nepal", "sri lanka", "myanmar", "united states",
      "usa ", "russia", "european union", "asean", "brics", "g20 ",
      "un ", "wto ", "imf ", "world bank", "sco ", "quad ", "diaspora",
      "soft power", "hard power", "nuclear deal", "india's image"], "gs2_ir"),

    # === GS3 Economy ===
    (["gdp", "growth rate", "fiscal policy", "fiscal deficit", "budget",
      "taxation", "gst", "direct tax", "indirect tax", "niti aayog",
      "planning commission", "five year plan", "monetary policy",
      "rbi ", "repo rate", "inflation", "employment", "unemployment",
      "poverty", "inequality", "hdl", "inclusive growth", "fdi ",
      "balance of payment", "exchange rate", "current account", "forex",
      "banking", "npas", "financial inclusion"], "gs3_economy"),
    (["agriculture", "farmer", "crop", "green revolution", "msp ",
      "minimum support price", "irrigation", "kisan", "apmc",
      "food security", "buffer stock", "horticulture", "fisheries",
      "animal husbandry", "agri", "rural economy", "e-nam",
      "fpo ", "cooperative farming", "precision farming"], "gs3_agriculture"),
    (["infrastructure", "energy", "power sector", "renewable", "solar",
      "wind energy", "nuclear energy", "transport", "road", "railway",
      "port", "aviation", "smart city", "amrut", "housing", "ppp ",
      "national infrastructure", "logistics", "supply chain"], "gs3_infrastructure"),
    (["space", "isro", "chandrayaan", "gaganyaan", "satellite",
      "biotechnology", "gmo ", "crispr", "vaccine", "biosafety",
      "artificial intelligence", "ai ", "machine learning", "deepfake",
      "dpdp", "data protection", "cyber", "ipr ", "patent",
      "quantum", "nanotechnology", "defence technology", "missile",
      "science and technology", "scientific", "technology policy",
      "digital", "internet", "5g"], "gs3_science_tech"),
    (["environment", "ecology", "biodiversity", "wildlife", "species",
      "climate change", "paris agreement", "ndc ", "carbon",
      "greenhouse gas", "pollution", "plastic", "waste management",
      "eia ", "environmental impact", "forest right", "tribal",
      "ramsar", "cbd ", "cites", "wetland", "mangrove", "coral",
      "tiger", "elephant", "protected area", "national park"], "gs3_environment"),
    (["disaster", "flood", "drought", "cyclone disaster", "earthquake disaster",
      "ndma", "disaster management", "sendai", "early warning", "rescue",
      "relief", "rehabilitation", "sdma"], "gs3_disaster_mgmt"),
    (["naxal", "lwe", "left wing extremism", "maoist", "terrorism",
      "insurgency", "border management", "cyber security", "critical infrastructure",
      "money laundering", "organised crime", "pmla", "fatf",
      "internal security", "counter terrorism"], "gs3_internal_security"),

    # === GS4 Ethics ===
    (["utilitarianism", "consequentialism", "bentham", "mill", "deontology",
      "kant", "categorical imperative", "virtue ethics", "aristotle",
      "ethics theory", "normative ethics", "meta-ethics",
      "applied ethics", "environmental ethics", "biomedical ethics"], "gs4_ethics_foundations"),
    (["emotional intelligence", "goleman", "self-awareness", "empathy",
      "social skill", "self-regulation", "motivation ei"], "gs4_ei"),
    (["attitude", "cognitive bias", "groupthink", "persuasion",
      "propaganda", "moral disengagement", "prejudice", "stereotype"], "gs4_attitude"),
    (["human values", "family values", "honesty", "compassion",
      "integrity", "service", "value education", "role model"], "gs4_human_values"),
    (["civil service", "civil servant", "probity", "transparency",
      "accountability civil", "public service", "ias ", "ips ", "conduct rule",
      "government servant", "bureaucracy", "code of ethics",
      "whistleblowing", "corruption", "lok pal", "cvc ", "vigilance"], "gs4_civil_services"),
    (["gandhi ethics", "satyagraha ethics", "trusteeship", "means and ends",
      "vivekananda", "ambedkar", "kautilya", "chanakya", "tagore",
      "aristotle thinker", "plato", "rawls", "justice rawls",
      "moral thinker", "philosopher", "reformer ethical"], "gs4_thinkers"),
    (["case study", "ethical dilemma", "whistle blower", "hierarchy",
      "conscience", "public official", "subordinate", "superior officer",
      "ethical scenario", "stakeholder", "public trust",
      "administrator", "dilemma", "moral conflict"], "gs4_case_studies"),
]


def _build_topic_index(conn: sqlite3.Connection) -> dict[str, str]:
    """Load all topic_ids from DB keyed by topic_id (exam_id='upsc_gs_mains')."""
    rows = conn.execute("SELECT topic_id FROM topics WHERE exam_id='upsc_gs_mains'").fetchall()
    return {r[0]: r[0] for r in rows}


def _assign_topic(question_text: str, paper_id: str,
                  valid_topic_ids: set[str]) -> str | None:
    """Keyword-match question_text against KEYWORD_TOPIC_MAP.
    Only returns topic_ids that exist in the DB and match the paper.
    Returns None if no confident match."""
    text_lower = question_text.lower()

    for keywords, topic_id in KEYWORD_TOPIC_MAP:
        # Paper guard: topic must belong to this paper
        if not topic_id.startswith(paper_id + "_"):
            continue
        if topic_id not in valid_topic_ids:
            continue
        if any(kw in text_lower for kw in keywords):
            return topic_id

    return None  # prefer NULL over wrong assignment


# Fallback L1 topic when no keyword matches (topic_id is NOT NULL in schema)
_FALLBACK_TOPIC = {
    "gs1": "gs1_modern_history",
    "gs2": "gs2_constitution",
    "gs3": "gs3_economy",
    "gs4": "gs4_human_values",
}


def _make_question_id(paper_id: str, year: int, seq: int) -> str:
    """Generate canonical question_id: gs1_2024_q01"""
    return f"{paper_id}_{year}_q{seq:02d}"


def seed_from_file(conn: sqlite3.Connection, json_path: Path,
                   valid_topic_ids: set[str], dry_run: bool = False) -> dict:
    """Seed all questions from one parsed JSON file. Returns stats dict.

    Actual pyq_questions schema (as of m026+m027):
      question_id, exam_id, paper_id, year, question_text, topic_id,
      subtopic_id, marks, answer_length TEXT, question_hash UNIQUE,
      secondary_topic_ids, cross_paper_flag, answer_word_count,
      legal_provisions_flag, case_study_preamble, staleness_flag
    """
    questions = json.loads(json_path.read_text())
    inserted = skipped = topic_assigned = topic_fallback = 0

    # Group by year to assign stable sequential numbers
    by_year: dict[int, list] = defaultdict(list)
    for q in questions:
        yr = q.get("year")
        if yr and 2013 <= yr <= 2025:
            by_year[yr].append(q)

    for yr, year_qs in sorted(by_year.items()):
        for seq, q in enumerate(year_qs, 1):
            paper_id = q.get("paper_id")
            q_text = (q.get("question_text") or "").strip()
            marks = q.get("marks", 10)
            wl = q.get("word_limit") or (150 if marks == 10 else 250)
            answer_length = f"{wl} words"
            case_study_preamble = q.get("case_study_preamble")

            if not paper_id or not q_text or len(q_text) < 20:
                skipped += 1
                continue

            question_id = _make_question_id(paper_id, yr, seq)
            q_hash = hashlib.sha256(q_text.encode()).hexdigest()

            topic_id = _assign_topic(q_text, paper_id, valid_topic_ids)
            if topic_id:
                topic_assigned += 1
            else:
                topic_id = _FALLBACK_TOPIC.get(paper_id, f"{paper_id}_human_values")
                topic_fallback += 1

            if dry_run:
                inserted += 1
                continue

            conn.execute(
                "INSERT OR IGNORE INTO pyq_questions "
                "(question_id, exam_id, paper_id, year, question_text, topic_id, "
                "marks, answer_length, question_hash, case_study_preamble, staleness_flag) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (question_id, "upsc_gs_mains", paper_id, yr, q_text, topic_id,
                 marks, answer_length, q_hash, case_study_preamble, 0),
            )
            inserted += conn.execute("SELECT changes()").fetchone()[0]

    if not dry_run:
        conn.commit()

    return {
        "file": json_path.name,
        "inserted": inserted,
        "skipped": skipped,
        "topic_assigned": topic_assigned,
        "topic_null": topic_fallback,
    }


def main(dry_run: bool = False):
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    valid_topic_ids = set(_build_topic_index(conn).keys())
    print(f"Loaded {len(valid_topic_ids)} topic_ids from DB")

    # Discover all parsed JSON files
    json_files = sorted(CACHE_DIR.glob("upsc_gs_parsed_*.json"))
    if not json_files:
        print(f"No parsed JSON files found in {CACHE_DIR}")
        print("Run parse_mrunal_pyqs.py and/or parse_upsc_gs_pdfs.py first.")
        sys.exit(1)

    print(f"Found {len(json_files)} parsed files:\n  " + "\n  ".join(f.name for f in json_files))

    all_stats = []
    for json_path in json_files:
        stats = seed_from_file(conn, json_path, valid_topic_ids, dry_run=dry_run)
        all_stats.append(stats)
        prefix = "[DRY] " if dry_run else ""
        print(
            f"  {prefix}{stats['file']}: "
            f"inserted={stats['inserted']} "
            f"skipped={stats['skipped']} "
            f"topic_assigned={stats['topic_assigned']} "
            f"topic_null={stats['topic_null']}"
        )

    conn.close()

    # Summary
    total_inserted = sum(s["inserted"] for s in all_stats)
    total_skipped  = sum(s["skipped"]  for s in all_stats)
    total_assigned = sum(s["topic_assigned"] for s in all_stats)
    total_null     = sum(s["topic_null"]     for s in all_stats)

    print(f"\n{'='*60}")
    print(f"{'DRY RUN — ' if dry_run else ''}Total inserted:       {total_inserted}")
    print(f"Total skipped:        {total_skipped}")
    print(f"Topic assigned:       {total_assigned} ({total_assigned*100//(total_inserted or 1)}%)")
    print(f"Topic NULL:           {total_null}")

    if not dry_run:
        # Verification query
        conn2 = sqlite3.connect(DB_PATH)
        rows = conn2.execute(
            "SELECT paper_id, year, COUNT(*) FROM pyq_questions "
            "GROUP BY paper_id, year ORDER BY paper_id, year"
        ).fetchall()
        conn2.close()

        print(f"\nDB verification — pyq_questions by paper × year:")
        print(f"  {'paper_id':<8} {'year':<6} {'count'}")
        print(f"  {'-'*25}")
        for paper_id, year, count in rows:
            print(f"  {paper_id:<8} {year:<6} {count}")

        grand_total = sum(r[2] for r in rows)
        print(f"\n  GRAND TOTAL: {grand_total} questions in DB")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and count without writing to DB")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
