"""
Descriptive quiz: write and get evaluated on IES PYQ answers.
Run: python3 scripts/quiz_descriptive.py --topic inflation_india
     python3 scripts/quiz_descriptive.py --id ge_04_0012
     python3 scripts/quiz_descriptive.py --paper ge_04 --random

Type your answer section by section. End each section with a blank line.
"""
import argparse
import json
import random
import sqlite3
import textwrap
import uuid
from pathlib import Path

import anthropic

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
EXAM_ID = "ies_2026"
USER_ID = "rahul"
WIDTH = 90

EVAL_SYSTEM = """You are an IES exam evaluator. Score a student's descriptive answer section by section against the marking rubric.

Return ONLY valid JSON:
{
  "intro_score": 0.0-1.0,
  "body_score": 0.0-1.0,
  "conclusion_score": 0.0-1.0,
  "overall_score": 0.0-1.0,
  "intro_feedback": "...",
  "body_feedback": "...",
  "conclusion_feedback": "...",
  "strengths": ["..."],
  "gaps": ["missing rubric points or terms not covered"],
  "examiner_tip": "one actionable tip to score higher"
}

Scoring rubric:
- intro_score: Did it define key concepts and frame the scope?
- body_score: Are rubric body-points covered? Is analysis present? Key terms used?
- conclusion_score: Is there a forward-looking/policy statement?
- overall_score: Weighted holistic score (intro=0.2, body=0.6, conclusion=0.2)
Be realistic and strict — IES is a competitive exam with high standards."""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_api_key() -> str:
    env_path = Path.home() / "Desktop" / "Claude Projects" / "Devthorium" / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise ValueError("ANTHROPIC_API_KEY not found")


def hr(char="─", width=WIDTH):
    print(char * width)


def wrap(text: str, indent=0):
    prefix = " " * indent
    print(textwrap.fill(text, width=WIDTH - indent, initial_indent=prefix, subsequent_indent=prefix))


def read_multiline(prompt: str) -> str:
    print(prompt)
    print("  (type your answer; press Enter twice to finish)\n")
    lines = []
    blank_count = 0
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            blank_count += 1
            if blank_count >= 2:
                break
            lines.append("")
        else:
            blank_count = 0
            lines.append(line)
    return "\n".join(lines).strip()


def pick_question(conn: sqlite3.Connection, question_id=None, topic_id=None, paper_id=None, use_random=False):
    if question_id:
        q = conn.execute(
            "SELECT * FROM pyq_questions WHERE question_id=? AND exam_id=?",
            (question_id, EXAM_ID)
        ).fetchone()
        if not q:
            print(f"Question {question_id} not found")
            raise SystemExit(1)
        return q

    clause_parts = ["q.exam_id=?"]
    params = [EXAM_ID]
    if topic_id:
        clause_parts.append("q.topic_id=?")
        params.append(topic_id)
    if paper_id:
        clause_parts.append("q.paper_id=?")
        params.append(paper_id)

    where = " AND ".join(clause_parts)

    if use_random:
        rows = conn.execute(
            f"SELECT * FROM pyq_questions WHERE {where} ORDER BY RANDOM() LIMIT 1", params
        ).fetchall()
    else:
        # Pick highest-marks recent question not yet attempted
        rows = conn.execute(f"""
            SELECT q.* FROM pyq_questions q
            LEFT JOIN descriptive_attempts da ON q.question_id=da.question_id AND q.exam_id=da.exam_id
                AND da.user_id=?
            WHERE {where} AND da.attempt_id IS NULL
            ORDER BY q.marks DESC, q.year DESC
            LIMIT 1
        """, [USER_ID] + params).fetchall()

        if not rows:
            # All attempted — pick highest marks
            rows = conn.execute(
                f"SELECT * FROM pyq_questions WHERE {where} ORDER BY marks DESC, year DESC LIMIT 1",
                params
            ).fetchall()

    if not rows:
        print("No questions found matching criteria")
        raise SystemExit(1)

    return rows[0]


def show_question(q, rubric):
    hr("═")
    marks_str = f"{q['marks']} marks" if q['marks'] else "marks unknown"
    wc = f" | {q['answer_length']} words" if q['answer_length'] else ""
    print(f"  {q['question_id']}  |  {q['year']}  |  {marks_str}{wc}  |  {q['topic_id']}")
    hr("═")
    print()
    wrap(q['question_text'])
    print()

    if rubric:
        hr()
        print("  Rubric hints:")
        rp = json.loads(rubric['rubric_points'])
        for p in rp:
            print(f"    [{p['section_hint']}/{p['category']}] {p['point']}")
        kt = json.loads(rubric['key_terms'])
        if kt:
            print(f"\n  Key terms: {', '.join(kt)}")
    hr()
    print()


def evaluate_answer(client, q, rubric, intro, body, conclusion, diagram_note):
    rubric_text = ""
    if rubric:
        rp = json.loads(rubric['rubric_points'])
        rubric_text = "Rubric points:\n" + "\n".join(
            f"  [{p['section_hint']}|wt={p['weight']}] {p['point']}" for p in rp
        )
        kt = json.loads(rubric['key_terms'])
        rubric_text += f"\n\nExpected key terms: {', '.join(kt)}"

    user_content = f"""Question ({q['marks'] or '?'} marks):
{q['question_text']}

{rubric_text}

Student's answer:

INTRO:
{intro or '[left blank]'}

BODY:
{body or '[left blank]'}

CONCLUSION:
{conclusion or '[left blank]'}

{"DIAGRAM NOTE: " + diagram_note if diagram_note else ""}"""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=EVAL_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except Exception:
        return None


def show_evaluation(ev, q, show_model_answer=True, conn=None):
    hr("═")
    overall = ev.get("overall_score", 0)
    grade = "EXCELLENT" if overall >= 0.85 else "GOOD" if overall >= 0.65 else "NEEDS WORK"
    print(f"  EVALUATION — {grade}  ({overall*100:.0f}/100)")
    hr("═")

    sections = [
        ("INTRO", "intro_score", "intro_feedback"),
        ("BODY", "body_score", "body_feedback"),
        ("CONCLUSION", "conclusion_score", "conclusion_feedback"),
    ]
    for label, score_key, fb_key in sections:
        score = ev.get(score_key, 0)
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        print(f"\n  {label}: {bar} {score*100:.0f}%")
        wrap(ev.get(fb_key, ""), indent=4)

    strengths = ev.get("strengths", [])
    if strengths:
        print("\n  Strengths:")
        for s in strengths:
            wrap(f"• {s}", indent=4)

    gaps = ev.get("gaps", [])
    if gaps:
        print("\n  Gaps / Missing:")
        for g in gaps:
            wrap(f"• {g}", indent=4)

    tip = ev.get("examiner_tip", "")
    if tip:
        print()
        hr("─")
        print("  EXAMINER TIP:")
        wrap(tip, indent=4)

    hr("─")

    if show_model_answer and conn:
        model_ans = conn.execute(
            "SELECT * FROM model_answers WHERE question_id=? AND exam_id=?",
            (q['question_id'], EXAM_ID)
        ).fetchone()

        if model_ans:
            show = input("\n  Show model answer? (y/n): ").strip().lower()
            if show == 'y':
                hr("═")
                print("  MODEL ANSWER")
                hr("═")
                print(f"\n  INTRO ({model_ans['wc_intro']}w):")
                wrap(model_ans['intro_text'], indent=2)
                print(f"\n  BODY ({model_ans['wc_body']}w):")
                wrap(model_ans['body_text'], indent=2)
                if model_ans['diagram_mode'] == 'described' and model_ans['diagram_description']:
                    print(f"\n  DIAGRAM [{model_ans['diagram_type']}]:")
                    wrap(model_ans['diagram_description'], indent=2)
                print(f"\n  CONCLUSION ({model_ans['wc_conclusion']}w):")
                wrap(model_ans['conclusion_text'], indent=2)
                schemes = json.loads(model_ans['schemes_referenced'] or '[]')
                if schemes:
                    print(f"\n  Schemes: {', '.join(schemes)}")
                hr("═")
        else:
            print("\n  [Model answer not yet generated]")


def save_attempt(conn, q, intro, body, conclusion, diagram_note, ev, session_id):
    scores = {
        "intro_score": ev.get("intro_score"),
        "body_score": ev.get("body_score"),
        "conclusion_score": ev.get("conclusion_score"),
        "overall_score": ev.get("overall_score"),
    }
    conn.execute("""
        INSERT INTO descriptive_attempts
            (user_id, question_id, exam_id, quiz_mode,
             user_answer_intro, user_answer_body, user_answer_conclusion, user_diagram_block,
             word_count_intro, word_count_body, word_count_conclusion,
             scores_json, weighted_score, session_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        USER_ID, q['question_id'], EXAM_ID, 'full',
        intro, body, conclusion, diagram_note,
        len(intro.split()), len(body.split()), len(conclusion.split()),
        json.dumps(scores), ev.get("overall_score"),
        session_id,
    ))
    conn.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IES Descriptive Quiz")
    parser.add_argument("--id", help="Specific question ID")
    parser.add_argument("--topic", help="Topic ID e.g. inflation_india")
    parser.add_argument("--paper", help="Paper ID e.g. ge_04")
    parser.add_argument("--random", action="store_true", help="Pick a random question")
    parser.add_argument("--no-model", action="store_true", help="Skip showing model answer")
    args = parser.parse_args()

    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    conn = get_connection()
    session_id = str(uuid.uuid4())[:8]

    q = pick_question(conn, args.id, args.topic, args.paper, args.random)
    rubric = conn.execute(
        "SELECT * FROM question_rubrics WHERE question_id=? AND exam_id=?",
        (q['question_id'], EXAM_ID)
    ).fetchone()

    show_question(q, rubric)

    intro = read_multiline("INTRO — Define core concepts, frame the scope:")
    print()
    body = read_multiline("BODY — Analysis, data points, diagrams, schemes:")
    print()
    conclusion = read_multiline("CONCLUSION — Policy implications, way forward:")
    print()

    diagram_note = ""
    if rubric and rubric['diagram_expected']:
        diagram_note = input(f"DIAGRAM ({rubric['diagram_type'] or 'expected'}) — describe or press Enter to skip: ").strip()
    print()

    print("Evaluating your answer...")
    ev = evaluate_answer(client, q, rubric, intro, body, conclusion, diagram_note)

    if ev:
        save_attempt(conn, q, intro, body, conclusion, diagram_note, ev, session_id)
        show_evaluation(ev, q, not args.no_model, conn)
    else:
        print("Evaluation failed — please try again")

    conn.close()
