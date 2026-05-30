"""
Study session planner — shows today's priority topics and study queue.
Run: python3 scripts/session_planner.py
     python3 scripts/session_planner.py --paper ge_04
     python3 scripts/session_planner.py --flag inflation_india   # mark as studying
     python3 scripts/session_planner.py --done inflation_india   # mark as verified
     python3 scripts/session_planner.py --reset inflation_india  # reset to UNVISITED
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
EXAM_ID = "ies_2026"
USER_ID = "rahul"
WIDTH = 90

EXAM_DATE = "2026-06-17"

STATE_EMOJI = {
    "UNVISITED": "○",
    "FLAGGED": "⚑",
    "IN_STUDY": "◑",
    "PARTIAL": "◕",
    "VERIFIED": "✓",
    "DECAYING": "↓",
}

STATE_ORDER = ["VERIFIED", "PARTIAL", "IN_STUDY", "FLAGGED", "UNVISITED", "DECAYING"]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hr(char="─", width=WIDTH):
    print(char * width)


def days_to_exam() -> int:
    today = datetime.today().date()
    exam = datetime.strptime(EXAM_DATE, "%Y-%m-%d").date()
    return (exam - today).days


def get_personal_priority(conn: sqlite3.Connection, topic_id: str) -> float:
    """Personal priority = base_priority - mastery discounts."""
    cfg = conn.execute(
        "SELECT w7_mastery_discount FROM exam_configurations WHERE exam_id=?", (EXAM_ID,)
    ).fetchone()
    w7 = cfg[0] if cfg else 0.20

    base = conn.execute(
        "SELECT base_priority_score FROM topic_base_scores WHERE topic_id=? AND exam_id=?",
        (topic_id, EXAM_ID)
    ).fetchone()
    base_score = base[0] if base else 0.0

    mastery = conn.execute(
        "SELECT mastery_level FROM user_mastery WHERE user_id=? AND topic_id=? AND exam_id=?",
        (USER_ID, topic_id, EXAM_ID)
    ).fetchone()
    mastery_level = mastery[0] if mastery else 0.0

    return round(base_score - w7 * mastery_level, 4)


def show_dashboard(conn: sqlite3.Connection, paper_filter=None):
    days_left = days_to_exam()

    hr("═")
    print(f"  IES 2026 Study Planner  |  {days_left} days to exam  |  {datetime.today().strftime('%d %b %Y')}")
    hr("═")

    paper_clause = f"AND gs.paper_id='{paper_filter}'" if paper_filter else ""

    rows = conn.execute(f"""
        SELECT t.topic_id, t.topic_name, t.paper_id,
               gs.state, gs.urgency_multiplier,
               bs.base_priority_score, bs.pyq_count, bs.distinct_years,
               um.mastery_level,
               COUNT(DISTINCT ma.answer_id) AS answers_ready,
               COUNT(DISTINCT q.question_id) AS total_q
        FROM gap_states gs
        JOIN topics t ON gs.topic_id=t.topic_id AND gs.exam_id=t.exam_id
        LEFT JOIN topic_base_scores bs ON gs.topic_id=bs.topic_id AND gs.exam_id=bs.exam_id
        LEFT JOIN user_mastery um ON gs.user_id=um.user_id AND gs.topic_id=um.topic_id AND gs.exam_id=um.exam_id
        LEFT JOIN pyq_questions q ON gs.topic_id=q.topic_id AND gs.exam_id=q.exam_id
        LEFT JOIN model_answers ma ON q.question_id=ma.question_id AND q.exam_id=ma.exam_id
        WHERE gs.user_id=? AND gs.exam_id=? {paper_clause}
        GROUP BY gs.topic_id
        ORDER BY gs.paper_id,
                 CASE gs.state
                     WHEN 'IN_STUDY' THEN 0
                     WHEN 'FLAGGED' THEN 1
                     WHEN 'PARTIAL' THEN 2
                     WHEN 'DECAYING' THEN 3
                     WHEN 'UNVISITED' THEN 4
                     WHEN 'VERIFIED' THEN 5
                 END,
                 bs.base_priority_score DESC
    """, (USER_ID, EXAM_ID)).fetchall()

    # Group by paper
    current_paper = None
    for r in rows:
        if r['paper_id'] != current_paper:
            current_paper = r['paper_id']
            print(f"\n  {current_paper.upper()}")
            print(f"  {'State':<3} {'Topic':<38} {'PYQ':>5} {'Score':>7} {'Ans':>5}")
            hr()

        state = r['state'] or 'UNVISITED'
        emoji = STATE_EMOJI.get(state, "?")
        prio = r['base_priority_score'] or 0.0
        answers = r['answers_ready'] or 0
        total_q = r['total_q'] or 0
        ans_str = f"{answers}/{total_q}"

        print(
            f"  {emoji}   {r['topic_id']:<38} {r['pyq_count'] or 0:>5} "
            f"{prio:>7.3f} {ans_str:>5}"
        )

    hr()

    # Summary
    state_counts = {}
    for r in rows:
        s = r['state'] or 'UNVISITED'
        state_counts[s] = state_counts.get(s, 0) + 1

    print("\n  Summary:")
    for s in STATE_ORDER:
        cnt = state_counts.get(s, 0)
        if cnt > 0:
            print(f"    {STATE_EMOJI[s]} {s:<12}: {cnt}")

    # Today's recommendation
    in_study = [r for r in rows if r['state'] == 'IN_STUDY']
    flagged = [r for r in rows if r['state'] == 'FLAGGED']
    unvisited_sorted = sorted(
        [r for r in rows if r['state'] == 'UNVISITED'],
        key=lambda x: -(x['base_priority_score'] or 0)
    )

    print("\n  TODAY'S QUEUE:")
    queue = in_study + flagged + unvisited_sorted[:max(0, 4 - len(in_study) - len(flagged))]
    if queue:
        for i, r in enumerate(queue[:4], 1):
            state = r['state'] or 'UNVISITED'
            emoji = STATE_EMOJI.get(state, "?")
            ans = r['answers_ready'] or 0
            total = r['total_q'] or 0
            print(f"    {i}. {emoji} {r['topic_id']} ({r['paper_id']}) — {ans}/{total} answers ready")
    else:
        print("    All topics verified! Review DECAYING topics.")

    print()
    hr("─")
    print("  Commands:")
    print("    --flag <topic_id>    Mark as in-study")
    print("    --done <topic_id>    Mark as verified")
    print("    --paper <paper_id>   Filter to one paper")
    print("    view: python3 scripts/view_answers.py --paper ge_04 --topic <topic>")
    print("    quiz: python3 scripts/quiz_descriptive.py --topic <topic>")
    hr("─")


def transition_state(conn: sqlite3.Connection, topic_id: str, new_state: str, trigger: str):
    current = conn.execute(
        "SELECT state FROM gap_states WHERE user_id=? AND topic_id=? AND exam_id=?",
        (USER_ID, topic_id, EXAM_ID)
    ).fetchone()

    if not current:
        print(f"Topic {topic_id} not found")
        return

    from_state = current[0]

    conn.execute("""
        UPDATE gap_states SET state=?, last_active_at=datetime('now')
        WHERE user_id=? AND topic_id=? AND exam_id=?
    """, (new_state, USER_ID, topic_id, EXAM_ID))

    conn.execute("""
        INSERT INTO gap_state_events
            (user_id, topic_id, exam_id, from_state, to_state, trigger, created_at)
        VALUES (?,?,?,?,?,?,datetime('now'))
    """, (USER_ID, topic_id, EXAM_ID, from_state, new_state, trigger))

    conn.commit()
    print(f"  {topic_id}: {from_state} → {new_state}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IES Study Session Planner")
    parser.add_argument("--paper", help="Filter to paper e.g. ge_04")
    parser.add_argument("--flag", help="Mark topic as IN_STUDY")
    parser.add_argument("--done", help="Mark topic as VERIFIED")
    parser.add_argument("--partial", help="Mark topic as PARTIAL")
    parser.add_argument("--reset", help="Reset topic to UNVISITED")
    args = parser.parse_args()

    conn = get_connection()

    if args.flag:
        transition_state(conn, args.flag, "IN_STUDY", "user_flag")
    elif args.done:
        transition_state(conn, args.done, "VERIFIED", "user_verified")
    elif args.partial:
        transition_state(conn, args.partial, "PARTIAL", "user_partial")
    elif args.reset:
        transition_state(conn, args.reset, "UNVISITED", "user_reset")
    else:
        show_dashboard(conn, args.paper)

    conn.close()
