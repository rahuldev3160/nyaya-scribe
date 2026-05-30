"""
Stage 6: CLI viewer for model answers.
Usage:
  python3 scripts/view_answers.py                        # list all papers
  python3 scripts/view_answers.py --paper ge_04          # list topics in paper
  python3 scripts/view_answers.py --paper ge_04 --topic inflation_india
  python3 scripts/view_answers.py --paper ge_04 --topic inflation_india --year 2025
  python3 scripts/view_answers.py --id ge_04_0012        # show by question_id
  python3 scripts/view_answers.py --search "fiscal deficit"  # search by keyword
"""
import argparse
import json
import sqlite3
import textwrap
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
EXAM_ID = "ies_2026"
WIDTH = 90


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hr(char="─", width=WIDTH):
    print(char * width)


def wrap(text: str, indent=0) -> str:
    prefix = " " * indent
    return textwrap.fill(text, width=WIDTH - indent, initial_indent=prefix, subsequent_indent=prefix)


def list_papers(conn: sqlite3.Connection):
    rows = conn.execute("""
        SELECT q.paper_id,
               COUNT(DISTINCT q.topic_id) AS topics,
               COUNT(q.question_id) AS questions,
               COUNT(a.answer_id) AS answered
        FROM pyq_questions q
        LEFT JOIN model_answers a ON q.question_id=a.question_id AND q.exam_id=a.exam_id
        WHERE q.exam_id=?
        GROUP BY q.paper_id ORDER BY q.paper_id
    """, (EXAM_ID,)).fetchall()

    hr("═")
    print(f"{'IES 2026 — Model Answers':^{WIDTH}}")
    hr("═")
    print(f"{'Paper':<12} {'Topics':>8} {'Questions':>10} {'Answered':>10} {'Coverage':>10}")
    hr()
    for r in rows:
        pct = f"{100*r['answered']//r['questions']}%" if r['questions'] else "0%"
        print(f"{r['paper_id']:<12} {r['topics']:>8} {r['questions']:>10} {r['answered']:>10} {pct:>10}")
    hr()
    print("\nUsage: --paper ge_04  to see topics")


def list_topics(conn: sqlite3.Connection, paper_id: str):
    rows = conn.execute("""
        SELECT t.topic_id, t.topic_name,
               COUNT(q.question_id) AS questions,
               COUNT(a.answer_id) AS answered
        FROM topics t
        LEFT JOIN pyq_questions q ON t.topic_id=q.topic_id AND t.exam_id=q.exam_id
        LEFT JOIN model_answers a ON q.question_id=a.question_id AND q.exam_id=a.exam_id
        WHERE t.exam_id=? AND t.paper_id=? AND t.topic_level='topic'
        GROUP BY t.topic_id ORDER BY questions DESC
    """, (EXAM_ID, paper_id)).fetchall()

    if not rows:
        print(f"No topics found for {paper_id}")
        return

    hr("═")
    print(f"  {paper_id.upper()} Topics")
    hr("═")
    for r in rows:
        pct = f"({100*r['answered']//r['questions']}%)" if r['questions'] else "(0%)"
        print(f"  {r['topic_id']:<40} {r['questions']:>3}q  {r['answered']:>3}ans {pct}")
    hr()
    print("\nUsage: --paper ge_04 --topic inflation_india")


def list_questions(conn: sqlite3.Connection, paper_id: str, topic_id: str):
    rows = conn.execute("""
        SELECT q.question_id, q.year, q.marks, q.answer_length,
               substr(q.question_text, 1, 80) AS preview,
               CASE WHEN a.answer_id IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_answer
        FROM pyq_questions q
        LEFT JOIN model_answers a ON q.question_id=a.question_id AND q.exam_id=a.exam_id
        WHERE q.exam_id=? AND q.paper_id=? AND q.topic_id=?
        ORDER BY q.year DESC, q.marks DESC
    """, (EXAM_ID, paper_id, topic_id)).fetchall()

    if not rows:
        print(f"No questions for {topic_id}")
        return

    hr("═")
    print(f"  {topic_id} ({paper_id})")
    hr("═")
    for r in rows:
        wc = f" /{r['answer_length']}w" if r['answer_length'] else ""
        ans_flag = "✓" if r['has_answer'] == 'YES' else "·"
        print(f"  [{ans_flag}] {r['question_id']:<20} {r['year']} | {r['marks'] or '?'}m{wc}")
        print(f"      {r['preview'].strip()[:75]}...")
    hr()
    print("\nUsage: --id ge_04_0012  to view a specific answer")


def show_answer(conn: sqlite3.Connection, question_id: str):
    q = conn.execute("""
        SELECT q.question_id, q.question_text, q.year, q.marks, q.paper_id, q.topic_id, q.answer_length
        FROM pyq_questions q
        WHERE q.question_id=? AND q.exam_id=?
    """, (question_id, EXAM_ID)).fetchone()

    if not q:
        print(f"Question {question_id} not found")
        return

    a = conn.execute("""
        SELECT intro_text, body_text, conclusion_text,
               diagram_mode, diagram_type, diagram_description, diagram_labels,
               data_points, schemes_referenced, key_terms_used,
               wc_intro, wc_body, wc_conclusion
        FROM model_answers
        WHERE question_id=? AND exam_id=?
    """, (question_id, EXAM_ID)).fetchone()

    marks_str = f"{q['marks']} marks" if q['marks'] else "marks unknown"
    wc_limit = f" | {q['answer_length']} words" if q['answer_length'] else ""

    hr("═")
    print(f"  {question_id}  |  {q['year']}  |  {marks_str}{wc_limit}  |  {q['topic_id']}")
    hr("═")
    print()
    print(wrap(q['question_text']))
    print()

    if not a:
        print("  [Answer not yet generated — run generate_answers.py]")
        hr()
        return

    # ── INTRO ──
    hr("─")
    print(f"  INTRODUCTION  ({a['wc_intro']} words)")
    hr("─")
    print(wrap(a['intro_text'], indent=2))
    print()

    # ── BODY ──
    hr("─")
    print(f"  BODY  ({a['wc_body']} words)")
    hr("─")
    print(wrap(a['body_text'], indent=2))
    print()

    # ── DIAGRAM ──
    if a['diagram_mode'] == 'described' and a['diagram_description']:
        hr("─")
        print(f"  DIAGRAM  [{a['diagram_type'] or 'diagram'}]")
        hr("─")
        print(wrap(a['diagram_description'], indent=2))
        labels = json.loads(a['diagram_labels'] or '[]')
        if labels:
            print(f"\n  Labels: {', '.join(labels)}")
        print()

    # ── CONCLUSION ──
    hr("─")
    print(f"  CONCLUSION  ({a['wc_conclusion']} words)")
    hr("─")
    print(wrap(a['conclusion_text'], indent=2))
    print()

    # ── DATA + SCHEMES ──
    data_pts = json.loads(a['data_points'] or '[]')
    schemes = json.loads(a['schemes_referenced'] or '[]')
    key_terms = json.loads(a['key_terms_used'] or '[]')

    if data_pts or schemes:
        hr("─")
        print("  QUICK REFERENCE")
        hr("─")
        if data_pts:
            print("  Data points:")
            for dp in data_pts:
                flag = " ⚠ verify" if dp.get("flag_verify") else ""
                print(f"    • {dp.get('value', '')} [{dp.get('source', '?')}]{flag}")
        if schemes:
            print(f"  Schemes: {', '.join(schemes)}")
        if key_terms:
            print(f"  Key terms: {', '.join(key_terms)}")
        print()

    hr("═")


def search_answers(conn: sqlite3.Connection, keyword: str):
    rows = conn.execute("""
        SELECT q.question_id, q.year, q.marks, q.paper_id, q.topic_id,
               substr(q.question_text, 1, 100) AS preview,
               CASE WHEN a.answer_id IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_answer
        FROM pyq_questions q
        LEFT JOIN model_answers a ON q.question_id=a.question_id AND q.exam_id=a.exam_id
        WHERE q.exam_id=? AND LOWER(q.question_text) LIKE LOWER(?)
        ORDER BY q.year DESC, q.marks DESC
        LIMIT 25
    """, (EXAM_ID, f"%{keyword}%")).fetchall()

    if not rows:
        print(f"No questions matching '{keyword}'")
        return

    hr("═")
    print(f"  Search: '{keyword}'  ({len(rows)} results)")
    hr("═")
    for r in rows:
        ans_flag = "✓" if r['has_answer'] == 'YES' else "·"
        print(f"  [{ans_flag}] {r['question_id']:<20} {r['year']} | {r['marks'] or '?'}m | {r['topic_id']}")
        print(f"      {r['preview'].strip()[:78]}...")
    hr()
    print("\nUsage: --id <question_id>  to view a specific answer")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IES PYQ Model Answer Viewer")
    parser.add_argument("--paper", help="Paper ID e.g. ge_04")
    parser.add_argument("--topic", help="Topic ID e.g. inflation_india")
    parser.add_argument("--year", type=int, help="Filter by year")
    parser.add_argument("--id", help="Show specific question by ID")
    parser.add_argument("--search", help="Search question text by keyword")
    args = parser.parse_args()

    conn = get_connection()

    if args.id:
        show_answer(conn, args.id)
    elif args.search:
        search_answers(conn, args.search)
    elif args.paper and args.topic:
        if args.year:
            # Filter questions in topic to a specific year
            rows = conn.execute("""
                SELECT question_id FROM pyq_questions
                WHERE exam_id=? AND paper_id=? AND topic_id=? AND year=?
                ORDER BY question_id
            """, (EXAM_ID, args.paper, args.topic, args.year)).fetchall()
            if not rows:
                print(f"No questions for {args.topic} in {args.year}")
            else:
                for r in rows:
                    show_answer(conn, r[0])
        else:
            list_questions(conn, args.paper, args.topic)
    elif args.paper:
        list_topics(conn, args.paper)
    else:
        list_papers(conn)

    conn.close()
