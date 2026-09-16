"""Tests for the GS Mains attempt-submission flow (upsc_bp.py's mains_question /
mains_question_submit routes), added to extend PLAN-024 Phase 1's attempt-history pattern
to GS1-4.

Test fixture question: gs4_2025_q01 (paper_id='gs4', exam_id='upsc_gs_mains'). GS4 is the
only GS Mains paper with real, clean PYQs *and* generated model answers today — BUG-035
means gs1-3's PYQ bank is largely scraper junk (blog comments, download-link spam), so
those rows are deliberately not used as test fixtures here; fixing BUG-035 is out of scope.
"""
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
UPSC_GS_DB = REPO_ROOT / "data" / "upsc_gs.db"

GS4_QID = "gs4_2025_q01"  # real PYQ, has a generated model answer (m065 seed)


def test_gs4_question_detail_loads(client):
    resp = client.get(f"/upsc/mains/q/{GS4_QID}")
    assert resp.status_code == 200
    assert b"marks" in resp.data or b"Introduction" in resp.data


def test_gs_mains_question_not_found_handled_gracefully(client):
    resp = client.get("/upsc/mains/q/does_not_exist_12345")
    assert resp.status_code == 200
    assert b"Question not found." in resp.data


def test_gs4_submit_creates_attempt_row(client, cleanup_gs_attempts):
    user_id = cleanup_gs_attempts
    resp = client.post(
        f"/upsc/mains/q/{GS4_QID}/submit",
        data={
            "intro": "Officers face a genuine conflict between personal duty and professional obligation.",
            "body": "The case involves competing values of honesty, loyalty and public interest.",
            "conclusion": "A principled, transparent course of action balancing both duties is advisable.",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "attempt_id=" in resp.headers["Location"]

    conn = sqlite3.connect(UPSC_GS_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM descriptive_attempts WHERE user_id=? AND question_id=? AND exam_id='upsc_gs_mains'",
        (user_id, GS4_QID),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["user_answer_intro"].startswith("Officers face")
    assert row["input_mode"] == "typed"  # default; no photo/canvas input in this scope
    assert row["model_revealed"] == 0    # default; no explicit reveal flow for GS Mains (matches IES's pattern)
    assert row["word_count_body"] > 0


def test_gs4_detail_page_shows_attempt_history_after_submit(client, cleanup_gs_attempts):
    submit_resp = client.post(
        f"/upsc/mains/q/{GS4_QID}/submit",
        data={"intro": "intro text here", "body": "body text here", "conclusion": "conclusion text here"},
        follow_redirects=True,
    )
    assert submit_resp.status_code == 200
    assert b"Answer submitted" in submit_resp.data
    assert b"Attempt History (1)" in submit_resp.data

    # second attempt against the same question should extend, not replace, the history
    submit_resp_2 = client.post(
        f"/upsc/mains/q/{GS4_QID}/submit",
        data={"intro": "second attempt intro", "body": "second attempt body", "conclusion": "second attempt conclusion"},
        follow_redirects=True,
    )
    assert b"Attempt History (2)" in submit_resp_2.data


def test_gs_mains_browse_page_links_to_new_detail_route(client):
    resp = client.get("/upsc/mains?paper=gs4&show_all=1")
    assert resp.status_code == 200
    assert b"/upsc/mains/q/" in resp.data
