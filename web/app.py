"""Flask app factory — entry point for gunicorn (web/wsgi.py)."""
import os
import secrets
import shutil
import sqlite3
import sys
import time
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, g, redirect, session

_DATA  = Path(__file__).parent.parent / "data"
_SEEDS = Path(__file__).parent.parent / "seeds"

_FEEDBACK_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS user_feedback (
        feedback_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'bug'
            CHECK(category IN ('bug','feature','issue','other')),
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT DEFAULT 'open'
            CHECK(status IN ('open','acknowledged','resolved')),
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_feedback_created
        ON user_feedback(created_at DESC);
"""

_ENGLISH_TABLES_SQL = """
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
"""


_RBI_KEY_DATA_SQL = """
    CREATE TABLE IF NOT EXISTS rbi_key_data (
        data_id TEXT PRIMARY KEY,
        section TEXT NOT NULL,
        section_color TEXT DEFAULT '#9AA0A6',
        section_sort INTEGER DEFAULT 0,
        item_name TEXT NOT NULL,
        item_value TEXT NOT NULL,
        item_note TEXT DEFAULT '',
        needs_verify INTEGER DEFAULT 0,
        is_must_know INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0
    );
"""

_RBI_KEY_DATA_SEED = [
    # LAF Corridor
    ("laf_01","LAF Corridor & Policy Rates","#8AB4F8",1,"Repo Rate","5.25%","MPC Feb 2026 kept unchanged. Cumulative 125 bps cuts since Feb 2025 (from 6.50%). MPC stance: Neutral.",0,1,1),
    ("laf_02","LAF Corridor & Policy Rates","#8AB4F8",1,"SDF Rate","5.00% (Repo − 25 bps)","Standing Deposit Facility (Apr 2022). LAF floor. Banks park surplus with RBI collateral-free.",0,0,2),
    ("laf_03","LAF Corridor & Policy Rates","#8AB4F8",1,"MSF Rate","5.50% (Repo + 25 bps)","Marginal Standing Facility. LAF ceiling. Banks borrow up to 3% of NDTL of SLR portfolio.",0,0,3),
    ("laf_04","LAF Corridor & Policy Rates","#8AB4F8",1,"Bank Rate","= MSF Rate","Rate for long-term advances outside LAF. Benchmark for penal rates.",0,0,4),
    ("laf_05","LAF Corridor & Policy Rates","#8AB4F8",1,"LAF Corridor width","±25 bps = 50 bps total","Symmetric: SDF (floor) ↔ Repo (signal) ↔ MSF (ceiling). Post-Apr 2022 structure.",0,0,5),
    ("laf_06","LAF Corridor & Policy Rates","#8AB4F8",1,"Reverse Repo","3.35% (superseded by SDF)","Exists in statute but SDF is the operative floor since Apr 2022. Exam trap: SDF ≠ reverse repo.",0,0,6),
    # Reserve Ratios & PSL
    ("rr_01","Reserve Ratios & PSL","#C084FC",2,"CRR","4% of NDTL","% of NDTL held as cash with RBI. No interest paid. RBI cut CRR injecting ₹2.5 lakh crore in FY26.",1,1,1),
    ("rr_02","Reserve Ratios & PSL","#C084FC",2,"SLR","18% of NDTL","% of NDTL held in approved G-secs/gold/cash. Banks borrow under MSF against SLR.",1,1,2),
    ("rr_03","Reserve Ratios & PSL","#C084FC",2,"Base for CRR & SLR","NDTL (Net Demand and Time Liabilities)","NDTL = Demand liabilities + Time liabilities − Inter-bank liabilities.",0,0,3),
    ("rr_04","Reserve Ratios & PSL","#C084FC",2,"PSL — domestic SCBs","40% of ANBC","Priority Sector Lending total. Sub-targets: Agriculture 18%, Micro enterprises 7.5%, Weaker sections 12%.",0,0,4),
    ("rr_05","Reserve Ratios & PSL","#C084FC",2,"Agriculture PSL sub-target","18% of ANBC","Of which ≥10% must go to Small & Marginal Farmers specifically.",0,0,5),
    # Banking Regulation
    ("brk_01","Banking Regulation & Asset Quality","#F28B82",3,"NPA trigger","90 days overdue","Interest/installment unpaid for 90 days → Sub-Standard NPA.",0,1,1),
    ("brk_02","Banking Regulation & Asset Quality","#F28B82",3,"NPA categories","Sub-standard → Doubtful → Loss","Sub-standard (<12 months) → Doubtful (12–36 months) → Loss (>3 yrs).",0,0,2),
    ("brk_03","Banking Regulation & Asset Quality","#F28B82",3,"CRAR minimum (India)","9% (Basel III global: 8%)","RBI mandates 9%. With CCB (2.5%) → effective minimum = 11.5%.",0,0,3),
    ("brk_04","Banking Regulation & Asset Quality","#F28B82",3,"Stressed assets","Gross NPA + Restructured Standard Assets","Broader than GNPA. Captures restructured loans that avoided NPA classification.",0,0,4),
    ("brk_05","Banking Regulation & Asset Quality","#F28B82",3,"PCA triggers","Net NPA > 6%; CRAR below threshold; ROA < 0 for 2 yrs","Prompt Corrective Action. Any one trigger → restrictions on dividends, lending, branches.",0,0,5),
    ("brk_06","Banking Regulation & Asset Quality","#F28B82",3,"IBC CIRP timeline","180 + 90 = 270 days max","Insolvency & Bankruptcy Code 2016. Time-bound NCLT process to maximise creditor recovery.",0,0,6),
    # Payment Infrastructure
    ("pay_01","Payment Infrastructure","#81C995",4,"RTGS","Min ₹2 lakh · Real-time · 24×7 · RBI","Real Time Gross Settlement. Instant gross settlement. No upper limit.",0,0,1),
    ("pay_02","Payment Infrastructure","#81C995",4,"NEFT","No minimum · 48 half-hourly batches · 24×7 · RBI","Deferred Net Settlement. Available 24×7 since Dec 2019.",0,0,2),
    ("pay_03","Payment Infrastructure","#81C995",4,"NPCI operates","UPI, IMPS, RuPay, NACH, FASTag, AePS, BBPS","Exam trap: RTGS and NEFT are RBI; UPI/IMPS etc. are NPCI.",0,0,3),
    ("pay_04","Payment Infrastructure","#81C995",4,"e-RUPI","Digital voucher — NOT CBDC","Person/purpose-specific prepaid e-voucher for targeted DBT. NPCI. Aug 2021.",0,0,4),
    ("pay_05","Payment Infrastructure","#81C995",4,"Digital Rupee (e₹)","CBDC — Central Bank Digital Currency","Legal tender issued by RBI. Retail pilot Nov 2022, Wholesale Dec 2022.",0,0,5),
    ("pay_06","Payment Infrastructure","#81C995",4,"NACH","Bulk recurring: salary/pension/EMI/utilities","National Automated Clearing House (NPCI). Replaced ECS.",0,0,6),
    # Fiscal Framework
    ("fis_01","Fiscal Framework","#FDD663",5,"GFD formula","Total Expenditure − Revenue Receipts − Non-debt Capital Receipts","Gross Fiscal Deficit = total borrowing requirement.",0,0,1),
    ("fis_02","Fiscal Framework","#FDD663",5,"GFD — FY26-27 BE","4.3% of GDP · ₹16,95,768 cr","Down from 4.4% (FY25-26 RE) and 4.8% (FY24-25 actual).",0,1,2),
    ("fis_03","Fiscal Framework","#FDD663",5,"Revenue Deficit — FY26-27 BE","1.5% of GDP","Revenue Expenditure − Revenue Receipts.",0,0,3),
    ("fis_04","Fiscal Framework","#FDD663",5,"Primary Deficit — FY26-27 BE","0.7% of GDP","GFD − Interest Payments. Declining (was 2.5% in FY22).",0,0,4),
    ("fis_05","Fiscal Framework","#FDD663",5,"Capital Expenditure — FY26-27 BE","₹12.21 lakh crore (+11.5%)","Highest ever. Effective capex = ₹17.1 lakh crore.",0,0,5),
    ("fis_06","Fiscal Framework","#FDD663",5,"States' share (16th FC)","41% (unchanged from 15th FC)","16th FC Chair: Dr Arvind Panagariya. Report tabled Feb 1, 2026.",0,0,6),
    ("fis_07","Fiscal Framework","#FDD663",5,"FRBM / debt anchor","GFD ≤ 3% · Debt: 50% ± 1% by 2031","Centre at 4.3%. 16th FC recommends 3.5% by 2030-31.",0,0,7),
    ("fis_08","Fiscal Framework","#FDD663",5,"Interest payments burden","26% of expenditure · 40% of revenue","₹14.04 lakh crore in FY26-27 BE.",0,0,8),
    # Indian Economy
    ("ine_01","Indian Economy — Quick Facts","#9AA0A6",6,"GDP rank by nominal size","4th globally (surpassed Japan)","Aspiration: 3rd by early 2030s.",0,0,1),
    ("ine_02","Indian Economy — Quick Facts","#9AA0A6",6,"Real GDP growth FY26","7.6% (2nd Advance Estimate)","FY25: 7.1%. FY27 projection: 6.8–7.2% (Economic Survey). Base: 2022-23.",0,1,2),
    ("ine_03","Indian Economy — Quick Facts","#9AA0A6",6,"GDP base year","2022-23 (revised from 2011-12)","MoSPI revised base year in FY26.",0,0,3),
    ("ine_04","Indian Economy — Quick Facts","#9AA0A6",6,"Headline CPI — FY26","1.7% · Core CPI: 4.3%","Sharp disinflation from food prices.",0,0,4),
    ("ine_05","Indian Economy — Quick Facts","#9AA0A6",6,"CPI base year","2024 (revised from 2012)","RBI targets CPI Combined at 4% ± 2% under FITF.",0,0,5),
    ("ine_06","Indian Economy — Quick Facts","#9AA0A6",6,"MPC inflation target","4% ± 2% (2%–6%) · FITF","FITF was effective until March 31, 2026. Verify if renewed.",1,0,6),
    ("ine_07","Indian Economy — Quick Facts","#9AA0A6",6,"Gross NPA ratio","2.2% (Sep 2025) — multi-decade low","Peak was 11.2% (March 2018). Bank credit growth: ~11.4% YoY.",0,0,7),
    ("ine_08","Indian Economy — Quick Facts","#9AA0A6",6,"RBI surplus transfer","₹2.68 lakh crore (FY25 — record)","27% higher than FY24 transfer. Under revised ECF (2025 review).",0,0,8),
    ("ine_09","Indian Economy — Quick Facts","#9AA0A6",6,"FI-Index (RBI)","67 in 2025 (↑24.3% since 2021)","Scale 0-100. Access (35%), Usage (45%), Quality (20%). Published annually in July.",0,0,9),
]


def _run_rbi_migrations() -> None:
    rbi_db_path = _DATA / "rbi.db"
    if not rbi_db_path.exists():
        return
    conn = sqlite3.connect(str(rbi_db_path))
    try:
        conn.executescript(_RBI_KEY_DATA_SQL)
        conn.commit()
        conn.executemany(
            "INSERT OR IGNORE INTO rbi_key_data "
            "(data_id,section,section_color,section_sort,item_name,item_value,item_note,needs_verify,is_must_know,sort_order) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            _RBI_KEY_DATA_SEED,
        )
        conn.commit()
    finally:
        conn.close()


def _boot_db(name: str) -> None:
    live = _DATA / f"{name}.db"
    seed = _SEEDS / f"{name}_seed.db"
    if live.exists():
        return
    if not seed.exists():
        raise RuntimeError(
            f"data/{name}.db missing and seeds/{name}_seed.db not found. "
            "Run python3 scripts/setup_all.py to initialise."
        )
    shutil.copy(seed, live)


def _run_migrations() -> None:
    db_path = _DATA / "ies.db"
    if not db_path.exists():
        return
    conn = sqlite3.connect(str(db_path))
    try:
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN remember_me INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            conn.executescript(_ENGLISH_TABLES_SQL)
            conn.commit()
        except Exception:
            pass
        try:
            conn.executescript(_FEEDBACK_TABLE_SQL)
            conn.commit()
        except Exception:
            pass
    finally:
        conn.close()


def _run_content_migrations() -> None:
    import importlib.util
    migrate_path = Path(__file__).parent.parent / "scripts" / "migrate.py"
    spec = importlib.util.spec_from_file_location("migrate", migrate_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

    _boot_db("ies")
    _boot_db("rbi")
    _boot_db("upsc")
    _boot_db("nyaya")
    _run_migrations()
    _run_rbi_migrations()
    _run_content_migrations()

    @app.context_processor
    def inject_globals():
        return {"current_user_id": getattr(g, "user_id", None)}

    @app.before_request
    def open_db():
        from db import _open_conn, _open_nyaya_conn
        from auth import validate_session
        g.request_start = time.time()
        g.conn = _open_conn()
        g.nyaya_conn = _open_nyaya_conn()
        g.user_id = None
        token = session.get("session_token")
        if token:
            g.user_id = validate_session(g.nyaya_conn, token)
            if not g.user_id:
                session.pop("session_token", None)

    @app.teardown_appcontext
    def close_db(exc):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()
        nyaya_conn = g.pop("nyaya_conn", None)
        if nyaya_conn is not None:
            nyaya_conn.close()

    from blueprints.auth_bp import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    from blueprints.dashboard_bp import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from blueprints.ies_answers_bp import ies_answers_bp
    app.register_blueprint(ies_answers_bp)

    from blueprints.ies_brief_bp import ies_brief_bp
    app.register_blueprint(ies_brief_bp)

    from blueprints.upsc_bp import upsc_bp
    app.register_blueprint(upsc_bp)

    from blueprints.ies_quiz_bp import ies_quiz_bp
    app.register_blueprint(ies_quiz_bp)

    from blueprints.ies_return_quiz_bp import ies_return_quiz_bp
    app.register_blueprint(ies_return_quiz_bp)

    from blueprints.rbi_prep_bp import rbi_prep_bp
    app.register_blueprint(rbi_prep_bp)

    from blueprints.rbi_dashboard_bp import rbi_dashboard_bp
    app.register_blueprint(rbi_dashboard_bp)

    from blueprints.upsc_dashboard_bp import upsc_dashboard_bp
    app.register_blueprint(upsc_dashboard_bp)

    from blueprints.progress_bp import progress_bp
    app.register_blueprint(progress_bp)

    from blueprints.setup_bp import setup_bp
    app.register_blueprint(setup_bp)

    from blueprints.profile_bp import profile_bp
    app.register_blueprint(profile_bp)

    from blueprints.english_bp import english_bp
    app.register_blueprint(english_bp)

    from blueprints.feedback_bp import feedback_bp
    app.register_blueprint(feedback_bp)

    @app.route("/")
    def index():
        if getattr(g, "user_id", None):
            return redirect("/dashboard")
        return redirect("/auth/login")

    return app
