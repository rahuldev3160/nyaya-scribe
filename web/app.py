"""
Entry point — boots DBs and defines auth-aware navigation.
Run: /opt/homebrew/bin/streamlit run web/app.py
"""
import shutil as _shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import extra_streamlit_components as stx

from auth import validate_session
from db import get_conn

# ── First-boot: copy seed DBs if live DBs don't exist ────────────────────────
_DATA  = Path(__file__).parent.parent / "data"
_SEEDS = Path(__file__).parent.parent / "seeds"


def _boot_db(name: str) -> None:
    live = _DATA / f"{name}.db"
    seed = _SEEDS / f"{name}_seed.db"
    if live.exists():
        return
    if not seed.exists():
        st.error(
            f"**Database not found.**  \n"
            f"`data/{name}.db` is missing and `seeds/{name}_seed.db` was not found.  \n"
            f"Run `python3 scripts/setup_all.py` to initialise."
        )
        st.stop()
    try:
        _shutil.copy(seed, live)
    except Exception as _e:
        st.error(f"**Could not initialise {name}.db:** {_e}  \nCheck that `data/` is writable.")
        st.stop()


_boot_db("ies")
_boot_db("rbi")
_boot_db("upsc")

# ── Run DB migrations (idempotent) ────────────────────────────────────────────
# Add remember_me column to sessions if it doesn't exist yet (existing DBs).
try:
    import sqlite3 as _sqlite3
    _db_path = _DATA / "ies.db"
    if _db_path.exists():
        _mc = _sqlite3.connect(str(_db_path))
        try:
            _mc.execute("ALTER TABLE sessions ADD COLUMN remember_me INTEGER DEFAULT 0")
            _mc.commit()
        except Exception:
            pass  # Column already exists

        # English Practice tables (idempotent)
        try:
            _mc.executescript("""
                CREATE TABLE IF NOT EXISTS english_question_types (
                    type_id TEXT NOT NULL, exam_id TEXT NOT NULL DEFAULT 'english_practice',
                    type_name TEXT NOT NULL, description TEXT,
                    section_labels_json TEXT, section_weights_json TEXT,
                    rubric_type TEXT, sort_order INTEGER DEFAULT 0,
                    PRIMARY KEY (type_id, exam_id)
                );
                CREATE TABLE IF NOT EXISTS english_questions (
                    question_id TEXT NOT NULL, exam_id TEXT NOT NULL DEFAULT 'english_practice',
                    type_id TEXT NOT NULL, prompt_text TEXT NOT NULL,
                    marks INTEGER, word_guide_json TEXT, word_count_target INTEGER,
                    section_weights_json TEXT, intro_text TEXT, body_text TEXT,
                    conclusion_text TEXT, difficulty TEXT DEFAULT 'medium',
                    source_exam TEXT, created_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (question_id, exam_id)
                );
                CREATE TABLE IF NOT EXISTS english_keywords (
                    keyword_id TEXT NOT NULL, question_id TEXT NOT NULL,
                    exam_id TEXT NOT NULL DEFAULT 'english_practice',
                    section TEXT NOT NULL CHECK(section IN ('intro','body','conclusion')),
                    keyword TEXT NOT NULL, variants_json TEXT, weight INTEGER DEFAULT 1,
                    keyword_type TEXT DEFAULT 'required'
                        CHECK(keyword_type IN ('required','bonus','negative','phrase')),
                    fuzzy_threshold REAL DEFAULT 0.82, penalty REAL,
                    PRIMARY KEY (keyword_id, exam_id)
                );
                CREATE TABLE IF NOT EXISTS english_attempts (
                    attempt_id TEXT NOT NULL, exam_id TEXT NOT NULL DEFAULT 'english_practice',
                    user_id TEXT NOT NULL, question_id TEXT NOT NULL,
                    user_answer_intro TEXT, user_answer_body TEXT, user_answer_conclusion TEXT,
                    word_count_intro INTEGER DEFAULT 0, word_count_body INTEGER DEFAULT 0,
                    word_count_conclusion INTEGER DEFAULT 0,
                    score_intro REAL DEFAULT 0.0, score_body REAL DEFAULT 0.0,
                    score_conclusion REAL DEFAULT 0.0, auto_score REAL DEFAULT 0.0,
                    self_assess_score REAL DEFAULT 0.0,
                    keywords_matched_json TEXT, keywords_missed_json TEXT,
                    self_assess_json TEXT, session_id TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (attempt_id, exam_id)
                );
                CREATE INDEX IF NOT EXISTS idx_english_attempts_user
                    ON english_attempts(user_id, exam_id, created_at DESC);
            """)
            _mc.commit()
        except Exception:
            pass
        finally:
            _mc.close()
except Exception:
    pass

# ── Cookie bootstrap: restore session from persistent browser cookie ──────────
# CookieManager must be instantiated before st.navigation() so it renders its
# hidden component. get() returns None on the first render pass before cookies
# load — the None check below handles that gracefully without st.stop().
_cookie_manager = stx.CookieManager(key="main")
st.session_state["_cookie_mgr"] = _cookie_manager

if not st.session_state.get("session_token"):
    _cookie_token = _cookie_manager.get("de_session")
    if _cookie_token:
        _conn = get_conn()
        _user_id = validate_session(_conn, _cookie_token)
        _conn.close()
        if _user_id:
            st.session_state["session_token"] = _cookie_token
            st.session_state["user_id"] = _user_id
            st.rerun()

# ── Auth-aware navigation ─────────────────────────────────────────────────────
_authed = bool(st.session_state.get("session_token"))

_login         = st.Page("pages/0_Login.py",          title="Sign In",          icon=":material/login:")
_dashboard     = st.Page("pages/Dashboard.py",         title="IES Dashboard",    icon=":material/home:",           default=True)
_rbi_dash      = st.Page("pages/RBI_Dashboard.py",     title="RBI Dashboard",    icon=":material/account_balance:")
_upsc_dash     = st.Page("pages/UPSC_Dashboard.py",    title="UPSC Dashboard",   icon=":material/school:")
_ies_pyqs      = st.Page("pages/1_Model_Answers.py",   title="IES PYQs",         icon=":material/menu_book:")
_quiz          = st.Page("pages/2_Quiz.py",            title="Quiz",             icon=":material/edit_note:")
_study         = st.Page("pages/3_Study_Brief.py",     title="Study Brief",      icon=":material/description:")
_progress      = st.Page("pages/4_My_Progress.py",     title="My Progress",      icon=":material/bar_chart:")
_return_q      = st.Page("pages/5_Return_Quiz.py",     title="Return Quiz",      icon=":material/quiz:")
_rbi           = st.Page("pages/6_RBI_Prep.py",        title="RBI Prep",         icon=":material/quiz:")
_upsc          = st.Page("pages/7_UPSC_Mains.py",      title="UPSC Mains",       icon=":material/menu_book:")
_setup         = st.Page("pages/8_My_Setup.py",        title="My Setup",         icon=":material/tune:")
_answer_rev    = st.Page("pages/9_Answer_Review.py",   title="Answer Review",    icon=":material/rate_review:")
_profile       = st.Page("pages/10_Profile.py",        title="Profile",          icon=":material/person:")
_english       = st.Page("pages/11_English_Practice.py", title="English Practice", icon=":material/spellcheck:")

if not _authed:
    _pg = st.navigation([_login])
else:
    _pg = st.navigation({
        "Dashboards": [_dashboard, _rbi_dash, _upsc_dash],
        "Study":      [_ies_pyqs, _study, _upsc],
        "Practice":   [_quiz, _return_q, _rbi, _english],
        "Progress":   [_progress, _answer_rev],
        "Account":    [_setup, _profile],
    })

_pg.run()
