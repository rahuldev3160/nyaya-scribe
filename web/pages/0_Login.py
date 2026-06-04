"""Google OAuth login page. Handles sign-in and the OAuth callback."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from db import get_conn
from auth import (
    build_auth_url, exchange_code, get_user_info,
    upsert_user, create_session, validate_session, is_oauth_configured,
)
from styles import apply_theme

st.set_page_config(page_title="Sign In — Exam Prep", page_icon="🔐", layout="centered")
apply_theme()

conn = get_conn()

# Already authenticated → go to dashboard
token = st.session_state.get("session_token")
if token and validate_session(conn, token):
    conn.close()
    st.rerun()

# OAuth callback: Google redirected back with ?code=...
params = st.query_params
if "code" in params:
    try:
        with st.spinner("Signing you in…"):
            tokens = exchange_code(params["code"])
            info = get_user_info(tokens["access_token"])
            user_id = upsert_user(
                conn,
                google_sub=info["sub"],
                email=info["email"],
                display_name=info.get("name"),
                avatar_url=info.get("picture"),
            )
            session_token = create_session(conn, user_id)
            _stale = [k for k in st.session_state
                      if k.startswith(("quiz_", "rq_", "rbi6_", "rbi_drill_"))]
            for k in _stale:
                del st.session_state[k]
            st.session_state.session_token = session_token
            st.session_state.user_id = user_id
            st.query_params.clear()
            conn.close()
            st.rerun()
    except Exception as exc:
        st.error(f"Sign-in failed: {exc}")
        st.query_params.clear()
else:
    # Show login UI
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("## 📚 Exam Prep")
        st.markdown("Sign in to track your progress across sessions.")
        st.markdown("<br>", unsafe_allow_html=True)

        if not is_oauth_configured():
            st.info(
                "**OAuth not configured.**  \n"
                "Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `OAUTH_REDIRECT_URI` "
                "environment variables to enable Google sign-in."
            )
        else:
            auth_url = build_auth_url()
            st.link_button("Sign in with Google", url=auth_url, use_container_width=True, type="primary")

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Your data is private and only used to track your study progress.")

conn.close()
