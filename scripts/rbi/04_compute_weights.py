"""
Compute and update priority_weight for every question in rbi_questions.

Formula:
  priority_weight = base_weight(topic) × core_multiplier × recent_multiplier

  core_multiplier  = 2.0 if is_core_concept else 1.0
  recent_multiplier = 1.5 if is_recent_dev else 1.0

Also refreshes flag_impact in rbi_topic_mastery:
  flag_impact = base_weight × (1 - coverage_pct)
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "rbi.db"


def compute_weights():
    conn = sqlite3.connect(DB_PATH)

    # Build topic → base_weight map
    weight_map = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT topic, base_weight FROM rbi_topic_weights"
        ).fetchall()
    }

    questions = conn.execute(
        "SELECT id, topic, is_core_concept, is_recent_dev FROM rbi_questions"
    ).fetchall()

    updates = []
    for qid, topic, is_core, is_recent in questions:
        base = weight_map.get(topic, 0.05)
        core_mult = 2.0 if is_core else 1.0
        recent_mult = 1.5 if is_recent else 1.0
        weight = round(base * core_mult * recent_mult, 4)
        updates.append((weight, qid))

    conn.executemany(
        "UPDATE rbi_questions SET priority_weight = ? WHERE id = ?", updates
    )
    conn.commit()
    print(f"Updated priority_weight for {len(updates)} questions")

    # Refresh coverage_pct and flag_impact in topic_mastery
    mastery_rows = conn.execute(
        "SELECT user_id, topic FROM rbi_topic_mastery"
    ).fetchall()

    for user_id, topic in mastery_rows:
        total_q = conn.execute(
            "SELECT COUNT(*) FROM rbi_questions WHERE topic = ?", (topic,)
        ).fetchone()[0]

        attempted = conn.execute(
            "SELECT COUNT(DISTINCT question_id) FROM rbi_attempts "
            "WHERE user_id = ? AND question_id IN "
            "(SELECT id FROM rbi_questions WHERE topic = ?)",
            (user_id, topic),
        ).fetchone()[0]

        coverage_pct = round(attempted / total_q, 4) if total_q > 0 else 0.0
        base_weight = weight_map.get(topic, 0.05)
        flag_impact = round(base_weight * (1.0 - coverage_pct), 4)

        conn.execute("""
            UPDATE rbi_topic_mastery
            SET coverage_pct = ?, flag_impact = ?, last_updated = datetime('now')
            WHERE user_id = ? AND topic = ?
        """, (coverage_pct, flag_impact, user_id, topic))

    conn.commit()
    conn.close()
    print("Refreshed coverage_pct and flag_impact in rbi_topic_mastery")


def print_summary():
    conn = sqlite3.connect(DB_PATH)
    print("\nTop 10 highest-weight questions:")
    rows = conn.execute(
        "SELECT id, topic, difficulty, priority_weight FROM rbi_questions "
        "ORDER BY priority_weight DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:25s}  topic={r[1]:20s}  diff={r[2]:6s}  weight={r[3]:.4f}")

    print("\nTopic flag_impact (highest = study first):")
    rows = conn.execute(
        "SELECT topic, subject, flag_impact, coverage_pct FROM rbi_topic_mastery "
        "WHERE user_id='rahul' ORDER BY flag_impact DESC LIMIT 15"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:25s}  {r[1]:12s}  impact={r[2]:.4f}  covered={r[3]:.1%}")
    conn.close()


if __name__ == "__main__":
    compute_weights()
    print_summary()
