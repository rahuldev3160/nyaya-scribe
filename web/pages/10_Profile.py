"""User profile page — account info, contact details, study snapshot, and session management."""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from auth import require_user
from db import get_conn, track_page_time
from styles import apply_theme

st.set_page_config(page_title="Profile · Exam Prep", page_icon="👤", layout="centered")
apply_theme()

cookie_manager = st.session_state.get("_cookie_mgr")

conn = get_conn()
user_id = require_user(conn)
track_page_time(conn, "Profile")

# ── Ensure phone_number column exists ─────────────────────────────────────────
try:
    conn.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
    conn.commit()
except Exception:
    pass  # Column already exists — safe to ignore

# ── Load user row ──────────────────────────────────────────────────────────────
user = conn.execute(
    """SELECT display_name, email, avatar_url, created_at, subscription_tier,
              phone_number, exam_focus, exam_date, onboarding_completed
       FROM users WHERE user_id=?""",
    (user_id,),
).fetchone()

if not user:
    conn.close()
    st.error("Session error. Please log in again.")
    st.stop()

# ── Section 1: Account header ─────────────────────────────────────────────────
st.markdown("## Profile")

col_avatar, col_info = st.columns([1, 4])

with col_avatar:
    if user["avatar_url"]:
        st.image(user["avatar_url"], width=64)
    else:
        st.markdown(
            '<div style="width:64px;height:64px;border-radius:50%;background:#3C4043;'
            'display:flex;align-items:center;justify-content:center;'
            'font-size:1.6rem;color:#9AA0A6">👤</div>',
            unsafe_allow_html=True,
        )

with col_info:
    display_name = user["display_name"] or "User"
    email = user["email"] or ""
    st.markdown(f"### {display_name}")
    st.markdown(
        f'<div style="color:#9AA0A6;font-size:0.88rem">{email}</div>',
        unsafe_allow_html=True,
    )

    # Member since
    try:
        created_dt = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
        member_since = created_dt.strftime("Member since %d %b %Y")
    except Exception:
        member_since = "Member"
    st.markdown(
        f'<div style="color:#9AA0A6;font-size:0.82rem;margin-top:2px">{member_since}</div>',
        unsafe_allow_html=True,
    )

    # Subscription tier badge
    tier = (user["subscription_tier"] or "free").lower()
    if tier == "pro":
        badge_bg = "#3D2E00"
        badge_border = "#FDD663"
        badge_color = "#FDD663"
        badge_label = "Pro"
    else:
        badge_bg = "#2D2D2D"
        badge_border = "#5F6368"
        badge_color = "#9AA0A6"
        badge_label = "Free"
    st.markdown(
        f'<span style="background:{badge_bg};border:1px solid {badge_border};'
        f'color:{badge_color};border-radius:4px;padding:2px 8px;'
        f'font-size:0.75rem;font-weight:600;letter-spacing:.05em">{badge_label}</span>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Section 2: Contact details ────────────────────────────────────────────────
st.markdown("#### Contact details")
st.markdown(
    '<div style="color:#9AA0A6;font-size:0.82rem;margin-bottom:12px">'
    'Used only to send you exam reminders (optional)</div>',
    unsafe_allow_html=True,
)

current_phone = user["phone_number"] or ""
phone_input = st.text_input(
    "Phone number",
    value=current_phone,
    placeholder="+91 XXXXX XXXXX",
)

if st.button("Save", use_container_width=False):
    phone_val = phone_input.strip() or None
    conn.execute(
        "UPDATE users SET phone_number=? WHERE user_id=?",
        (phone_val, user_id),
    )
    conn.commit()
    st.success("Contact details saved.")

st.markdown("---")

# ── Section 3: Study snapshot ─────────────────────────────────────────────────
st.markdown("#### Study snapshot")

answers_graded = conn.execute(
    "SELECT COUNT(*) FROM descriptive_attempts WHERE user_id=?",
    (user_id,),
).fetchone()[0]

mcqs_attempted = conn.execute(
    "SELECT COUNT(*) FROM return_quiz_attempts WHERE user_id=?",
    (user_id,),
).fetchone()[0]


def _jl(s):
    if not s:
        return []
    try:
        r = json.loads(s)
        return r if isinstance(r, list) else []
    except Exception:
        return []


exam_focus_list = _jl(user["exam_focus"])
EXAM_LABELS = {"ies": "IES 2026", "rbi": "RBI DEPR", "upsc": "UPSC Eco Optional"}
focus_display = ", ".join(EXAM_LABELS.get(e, e) for e in exam_focus_list) if exam_focus_list else "Not set"

exam_date_raw = user["exam_date"]
if exam_date_raw:
    try:
        exam_dt = datetime.strptime(exam_date_raw, "%Y-%m-%d")
        exam_date_display = exam_dt.strftime("%d %b %Y")
    except Exception:
        exam_date_display = exam_date_raw
else:
    exam_date_display = "Not set"

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Answers graded", answers_graded)
with col2:
    st.metric("MCQs attempted", mcqs_attempted)
with col3:
    st.metric("Exam focus", focus_display)

if exam_date_raw and exam_date_raw != "Not set":
    st.markdown(
        f'<div style="color:#9AA0A6;font-size:0.82rem;margin-top:4px">'
        f'Target exam date: {exam_date_display}</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Section 4: Session / logout ───────────────────────────────────────────────
st.markdown("#### Session")

if st.button("Sign out", type="secondary"):
    # Delete only this device's session token, not all sessions for the user
    current_token = st.session_state.get("session_token")
    if current_token:
        conn.execute("DELETE FROM sessions WHERE session_token=?", (current_token,))
        conn.commit()
    cookie_manager.delete("de_session", key="delete_de_session")
    conn.close()
    st.session_state.clear()
    st.rerun()

conn.close()
