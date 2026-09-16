"""Tests for the Eco-Optional attempt-submission flow (upsc_eco_bp.py), added to extend
PLAN-024 Phase 1's attempt-history pattern to Eco-Optional. Before this, Eco-Optional had
only a topic-level dashboard (upsc_dashboard_bp.py) with no route to view a topic's actual
questions or submit an attempt against upsc_eco_opt.db's descriptive_attempts table.

Test fixture: upsc_p1_0001 (topic_id='advanced_micro', exam_id='upsc_eco_opt') — one of 908
real PYQs in this DB, all of which already have a generated model answer and a rubric row
(question_rubrics), unlike GS Mains gs1-3.
"""
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
UPSC_ECO_DB = REPO_ROOT / "data" / "upsc_eco_opt.db"

ECO_TOPIC = "advanced_micro"
ECO_QID = "upsc_p1_0001"


def test_eco_topic_page_lists_questions(client):
    resp = client.get(f"/upsc/eco/{ECO_TOPIC}")
    assert resp.status_code == 200
    assert f"/upsc/eco/{ECO_TOPIC}/q/".encode() in resp.data


def test_eco_topic_not_found_handled_gracefully(client):
    resp = client.get("/upsc/eco/does_not_exist_topic")
    assert resp.status_code == 200
    assert b"Topic not found." in resp.data


def test_eco_question_detail_loads(client):
    resp = client.get(f"/upsc/eco/{ECO_TOPIC}/q/{ECO_QID}")
    assert resp.status_code == 200
    assert b"market failure" in resp.data.lower() or b"Introduction" in resp.data


def test_eco_submit_creates_attempt_row(client, cleanup_eco_attempts):
    user_id = cleanup_eco_attempts
    resp = client.post(
        f"/upsc/eco/{ECO_TOPIC}/q/{ECO_QID}/submit",
        data={
            "intro": "Market failure occurs when resource allocation is inefficient.",
            "body": "Externalities, public goods and information asymmetry are key causes.",
            "conclusion": "Government intervention can correct these failures via taxes and regulation.",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "attempt_id=" in resp.headers["Location"]

    conn = sqlite3.connect(UPSC_ECO_DB)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM descriptive_attempts WHERE user_id=? AND question_id=? AND exam_id='upsc_eco_opt'",
        (user_id, ECO_QID),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row["user_answer_intro"].startswith("Market failure")
    assert row["input_mode"] == "typed"
    assert row["model_revealed"] == 0
    assert row["word_count_body"] > 0


def test_eco_detail_page_shows_attempt_history_after_submit(client, cleanup_eco_attempts):
    resp = client.post(
        f"/upsc/eco/{ECO_TOPIC}/q/{ECO_QID}/submit",
        data={"intro": "intro text", "body": "body text", "conclusion": "conclusion text"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Answer submitted" in resp.data
    assert b"Attempt History (1)" in resp.data


def test_eco_dashboard_topic_links_point_to_new_route_not_gs_mains(client):
    """Regression check: upsc_dashboard.html's Study/Write links and upsc_topic_state's
    redirect previously pointed at /upsc/mains (GS Mains, a different exam's DB entirely —
    a leftover from the S46 exam_id mixup). They must now point at /upsc/eco/<topic_id>.
    """
    resp = client.get("/upsc")
    assert resp.status_code == 200
    assert b"/upsc/eco/" in resp.data
