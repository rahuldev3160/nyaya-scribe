"""Auth blueprint — /auth/login, /auth/callback, /auth/logout."""
import secrets
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from auth import (
    build_auth_url, exchange_code, get_user_info,
    upsert_user, create_session, is_oauth_configured,
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if getattr(g, "user_id", None):
        return redirect(url_for("index"))

    auth_url = None
    if request.method == "POST" and is_oauth_configured():
        remember_me = request.form.get("remember_me") == "on"
        csrf = secrets.token_hex(16)
        state = f"{csrf}:{'1' if remember_me else '0'}"
        session["oauth_state"] = state
        auth_url = build_auth_url(state)
        return redirect(auth_url)

    return render_template(
        "login.html",
        oauth_configured=is_oauth_configured(),
    )


@auth_bp.route("/callback")
def callback():
    code = request.args.get("code")
    state = request.args.get("state", "")

    # CSRF validation — BUG-008 fix
    expected_state = session.pop("oauth_state", None)
    if not expected_state or not state:
        flash("Invalid sign-in request. Please try again.", "error")
        return redirect(url_for("auth.login"))
    if expected_state.split(":")[0] != state.split(":")[0]:
        flash("OAuth state mismatch. Possible CSRF. Please try again.", "error")
        return redirect(url_for("auth.login"))

    remember_me = state.endswith(":1")

    try:
        tokens = exchange_code(code)
        info = get_user_info(tokens["access_token"])
        user_id = upsert_user(
            g.conn,
            google_sub=info["sub"],
            email=info["email"],
            display_name=info.get("name"),
            avatar_url=info.get("picture"),
        )
        session_token = create_session(g.conn, user_id, remember_me=remember_me)

        session.clear()
        session["session_token"] = session_token
        session["user_id"] = user_id
        session["session_id"] = str(uuid4())
        if remember_me:
            session.permanent = True

        return redirect(url_for("index"))
    except Exception as exc:
        flash(f"Sign-in failed: {exc}", "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    token = session.get("session_token")
    if token:
        try:
            g.conn.execute("DELETE FROM sessions WHERE session_token=?", (token,))
            g.conn.commit()
        except Exception:
            pass
    session.clear()
    return redirect(url_for("auth.login"))
