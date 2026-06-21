"""
Seed essay_frameworks, essay_hook_types, essay_theme_analysis into upsc_gs.db.
Run once after m039 migration.

Usage:
    python3 scripts/essay/seed_frameworks.py
    python3 scripts/essay/seed_frameworks.py --dry-run
"""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DB_PATH = ROOT / "data" / "upsc_gs.db"

FRAMEWORKS = [
    (
        "PESTLE",
        "PESTLE Analysis",
        json.dumps([
            {"slot": "P", "label": "Political"},
            {"slot": "E", "label": "Economic"},
            {"slot": "S", "label": "Social"},
            {"slot": "T", "label": "Technological"},
            {"slot": "L", "label": "Legal"},
            {"slot": "E2", "label": "Environmental"},
        ]),
        json.dumps(["governance", "economy", "technology", "digital_inequality", "federalism"]),
        json.dumps(["B"]),
    ),
    (
        "SPIDER",
        "SPIDER Framework",
        json.dumps([
            {"slot": "S", "label": "Social"},
            {"slot": "P", "label": "Political"},
            {"slot": "I", "label": "Institutional"},
            {"slot": "D", "label": "Developmental"},
            {"slot": "E", "label": "Economic"},
            {"slot": "R", "label": "Rights"},
        ]),
        json.dumps(["gender_justice", "development_inequality", "social_justice", "media_democracy"]),
        json.dumps(["B"]),
    ),
    (
        "IDEA",
        "IDEA Framework",
        json.dumps([
            {"slot": "I", "label": "Ideational"},
            {"slot": "D", "label": "Dialectical"},
            {"slot": "E", "label": "Ethical"},
            {"slot": "A", "label": "Aspirational"},
        ]),
        json.dumps(["values_ethics", "philosophy", "democracy", "science_aspiration"]),
        json.dumps(["A"]),
    ),
    (
        "PPF",
        "Past-Present-Future",
        json.dumps([
            {"slot": "PAST", "label": "Historical"},
            {"slot": "PRESENT", "label": "Contemporary"},
            {"slot": "FUTURE", "label": "Aspirational"},
        ]),
        json.dumps(["nature_environment", "philosophy", "geopolitics", "education"]),
        json.dumps(["A", "B"]),
    ),
    (
        "INDIVIDUAL_SOCIETY",
        "Individual and Society",
        json.dumps([
            {"slot": "I", "label": "Individual"},
            {"slot": "S", "label": "Society"},
        ]),
        json.dumps(["values_ethics", "philosophy", "social_justice"]),
        json.dumps(["A"]),
    ),
    (
        "CUSTOM",
        "Custom Framework",
        json.dumps([]),
        json.dumps([]),
        json.dumps(["A", "B"]),
    ),
]

HOOK_TYPES = [
    (
        "QUOTE",
        "Quotation",
        "Open with a direct quote from a thinker, leader, or literary figure.",
        'As [THINKER] once said, "[QUOTE]"',
        json.dumps(["values_ethics", "philosophy", "governance", "social_justice"]),
    ),
    (
        "DATA",
        "Statistic / Data Point",
        "Open with a striking number or empirical finding.",
        "According to [SOURCE], [STATISTIC] — a figure that demands urgent reflection.",
        json.dumps(["technology", "economy", "gender_justice", "education"]),
    ),
    (
        "HISTORICAL_FACT",
        "Historical Fact",
        "Open with a pivotal historical moment or turning point.",
        "When [EVENT] in [YEAR], it revealed [INSIGHT] that resonates to this day.",
        json.dumps(["governance", "values_ethics", "nature_environment", "geopolitics"]),
    ),
    (
        "CONTEMPORARY",
        "Contemporary Event",
        "Open with a recent current affairs event or development.",
        "In [YEAR], [EVENT] forced the world to confront [THEME] in ways previously unimagined.",
        json.dumps(["technology", "economy", "governance", "gender_justice"]),
    ),
    (
        "LITERARY_REF",
        "Literary / Philosophical Reference",
        "Open by invoking a poem, parable, myth, or philosophical text.",
        "[WORK] by [AUTHOR] begins with [REFERENCE] — a metaphor that illuminates our theme.",
        json.dumps(["values_ethics", "philosophy", "nature_environment", "education"]),
    ),
    (
        "RHETORICAL_Q",
        "Rhetorical Question",
        "Open with a provocative question that frames the essay's central tension.",
        "What does it mean to [ACTION] in an age when [PARADOX]?",
        json.dumps(["values_ethics", "philosophy", "technology", "democracy"]),
    ),
]

THEME_ANALYSIS = [
    (
        "values_ethics",
        "Philosophy of Values & Ethics",
        12,
        "A",
        json.dumps([2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]),
        json.dumps([
            {"year": 2024, "section": "A", "prompt": "There is no path to happiness; happiness is the path."},
            {"year": 2025, "section": "A", "prompt": "Truth knows no color."},
        ]),
        "India's Viksit Bharat 2047 discourse raises questions about what kind of nation we aspire to be — material prosperity alone or moral civilizational rise.",
        "stable",
        "high",
    ),
    (
        "technology",
        "Technology: Promise, Peril, Displacement",
        9,
        "both",
        json.dumps([2015, 2017, 2018, 2019, 2020, 2022, 2023, 2024, 2025]),
        json.dumps([
            {"year": 2024, "section": "B", "prompt": "Social media is triggering the Fear of Missing Out amongst the youth."},
        ]),
        "Generative AI adoption (ChatGPT, Gemini), India's Digital Public Infrastructure (UPI, ONDC, DPDP Act 2023), and Operation Sindoor drone warfare signal that tech-society tension is unavoidable in 2026.",
        "rising",
        "high",
    ),
    (
        "gender_justice",
        "Gender Justice & Women Empowerment",
        7,
        "B",
        json.dumps([2014, 2016, 2018, 2019, 2021, 2022, 2024]),
        json.dumps([
            {"year": 2022, "section": "B", "prompt": "The most important lesson in life is 'never give up.'"},
        ]),
        "Women's Reservation Act 2023 (33% seats in Lok Sabha/Assemblies) awaits delimitation trigger; Nari Shakti Vandan Adhiniyam implementation debate ongoing.",
        "stable",
        "medium",
    ),
    (
        "education",
        "Education: Purpose, Reform, Values",
        6,
        "both",
        json.dumps([2015, 2017, 2019, 2021, 2023, 2024]),
        json.dumps([
            {"year": 2024, "section": "A", "prompt": "The empires of the future will be the empires of the mind."},
        ]),
        "NEP 2020 full implementation ongoing; IIT/NIRF rankings and employability gap debate; AI in classrooms raises question: what is education FOR?",
        "stable",
        "medium",
    ),
    (
        "economy",
        "Economy: Growth, Inequality, Inclusion",
        6,
        "B",
        json.dumps([2014, 2016, 2018, 2020, 2022, 2025]),
        json.dumps([
            {"year": 2025, "section": "B", "prompt": "Contentment is natural wealth; luxury is artificial poverty."},
        ]),
        "India surpassed Japan as 4th largest economy; yet Oxford Multidimensional Poverty Index shows 230M still poor. Growth-inequality paradox is live.",
        "stable",
        "medium",
    ),
    (
        "governance",
        "Governance: Federalism, Institutions",
        5,
        "B",
        json.dumps([2016, 2018, 2020, 2022, 2024]),
        json.dumps([
            {"year": 2024, "section": "B", "prompt": "Nearly all men can stand adversity, but to test a man's character, give him power."},
        ]),
        "One Nation One Election debate; SC vs. executive tensions (collegium, electoral bonds); cooperative vs. competitive federalism in GST council.",
        "stable",
        "medium",
    ),
    (
        "nature_environment",
        "Nature, Environment & Civilization",
        5,
        "both",
        json.dumps([2015, 2018, 2020, 2022, 2024]),
        json.dumps([
            {"year": 2024, "section": "A", "prompt": "Forest precedes civilization and the desert follows them."},
        ]),
        "COP29 Baku pledges vs. India's coal dependency; heatwave deaths (2024 peak: 50.7°C in Rajasthan); biodiversity loss report (IPBES 2024).",
        "rising",
        "high",
    ),
]


def seed_frameworks(conn, dry_run: bool) -> None:
    rows = [
        (fw[0], fw[1], fw[2], fw[3], fw[4])
        for fw in FRAMEWORKS
    ]
    if dry_run:
        print(f"[dry-run] Would insert {len(rows)} rows into essay_frameworks:")
        for r in rows:
            print(f"  {r[0]} — {r[1]}")
        return
    conn.executemany(
        "INSERT OR IGNORE INTO essay_frameworks"
        " (framework_id, framework_name, slots_json, best_for_themes, typical_sections)"
        " VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()
    print(f"Seeded {len(rows)} rows into essay_frameworks")


def seed_hook_types(conn, dry_run: bool) -> None:
    rows = [
        (ht[0], ht[1], ht[2], ht[3], ht[4])
        for ht in HOOK_TYPES
    ]
    if dry_run:
        print(f"[dry-run] Would insert {len(rows)} rows into essay_hook_types:")
        for r in rows:
            print(f"  {r[0]} — {r[1]}")
        return
    conn.executemany(
        "INSERT OR IGNORE INTO essay_hook_types"
        " (hook_type_id, label, description, example_template, best_for_themes)"
        " VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()
    print(f"Seeded {len(rows)} rows into essay_hook_types")


def seed_theme_analysis(conn, dry_run: bool) -> None:
    rows = [
        (ta[0], ta[1], ta[2], ta[3], ta[4], ta[5], ta[6], ta[7], ta[8])
        for ta in THEME_ANALYSIS
    ]
    if dry_run:
        print(f"[dry-run] Would insert {len(rows)} rows into essay_theme_analysis:")
        for r in rows:
            print(f"  {r[0]} — {r[1]} (freq={r[2]}, prob_2026={r[8]})")
        return
    conn.executemany(
        "INSERT OR IGNORE INTO essay_theme_analysis"
        " (theme_tag, theme_label, frequency_count, typical_section,"
        "  year_appearances, example_questions, fy26_ca_hook, trend, probability_2026)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    print(f"Seeded {len(rows)} rows into essay_theme_analysis")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} does not exist. Run migrations first.")
        raise SystemExit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        seed_frameworks(conn, args.dry_run)
        seed_hook_types(conn, args.dry_run)
        seed_theme_analysis(conn, args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
