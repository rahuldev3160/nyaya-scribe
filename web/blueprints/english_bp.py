import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, g, redirect, render_template, request, session, url_for
from auth import login_required
from db import get_conn, track_page_time
from scoring import RUBRICS, build_feedback, compute_self_assess_score, score_answer

english_bp = Blueprint("english_practice", __name__)

EXAM_ID = "english_practice"


def _load_types(conn):
    rows = conn.execute(
        "SELECT type_id, type_name, description, section_labels_json, section_weights_json, rubric_type, sort_order "
        "FROM english_question_types WHERE exam_id=? ORDER BY sort_order",
        (EXAM_ID,),
    ).fetchall()
    return [dict(r) for r in rows]


def _load_questions(conn, type_id):
    rows = conn.execute(
        "SELECT question_id, type_id, prompt_text, marks, word_guide_json, word_count_target, "
        "section_weights_json, intro_text, body_text, conclusion_text, difficulty, source_exam "
        "FROM english_questions WHERE exam_id=? AND type_id=? ORDER BY difficulty, question_id",
        (EXAM_ID, type_id),
    ).fetchall()
    return [dict(r) for r in rows]


def _load_keyword_schema(conn, question_id):
    rows = conn.execute(
        "SELECT section, keyword, variants_json, weight, keyword_type, fuzzy_threshold, penalty "
        "FROM english_keywords WHERE question_id=? AND exam_id=?",
        (question_id, EXAM_ID),
    ).fetchall()
    schema = {
        "intro":      {"required": [], "bonus": [], "negative": [], "phrases": []},
        "body":       {"required": [], "bonus": [], "negative": [], "phrases": []},
        "conclusion": {"required": [], "bonus": [], "negative": [], "phrases": []},
    }
    for row in rows:
        sec = row["section"]
        ktype = row["keyword_type"]
        entry = {
            "canonical": row["keyword"],
            "variants": json.loads(row["variants_json"] or f'["{row["keyword"]}"]'),
            "weight": float(row["weight"] or 1),
            "fuzzy_threshold": float(row["fuzzy_threshold"] or 0.82),
        }
        if row["penalty"] is not None:
            entry["penalty"] = float(row["penalty"])
        schema[sec][ktype].append(entry)
    return schema


def _save_attempt(conn, user_id, question_id, intro, body, conclusion, auto_result, self_checks, self_score):
    sections = auto_result.get("sections", {})
    nailed = [k for sec in sections.values() for k in sec.get("keywords_hit", [])]
    missed = [k for sec in sections.values() for k in sec.get("keywords_missed", [])]
    conn.execute(
        "INSERT INTO english_attempts "
        "(attempt_id,exam_id,user_id,question_id,user_answer_intro,user_answer_body,user_answer_conclusion,"
        "word_count_intro,word_count_body,word_count_conclusion,score_intro,score_body,score_conclusion,"
        "auto_score,self_assess_score,keywords_matched_json,keywords_missed_json,self_assess_json,session_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            uuid.uuid4().hex[:12], EXAM_ID, user_id, question_id,
            intro, body, conclusion,
            len(intro.split()), len(body.split()), len(conclusion.split()),
            round(sections.get("intro", {}).get("score_pct", 0) / 10, 2),
            round(sections.get("body",  {}).get("score_pct", 0) / 10, 2),
            round(sections.get("conclusion", {}).get("score_pct", 0) / 10, 2),
            round(auto_result.get("overall_pct", 0) / 10, 2),
            round(self_score, 4),
            json.dumps(nailed), json.dumps(missed), json.dumps(self_checks),
            session.get("eng_session_id", uuid.uuid4().hex[:8]),
        ),
    )
    conn.commit()


QUESTION_TYPES_SEED = [
    ("essay",   "Essay",                  "Extended analytical prose on a given topic.",                                                                          '{"intro":"Introduction","body":"Body","conclusion":"Conclusion"}', '{"intro":0.15,"body":0.70,"conclusion":0.15}', "essay",  1),
    ("précis",  "Précis Writing",         "Compress a passage to 1/3 length. Title in Intro, précis text in Body. Third person, no lifted phrases.",               '{"intro":"Title","body":"Précis","conclusion":""}',               '{"intro":0.10,"body":0.85,"conclusion":0.05}', "précis", 2),
    ("rc",      "Reading Comprehension",  "Answer a question based on the passage. Direct answer first. Passage content only — no external knowledge.",            '{"intro":"Answer","body":"Evidence","conclusion":"Inference"}',    '{"intro":0.20,"body":0.60,"conclusion":0.20}', "rc",     3),
    ("letter",  "Letter Writing",         "Formal letter: salutation, body paragraphs, proper closing. One of three options.",                                     '{"intro":"Opening","body":"Body","conclusion":"Closing"}',         '{"intro":0.15,"body":0.70,"conclusion":0.15}', "letter", 4),
    ("report",  "Report Writing",         "Official report: To/From/Date/Subject header, factual body, clear recommendations. Concise, no personal opinion.",      '{"intro":"Header","body":"Body","conclusion":"Recommendations"}',   '{"intro":0.15,"body":0.70,"conclusion":0.15}', "report", 5),
]


def _ensure_types_seeded(conn):
    for row in QUESTION_TYPES_SEED:
        conn.execute(
            "INSERT OR IGNORE INTO english_question_types "
            "(type_id, type_name, description, section_labels_json, section_weights_json, rubric_type, sort_order, exam_id) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (*row, EXAM_ID),
        )
    conn.commit()


@english_bp.route("/english/dashboard", methods=["GET"])
@login_required
def english_dashboard():
    conn = get_conn()
    user_id = g.user_id
    track_page_time(conn, "English Dashboard")
    _ensure_types_seeded(conn)

    all_types = _load_types(conn)
    type_map = {t["type_id"]: t for t in all_types}

    q_counts = {}
    for t in all_types:
        row = conn.execute(
            "SELECT COUNT(*) FROM english_questions WHERE exam_id=? AND type_id=?",
            (EXAM_ID, t["type_id"]),
        ).fetchone()
        q_counts[t["type_id"]] = row[0] if row else 0

    attempts_rows = conn.execute(
        "SELECT ea.attempt_id, ea.question_id, ea.auto_score, ea.self_assess_score, ea.created_at, "
        "       eq.type_id "
        "FROM english_attempts ea "
        "JOIN english_questions eq ON ea.question_id = eq.question_id "
        "WHERE ea.user_id=? AND ea.exam_id=? "
        "ORDER BY ea.created_at DESC",
        (user_id, EXAM_ID),
    ).fetchall()
    attempts = [dict(r) for r in attempts_rows]

    total_attempts = len(attempts)
    avg_auto = round(sum(a["auto_score"] or 0 for a in attempts) / total_attempts, 2) if total_attempts else 0
    avg_self = round(sum(a["self_assess_score"] or 0 for a in attempts) / total_attempts, 2) if total_attempts else 0

    by_type = {}
    for a in attempts:
        tid = a["type_id"]
        if tid not in by_type:
            by_type[tid] = {"count": 0, "auto_sum": 0.0, "self_sum": 0.0}
        by_type[tid]["count"] += 1
        by_type[tid]["auto_sum"] += a["auto_score"] or 0
        by_type[tid]["self_sum"] += a["self_assess_score"] or 0
    type_stats = []
    for t in all_types:
        tid = t["type_id"]
        d = by_type.get(tid, {"count": 0, "auto_sum": 0.0, "self_sum": 0.0})
        cnt = d["count"]
        type_stats.append({
            "type_id":  tid,
            "name":     t["type_name"],
            "count":    cnt,
            "avg_auto": round(d["auto_sum"] / cnt, 2) if cnt else 0,
            "avg_self": round(d["self_sum"] / cnt, 2) if cnt else 0,
        })

    recent = attempts[:5]

    return render_template(
        "english_dashboard.html",
        active_page="english_dashboard",
        all_types=all_types,
        q_counts=q_counts,
        total_attempts=total_attempts,
        avg_auto=avg_auto,
        avg_self=avg_self,
        type_stats=type_stats,
        recent=recent,
    )


@english_bp.route("/practice/english", methods=["GET"])
@login_required
def english_page():
    conn = get_conn()
    user_id = g.user_id
    track_page_time(conn, "English Practice")

    if request.args.get("reset") == "1":
        session.pop("eng_last_result", None)

    all_types = _load_types(conn)
    if not all_types:
        return render_template("english.html", active_page="english", no_content=True)

    curr_type = request.args.get("type", session.get("eng_curr_type", all_types[0]["type_id"]))
    if curr_type not in {t["type_id"] for t in all_types}:
        curr_type = all_types[0]["type_id"]
    session["eng_curr_type"] = curr_type

    questions = _load_questions(conn, curr_type)
    if not questions:
        return render_template("english.html", active_page="english",
                               no_questions=True,
                               all_types=[{"id": t["type_id"], "name": t["type_name"]} for t in all_types],
                               curr_type=curr_type)

    curr_qid = request.args.get("qid", session.get("eng_curr_qid", questions[0]["question_id"]))
    qids = [q["question_id"] for q in questions]
    if curr_qid not in qids:
        curr_qid = qids[0]
    session["eng_curr_qid"] = curr_qid

    selected_q = next(q for q in questions if q["question_id"] == curr_qid)
    qt_info = next(t for t in all_types if t["type_id"] == curr_type)
    rubric_type = qt_info.get("rubric_type", curr_type)
    criteria = RUBRICS.get(rubric_type, [])

    sec_labels = json.loads(qt_info.get("section_labels_json") or '{"intro":"Introduction","body":"Body","conclusion":"Conclusion"}')
    sec_weights = json.loads(selected_q.get("section_weights_json") or '{"intro":0.15,"body":0.70,"conclusion":0.15}')
    word_guide = json.loads(selected_q.get("word_guide_json") or '{"intro":80,"body":340,"conclusion":80}')

    last = session.get("eng_last_result")
    if last and last.get("qid") == curr_qid:
        phase = "done" if last.get("self_assess") is not None else "self_assess"
    else:
        phase = "write"

    type_opts = [{"id": t["type_id"], "name": t["type_name"]} for t in all_types]
    q_label_map = {
        q["question_id"]: f"{(q['source_exam'] or '').upper()} · {(q['difficulty'] or 'medium').capitalize()} · {q['prompt_text'][:55]}…"
        for q in questions
    }

    next_qid = qids[(qids.index(curr_qid) + 1) % len(qids)]
    diff_color = {"easy": "#81C995", "medium": "#FDD663", "hard": "#F28B82"}.get(
        selected_q.get("difficulty", "medium"), "#9AA0A6"
    )

    error = session.pop("eng_error", None)

    return render_template(
        "english.html",
        active_page="english",
        all_types=type_opts,
        curr_type=curr_type,
        questions=questions,
        curr_qid=curr_qid,
        selected_q=selected_q,
        qt_info=qt_info,
        sec_labels=sec_labels,
        sec_weights=sec_weights,
        word_guide=word_guide,
        criteria=criteria,
        phase=phase,
        last=last,
        next_qid=next_qid,
        diff_color=diff_color,
        q_label_map=q_label_map,
        error=error,
        no_content=False,
        no_questions=False,
    )


@english_bp.route("/practice/english/score", methods=["POST"])
@login_required
def english_score():
    conn = get_conn()
    curr_type = request.form.get("type_id", "essay")
    curr_qid = request.form.get("qid", "")
    intro = request.form.get("intro", "").strip()
    body = request.form.get("body", "").strip()
    conclusion = request.form.get("conclusion", "").strip()

    if not body:
        session["eng_error"] = "Please write at least a Body section before scoring."
        return redirect(url_for("english_practice.english_page", type=curr_type, qid=curr_qid))

    questions = _load_questions(conn, curr_type)
    selected_q = next((q for q in questions if q["question_id"] == curr_qid), None)
    if not selected_q:
        return redirect(url_for("english_practice.english_page", type=curr_type))

    qt_info_rows = _load_types(conn)
    qt_info = next((t for t in qt_info_rows if t["type_id"] == curr_type), {})
    sec_weights = json.loads(selected_q.get("section_weights_json") or '{"intro":0.15,"body":0.70,"conclusion":0.15}')

    kw_schema = _load_keyword_schema(conn, curr_qid)
    raw_result = score_answer(kw_schema, sec_weights, intro, body, conclusion)
    feedback = build_feedback(raw_result)

    session["eng_last_result"] = {
        "qid": curr_qid,
        "intro": intro,
        "body": body,
        "conclusion": conclusion,
        "auto": feedback,
        "self_assess": None,
    }
    return redirect(url_for("english_practice.english_page", type=curr_type, qid=curr_qid))


@english_bp.route("/practice/english/assess", methods=["POST"])
@login_required
def english_assess():
    conn = get_conn()
    curr_type = request.form.get("type_id", "essay")
    curr_qid = request.form.get("qid", "")

    qt_info_rows = _load_types(conn)
    qt_info = next((t for t in qt_info_rows if t["type_id"] == curr_type), {})
    rubric_type = qt_info.get("rubric_type", curr_type)
    criteria = RUBRICS.get(rubric_type, [])

    checks = {c["id"]: request.form.get(f"check_{c['id']}") == "1" for c in criteria}
    self_score = compute_self_assess_score(rubric_type, checks)

    last = session.get("eng_last_result", {})
    if last.get("qid") == curr_qid:
        try:
            _save_attempt(
                conn, g.user_id, curr_qid,
                last.get("intro", ""), last.get("body", ""), last.get("conclusion", ""),
                last.get("auto", {}), checks, self_score,
            )
        except Exception:
            pass
        last["self_assess"] = {"checks": checks, "score": self_score}
        session["eng_last_result"] = last

    return redirect(url_for("english_practice.english_page", type=curr_type, qid=curr_qid))
