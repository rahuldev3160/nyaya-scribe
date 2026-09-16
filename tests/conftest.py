"""Shared pytest fixtures for the Descriptive Exams Flask app.

Runs against the real local dev DB files under data/ (this repo has no DB-path override
mechanism — see web/db.py, web/upsc_db.py, web/upsc_gs_db.py, all hardcode `data/*.db`).
Tests are additive-only: every fixture creates its own throwaway user/session/attempt rows
and deletes exactly those rows (by the ids it created) in teardown. No pre-existing row in
any DB is ever read for mutation, updated, or deleted by these tests.
"""
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WEB_DIR = REPO_ROOT / "web"
sys.path.insert(0, str(WEB_DIR))

NYAYA_DB = REPO_ROOT / "data" / "nyaya.db"
UPSC_GS_DB = REPO_ROOT / "data" / "upsc_gs.db"
UPSC_ECO_DB = REPO_ROOT / "data" / "upsc_eco_opt.db"


@pytest.fixture(scope="session")
def app():
    from app import create_app
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    return flask_app


@pytest.fixture()
def test_user():
    """Create a throwaway user + session in nyaya.db; yield (user_id, session_token);
    delete exactly those two rows (and any feature-usage row for this user) on teardown.
    """
    user_id = f"test-{uuid.uuid4().hex[:12]}"
    google_sub = f"test-google-sub-{uuid.uuid4().hex}"
    session_token = uuid.uuid4().hex

    conn = sqlite3.connect(NYAYA_DB)
    conn.execute(
        "INSERT INTO users (user_id, google_sub, email, display_name, subscription_tier) "
        "VALUES (?, ?, ?, ?, 'free')",
        (user_id, google_sub, f"{user_id}@nyaya.test", "Test User"),
    )
    expires_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    conn.execute(
        "INSERT INTO sessions (session_token, user_id, expires_at, remember_me) VALUES (?, ?, ?, 0)",
        (session_token, user_id, expires_at),
    )
    conn.commit()
    conn.close()

    yield user_id, session_token

    conn = sqlite3.connect(NYAYA_DB)
    conn.execute("DELETE FROM sessions WHERE session_token=?", (session_token,))
    conn.execute("DELETE FROM user_feature_usage WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM user_feature_overrides WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


@pytest.fixture()
def client(app, test_user):
    user_id, session_token = test_user
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["session_token"] = session_token
        c.test_user_id = user_id
        yield c


@pytest.fixture()
def cleanup_gs_attempts(test_user):
    """Delete descriptive_attempts rows this test's user creates in upsc_gs.db, on teardown."""
    user_id, _ = test_user
    yield user_id
    conn = sqlite3.connect(UPSC_GS_DB)
    conn.execute("DELETE FROM descriptive_attempts WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


@pytest.fixture()
def cleanup_eco_attempts(test_user):
    """Delete descriptive_attempts rows this test's user creates in upsc_eco_opt.db, on teardown."""
    user_id, _ = test_user
    yield user_id
    conn = sqlite3.connect(UPSC_ECO_DB)
    conn.execute("DELETE FROM descriptive_attempts WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
