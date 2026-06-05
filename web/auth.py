"""Google OAuth helpers and session management."""
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _google_env() -> tuple[str, str, str]:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:8501/0_Login")
    return client_id, client_secret, redirect_uri


def is_oauth_configured() -> bool:
    client_id, client_secret, _ = _google_env()
    return bool(client_id and client_secret)


def build_auth_url(remember_me: bool = False) -> str:
    client_id, _, redirect_uri = _google_env()
    # Encode remember_me into the OAuth state so it survives the redirect.
    # Format: "<csrf_hex>:<0|1>"
    state = f"{secrets.token_hex(16)}:{'1' if remember_me else '0'}"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    client_id, client_secret, redirect_uri = _google_env()
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_user_info(access_token: str) -> dict:
    resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def upsert_user(conn: sqlite3.Connection, google_sub: str, email: str,
                display_name: str | None, avatar_url: str | None) -> str:
    """Create or update user, return internal user_id UUID."""
    row = conn.execute(
        "SELECT user_id FROM users WHERE google_sub=?", (google_sub,)
    ).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if row:
        user_id = row["user_id"]
        conn.execute(
            "UPDATE users SET email=?, display_name=?, avatar_url=?, last_seen_at=? WHERE user_id=?",
            (email, display_name, avatar_url, now, user_id),
        )
    else:
        user_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users (user_id, google_sub, email, display_name, avatar_url) VALUES (?,?,?,?,?)",
            (user_id, google_sub, email, display_name, avatar_url),
        )
    conn.commit()
    return user_id


def create_session(conn: sqlite3.Connection, user_id: str, remember_me: bool = False) -> str:
    """Create a session token. Expiry is 30 days if remember_me else 1 day.
    Multi-device: existing sessions for this user are preserved.
    Expired sessions across all users are pruned as housekeeping."""
    token = secrets.token_hex(32)
    days = 30 if remember_me else 1
    expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    conn.execute(
        "INSERT INTO sessions (session_token, user_id, expires_at, remember_me) VALUES (?,?,?,?)",
        (token, user_id, expires_at, int(remember_me)),
    )
    conn.execute(
        "DELETE FROM sessions WHERE expires_at < ?",
        (datetime.now(timezone.utc).isoformat(),),
    )
    conn.commit()
    return token


def validate_session(conn: sqlite3.Connection, token: str) -> str | None:
    """Return user_id if session token is valid and unexpired, else None."""
    if not token:
        return None
    row = conn.execute(
        "SELECT user_id, expires_at FROM sessions WHERE session_token=?", (token,)
    ).fetchone()
    if not row:
        return None
    expires = datetime.fromisoformat(row["expires_at"])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return None
    return row["user_id"]


def require_user(conn: sqlite3.Connection) -> str:
    """
    Return authenticated user_id. Clears session and reruns to login if not authenticated.
    Call at the top of every page that requires login.
    """
    import streamlit as st
    token = st.session_state.get("session_token")
    user_id = validate_session(conn, token)
    if user_id:
        st.session_state.user_id = user_id
        return user_id
    conn.close()
    st.session_state.pop("session_token", None)
    st.session_state.pop("user_id", None)
    st.rerun()
