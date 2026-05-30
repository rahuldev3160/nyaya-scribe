"""
Generate a study context package for a topic — copy-paste to Claude.ai.
Run: python3 scripts/generate_context.py --topic economic_growth_development
     python3 scripts/generate_context.py --topic inflation_india --save

Outputs a focused study prompt with top PYQs, rubric points, key terms,
and diagram hints. Designed to be pasted into Claude.ai for deep study.
"""
import argparse
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
EXAM_ID = "ies_2026"
USER_ID = "rahul"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_context(conn: sqlite3.Connection, topic_id: str) -> str:
    # Topic info
    topic = conn.execute(
        "SELECT topic_name, paper_id, syllabus_weight FROM topics WHERE topic_id=? AND exam_id=? AND topic_level='topic'",
        (topic_id, EXAM_ID)
    ).fetchone()
    if not topic:
        return f"Topic {topic_id} not found"

    # Subtopics
    subtopics = conn.execute(
        "SELECT topic_name FROM topics WHERE subtopic_of=? AND exam_id=? ORDER BY topic_id",
        (topic_id, EXAM_ID)
    ).fetchall()

    # Priority score
    bs = conn.execute(
        "SELECT base_priority_score, pyq_count, distinct_years FROM topic_base_scores WHERE topic_id=? AND exam_id=?",
        (topic_id, EXAM_ID)
    ).fetchone()

    # Top 10 PYQs by marks + year desc
    questions = conn.execute("""
        SELECT q.question_id, q.year, q.marks, q.question_text, q.answer_length,
               r.rubric_points, r.key_terms, r.diagram_expected, r.diagram_type
        FROM pyq_questions q
        LEFT JOIN question_rubrics r ON q.question_id=r.question_id AND q.exam_id=r.exam_id
        WHERE q.topic_id=? AND q.exam_id=?
        ORDER BY q.marks DESC NULLS LAST, q.year DESC
        LIMIT 10
    """, (topic_id, EXAM_ID)).fetchall()

    # Aggregate all key terms from rubrics
    all_key_terms = set()
    all_diagrams = []
    for q in questions:
        if q['key_terms']:
            for kt in json.loads(q['key_terms']):
                all_key_terms.add(kt)
        if q['diagram_expected'] and q['diagram_type']:
            all_diagrams.append(q['diagram_type'])

    # Build the prompt
    lines = []
    lines.append("=" * 70)
    lines.append(f"IES 2026 STUDY CONTEXT: {topic['topic_name']}")
    prio = f"{bs['base_priority_score']:.3f}" if bs else "?"
    lines.append(f"Paper: {topic['paper_id'].upper()} | Priority Score: {prio}")
    pyq_count = bs['pyq_count'] if bs else '?'
    pyq_yrs = bs['distinct_years'] if bs else '?'
    lines.append(f"PYQ Count: {pyq_count} questions across {pyq_yrs} years")
    lines.append("=" * 70)

    if subtopics:
        lines.append("\nSYLLABUS COVERAGE:")
        for st in subtopics:
            lines.append(f"  • {st['topic_name']}")

    lines.append("\nKEY TERMS TO MASTER:")
    for kt in sorted(all_key_terms):
        lines.append(f"  • {kt}")

    if all_diagrams:
        from collections import Counter
        diag_counts = Counter(all_diagrams)
        lines.append("\nDIAGRAMS FREQUENTLY ASKED:")
        for dtype, cnt in diag_counts.most_common():
            lines.append(f"  • {dtype} ({cnt}x)")

    lines.append(f"\nTOP {len(questions)} MOST IMPORTANT QUESTIONS (by marks + recency):")
    lines.append("-" * 70)

    for i, q in enumerate(questions, 1):
        marks_str = f"{q['marks']}m" if q['marks'] else "?m"
        wc = f"/{q['answer_length']}w" if q['answer_length'] else ""
        lines.append(f"\nQ{i}. [{q['year']} | {marks_str}{wc}]")
        lines.append(q['question_text'])

        if q['rubric_points']:
            rp = json.loads(q['rubric_points'])
            lines.append(f"\n   Rubric ({len(rp)} points):")
            for p in rp:
                lines.append(f"   [{p['section_hint']}] {p['point']}")

        if q['diagram_expected']:
            lines.append(f"   ⊞ Diagram expected: {q['diagram_type'] or 'relevant diagram'}")

    lines.append("\n" + "=" * 70)
    lines.append("STUDY INSTRUCTIONS:")
    lines.append("1. Ask Claude.ai to explain each key term with IES-level depth")
    lines.append("2. For each question, ask for a model answer (intro/body/conclusion format)")
    lines.append("3. Ask to draw/describe relevant diagrams for this topic")
    lines.append("4. Focus on 2025, 2024, 2023 patterns — exam repeats themes")
    lines.append("5. Note government schemes + latest data points for GE-03/GE-04")
    lines.append("=" * 70)

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate study context package")
    parser.add_argument("--topic", required=True, help="Topic ID e.g. economic_growth_development")
    parser.add_argument("--save", action="store_true", help="Save to data/context_<topic>.txt")
    args = parser.parse_args()

    conn = get_connection()
    context = build_context(conn, args.topic)
    print(context)

    if args.save:
        out_path = Path(__file__).parent.parent / "data" / f"context_{args.topic}.txt"
        out_path.write_text(context)
        print(f"\nSaved to {out_path}")

    conn.close()
