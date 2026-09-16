"""Tests for the GS2 PYQ ingestion (scripts/ingest_gs2_pyqs_docx.py), added after BUG-035
deleted gs1/gs2/gs3's scraper-junk pyq_questions rows and a real, cross-verified source
(~/Downloads/upsc-gs2-pyq-compilation.docx) was ingested to re-populate gs2 only.

Not re-testing the docx parser itself here (that was validated by hand against the real
scanned UPSC papers before ingestion — see the script's own docstring). These tests confirm
the ingested rows are real, correctly shaped, and actually reachable through the existing
/upsc/mains route and question-detail route — i.e. that the data is usable by the live app,
not just present in the DB.
"""
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
UPSC_GS_DB = REPO_ROOT / "data" / "upsc_gs.db"


def _conn():
    conn = sqlite3.connect(UPSC_GS_DB)
    conn.row_factory = sqlite3.Row
    return conn


def test_gs2_has_exactly_200_rows_20_per_year_2016_to_2025():
    conn = _conn()
    total = conn.execute(
        "SELECT COUNT(*) c FROM pyq_questions WHERE exam_id='upsc_gs_mains' AND paper_id='gs2'"
    ).fetchone()["c"]
    assert total == 200

    by_year = dict(conn.execute(
        "SELECT year, COUNT(*) c FROM pyq_questions WHERE exam_id='upsc_gs_mains' AND paper_id='gs2' "
        "GROUP BY year"
    ).fetchall())
    conn.close()
    assert by_year == {y: 20 for y in range(2016, 2026)}


def test_gs2_rows_are_tagged_official_pyq_and_have_no_fabricated_gaps():
    conn = _conn()
    rows = conn.execute(
        "SELECT question_id, question_text, source_type, marks, answer_length "
        "FROM pyq_questions WHERE exam_id='upsc_gs_mains' AND paper_id='gs2'"
    ).fetchall()
    conn.close()
    assert len(rows) == 200
    for r in rows:
        assert r["source_type"] == "official_pyq"
        assert r["question_text"] and len(r["question_text"]) > 20
        # every row in this source had both a marks and word-limit value — no silent fabrication
        assert r["marks"] is not None
        assert r["answer_length"] is not None


def test_gs2_2016_marking_scheme_matches_source_outlier_year():
    """2016 used 12.5 marks x 20 (200-word limit) — different from 2017-2025's 10/15-mark
    pattern. Confirms the outlier year wasn't silently normalized/guessed."""
    conn = _conn()
    rows = conn.execute(
        "SELECT marks, answer_length FROM pyq_questions "
        "WHERE exam_id='upsc_gs_mains' AND paper_id='gs2' AND year=2016"
    ).fetchall()
    conn.close()
    assert len(rows) == 20
    assert all(r["marks"] == 12.5 for r in rows)
    assert all(r["answer_length"] == "200 words" for r in rows)


def test_gs2_topic_ids_are_all_top_level_and_reachable_via_dropdown():
    """Regression check for the subtopic-reachability bug found during ingestion:
    upsc_bp.py's _get_topics() only lists topic_level='topic' rows in the browse dropdown,
    so no gs2 pyq_questions row may be tagged with a subtopic id (e.g. gs2_fed_panchayati)."""
    conn = _conn()
    rows = conn.execute(
        """SELECT DISTINCT q.topic_id, t.topic_level FROM pyq_questions q
           JOIN topics t ON t.topic_id = q.topic_id AND t.exam_id = q.exam_id
           WHERE q.exam_id='upsc_gs_mains' AND q.paper_id='gs2'"""
    ).fetchall()
    conn.close()
    assert len(rows) > 0
    assert all(r["topic_level"] == "topic" for r in rows)


def test_gs2_sample_row_text_matches_source_exactly():
    """Spot-check against text hand-verified against the real scanned 2025/2016/2020 papers."""
    conn = _conn()
    row2025 = conn.execute(
        "SELECT question_text, marks, answer_length FROM pyq_questions WHERE question_id='gs2_2025_q11'"
    ).fetchone()
    row2016 = conn.execute(
        "SELECT question_text, marks FROM pyq_questions WHERE question_id='gs2_2016_q01'"
    ).fetchone()
    conn.close()

    assert row2025["question_text"].startswith(
        "Constitutional morality is the fulcrum which acts as an essential check"
    )
    assert row2025["marks"] == 15
    assert row2025["answer_length"] == "250 words"

    assert row2016["question_text"].startswith(
        "Discuss the essentials of the 69th Constitutional Amendment Act"
    )
    assert row2016["marks"] == 12.5


def test_gs1_and_gs3_untouched_still_empty():
    """BUG-035 left gs1/gs3 empty pending separate re-sourcing — this ingestion must not
    have touched them."""
    conn = _conn()
    gs1 = conn.execute("SELECT COUNT(*) c FROM pyq_questions WHERE paper_id='gs1'").fetchone()["c"]
    gs3 = conn.execute("SELECT COUNT(*) c FROM pyq_questions WHERE paper_id='gs3'").fetchone()["c"]
    gs4 = conn.execute("SELECT COUNT(*) c FROM pyq_questions WHERE paper_id='gs4'").fetchone()["c"]
    conn.close()
    assert gs1 == 0
    assert gs3 == 0
    assert gs4 == 81  # unchanged from before this session


def test_upsc_mains_route_lists_gs2_questions(client):
    """The existing /upsc/mains?paper=gs2 route (no code changes needed) must surface the
    newly-ingested rows. show_all=1 is required because the route's default view only shows
    questions with a generated model_answer, and gs2 has none yet (separate, later task)."""
    resp = client.get("/upsc/mains?paper=gs2&show_all=1")
    assert resp.status_code == 200
    assert b"gs2_" in resp.data
    assert b"/upsc/mains/q/gs2_" in resp.data


def test_gs2_question_detail_route_renders_real_question_text(client):
    resp = client.get("/upsc/mains/q/gs2_2025_q11")
    assert resp.status_code == 200
    assert b"Constitutional morality" in resp.data
