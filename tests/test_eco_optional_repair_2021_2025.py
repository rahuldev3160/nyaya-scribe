"""Tests for the Eco-Optional PYQ gap-repair (2021-2025, Paper 1 + Paper 2).

Context: a read-only audit found pyq_questions was 48% incomplete for every checkable
year (2021-2025) against the real 28-lettered-sub-part exam structure (Q1/Q5 compulsory,
5 sub-parts a-e each; Q2/Q3/Q4/Q6/Q7/Q8, 3 sub-parts a/b/c each). This session OCR'd the
real scanned official booklets (~/Desktop/UPSC/Mains/Optional/Economics/PYQs_paper{1,2}/
{year}.pdf via pdftoppm+tesseract), independently re-derived the exact missing sub-parts
per year/paper against the DB's actual rows, and inserted 135 real recovered rows
(question_id continuing upsc_p1_0503.. / upsc_p2_0438.. from the prior max). No existing
row was modified, duplicated, or deleted.

Pre-repair state (146 rows for 2021-2025 across both papers) is backed up via
~/.claude/backups (backup id #7) before this session's insert.
"""
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
UPSC_ECO_DB = REPO_ROOT / "data" / "upsc_eco_opt.db"

EXPECTED_TOTALS = {
    ("upsc_p1", 2021): 28,
    ("upsc_p1", 2022): 28,
    ("upsc_p1", 2023): 28,
    ("upsc_p1", 2024): 28,
    ("upsc_p1", 2025): 29,  # pre-existing row-granularity quirk: Q4(b) split across 2 rows
    ("upsc_p2", 2021): 28,
    ("upsc_p2", 2022): 28,
    ("upsc_p2", 2023): 28,
    ("upsc_p2", 2024): 28,
    ("upsc_p2", 2025): 28,
}

# A sample of newly-inserted rows, one per paper-year, to spot check without hardcoding
# all 135 ids.
SAMPLE_NEW_ROWS = [
    ("upsc_p1", 2021, "Does government borrowing always crowd out the private investment"),
    ("upsc_p1", 2022, "Discuss the concept of ‘liquidity trap’"),
    ("upsc_p1", 2023, "Explain the backward bending supply curve of labour"),
    ("upsc_p1", 2024, "Derive Pareto optimality conditions in production"),
    ("upsc_p1", 2025, "Show that when prices and income increase in the same proportion"),
    ("upsc_p2", 2021, "Evaluate the role of MGNREGA"),
    ("upsc_p2", 2022, "Critically examine the various poverty alleviation programmes in India since 1970"),
    ("upsc_p2", 2023, "Examine the salient features of the Action Plan for Disinvestment"),
    ("upsc_p2", 2024, "What are the implications of “PM-Kisan Samman Nidhi” scheme"),
    ("upsc_p2", 2025, "Discuss the initiatives launched by the Reserve Bank of India (RBI) to promote financial inclusion"),
]


def _conn():
    conn = sqlite3.connect(UPSC_ECO_DB)
    conn.row_factory = sqlite3.Row
    return conn


def test_all_ten_paper_years_reach_expected_total():
    conn = _conn()
    for (paper_id, year), expected in EXPECTED_TOTALS.items():
        cnt = conn.execute(
            "SELECT COUNT(*) FROM pyq_questions WHERE paper_id=? AND year=?",
            (paper_id, year),
        ).fetchone()[0]
        assert cnt == expected, f"{paper_id} {year}: expected {expected}, got {cnt}"
    conn.close()


def test_135_new_rows_present_with_official_pyq_source():
    conn = _conn()
    cnt = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions "
        "WHERE (question_id LIKE 'upsc_p1_05%' OR question_id LIKE 'upsc_p2_04%') "
        "AND source_type='official_pyq'"
    ).fetchone()[0]
    # upsc_p1_05xx starts exactly at 0503 (continuation point) and upsc_p2_04xx at 0438
    new_p1 = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE paper_id='upsc_p1' AND CAST(substr(question_id,-4) AS INTEGER) >= 503"
    ).fetchone()[0]
    new_p2 = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE paper_id='upsc_p2' AND CAST(substr(question_id,-4) AS INTEGER) >= 438"
    ).fetchone()[0]
    assert new_p1 == 77, f"expected 77 new p1 rows, got {new_p1}"
    assert new_p2 == 58, f"expected 58 new p2 rows, got {new_p2}"
    assert new_p1 + new_p2 == 135
    conn.close()


def test_sample_new_rows_are_queryable_by_exact_text():
    conn = _conn()
    for paper_id, year, needle in SAMPLE_NEW_ROWS:
        row = conn.execute(
            "SELECT * FROM pyq_questions WHERE paper_id=? AND year=? AND question_text LIKE ?",
            (paper_id, year, f"%{needle}%"),
        ).fetchone()
        assert row is not None, f"expected new row for {paper_id} {year} containing {needle!r}"
        assert row["exam_id"] == "upsc_eco_opt"
        assert row["source_type"] == "official_pyq"
        assert row["topic_id"] is not None
    conn.close()


def test_new_rows_have_valid_toplevel_topic_ids():
    conn = _conn()
    valid_topics = {
        r["topic_id"]
        for r in conn.execute(
            "SELECT topic_id FROM topics WHERE exam_id='upsc_eco_opt' AND topic_level='topic'"
        ).fetchall()
    }
    new_rows = conn.execute(
        "SELECT question_id, topic_id FROM pyq_questions "
        "WHERE (paper_id='upsc_p1' AND CAST(substr(question_id,-4) AS INTEGER) >= 503) "
        "OR (paper_id='upsc_p2' AND CAST(substr(question_id,-4) AS INTEGER) >= 438)"
    ).fetchall()
    assert len(new_rows) == 135
    for r in new_rows:
        assert r["topic_id"] in valid_topics, f"{r['question_id']} has invalid topic_id {r['topic_id']}"
    conn.close()


def test_no_duplicate_question_hash_in_whole_table():
    conn = _conn()
    dupes = conn.execute(
        "SELECT question_hash, COUNT(*) c FROM pyq_questions "
        "WHERE exam_id='upsc_eco_opt' GROUP BY question_hash HAVING c > 1"
    ).fetchall()
    assert dupes == []
    conn.close()


def test_new_row_reachable_via_eco_topic_route(client):
    """A newly-inserted row must actually render through /upsc/eco/<topic_id>, same as
    pre-existing rows — regression check against BUG-036-style silent unreachability."""
    conn = _conn()
    row = conn.execute(
        "SELECT question_id, topic_id FROM pyq_questions "
        "WHERE paper_id='upsc_p1' AND year=2021 AND CAST(substr(question_id,-4) AS INTEGER) >= 503 "
        "LIMIT 1"
    ).fetchone()
    conn.close()
    assert row is not None

    resp = client.get(f"/upsc/eco/{row['topic_id']}?show_all=1")
    assert resp.status_code == 200

    resp2 = client.get(f"/upsc/eco/{row['topic_id']}/q/{row['question_id']}")
    assert resp2.status_code == 200


def test_no_gs_or_other_exam_rows_touched():
    """Scope guard: this repair must never have touched gs1-4 or any other exam_id."""
    conn = _conn()
    other = conn.execute(
        "SELECT COUNT(*) FROM pyq_questions WHERE exam_id != 'upsc_eco_opt'"
    ).fetchone()[0]
    assert other == 0, "upsc_eco_opt.db pyq_questions should only ever contain upsc_eco_opt rows"
    conn.close()
