"""Seed ethics_concept_analysis and ethics_scenario_analysis from PLAN-019 research findings."""

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_gs.db"

CONCEPTS = [
    ("integrity",             "Integrity & Probity",              11, "A",    "high",   "stable"),
    ("civil_service_values",  "Civil Service Values",             10, "A",    "high",   "stable"),
    ("governance",            "Good Governance",                   9, "A",    "high",   "stable"),
    ("emotional_intelligence","Emotional Intelligence",            8, "A",    "high",   "stable"),
    ("corruption",            "Corruption & Anti-Corruption",      8, "A",    "high",   "stable"),
    ("aptitude",              "Attitude & Aptitude",               7, "A",    "high",   "stable"),
    ("laws_ethics",           "Laws vs Ethics",                    5, "A",    "medium", "stable"),
    ("conscience",            "Conscience",                        5, "A",    "medium", "stable"),
    ("conflict_of_interest",  "Conflict of Interest",              5, "both", "high",   "rising"),
    ("international_ethics",  "International Relations Ethics",    5, "A",    "medium", "stable"),
    ("constitutional_morality","Constitutional Morality",          4, "A",    "high",   "rising"),
    ("gender_equality",       "Gender Equality",                   4, "A",    "medium", "stable"),
    ("environmental_ethics",  "Environmental Ethics",              4, "A",    "medium", "stable"),
    ("digital_ethics",        "Digital & Tech Ethics",             4, "A",    "high",   "rising"),
    ("transparency",          "RTI & Whistleblowing Mechanisms",   5, "A",    "medium", "stable"),
]

SCENARIOS = [
    ("hierarchical_pressure",   "Hierarchical & Political Pressure",       18, "duty_vs_loyalty",        "high"),
    ("corruption_misuse",       "Corruption & Misuse of Office",           16, "integrity_vs_compliance", "high"),
    ("whistleblowing",          "Whistleblowing Dilemma",                  14, "duty_vs_loyalty",        "high"),
    ("duty_vs_personal",        "Official Duty vs Personal Obligation",    10, "duty_vs_compassion",     "high"),
    ("rules_vs_compassion",     "Rules vs Compassion",                      9, "rules_vs_outcomes",      "high"),
    ("gender_discrimination",   "Gender Discrimination & Harassment",        8, "rights_vs_institutional","medium"),
    ("private_sector",          "Private Sector Ethics",                    8, "profit_vs_ethics",       "medium"),
    ("development_environment", "Development vs Environment",               7, "progress_vs_ecology",    "high"),
    ("disaster_allocation",     "Disaster & Emergency Resource Allocation", 7, "triage_ethics",          "medium"),
    ("conflict_of_interest",    "Conflict of Interest",                     4, "personal_vs_public",     "high"),
]


def seed(conn, dry_run: bool) -> None:
    concept_inserted = 0
    concept_skipped = 0
    for (tag, label, freq, sec_pref, prob, trend) in CONCEPTS:
        if dry_run:
            concept_inserted += 1
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO ethics_concept_analysis "
            "(concept_tag, concept_label, frequency_count, section_preference, fy26_probability, trend) "
            "VALUES (?,?,?,?,?,?)",
            (tag, label, freq, sec_pref, prob, trend),
        )
        if cur.rowcount:
            concept_inserted += 1
        else:
            concept_skipped += 1

    scenario_inserted = 0
    scenario_skipped = 0
    for (stype, slabel, freq, dilemma, prob) in SCENARIOS:
        if dry_run:
            scenario_inserted += 1
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO ethics_scenario_analysis "
            "(scenario_type, scenario_label, frequency_count, core_dilemma_type, fy26_probability) "
            "VALUES (?,?,?,?,?)",
            (stype, slabel, freq, dilemma, prob),
        )
        if cur.rowcount:
            scenario_inserted += 1
        else:
            scenario_skipped += 1

    if not dry_run:
        conn.commit()

    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}ethics_concept_analysis: {concept_inserted} inserted, {concept_skipped} already existed")
    print(f"{prefix}ethics_scenario_analysis: {scenario_inserted} inserted, {scenario_skipped} already existed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ethics concept + scenario analysis tables")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be seeded without writing")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    try:
        seed(conn, dry_run=args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
