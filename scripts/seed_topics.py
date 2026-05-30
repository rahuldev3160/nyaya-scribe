"""
Stage 2: Seed IES topic taxonomy from config/topics_ies.json.
Run: python scripts/seed_topics.py

Seeds topics + subtopics tables. Pre-populates gap_states and
topic_attempt_summary with zero rows for user 'rahul'.
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "ies.db"
CONFIG_PATH = Path(__file__).parent.parent / "config" / "topics_ies.json"
USER_ID = "rahul"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def seed_topics(conn: sqlite3.Connection, data: dict) -> tuple[int, int]:
    exam_id = data["exam_id"]
    topics_inserted = 0
    subtopics_inserted = 0

    for paper in data["papers"]:
        paper_id = paper["paper_id"]
        paper_weight = paper["syllabus_weight_default"]

        for topic in paper["topics"]:
            tid = topic["topic_id"]
            conn.execute("""
                INSERT OR IGNORE INTO topics
                    (topic_id, exam_id, paper_id, topic_name, subtopic_of, topic_level, syllabus_weight)
                VALUES (?, ?, ?, ?, NULL, 'topic', ?)
            """, (tid, exam_id, paper_id, topic["topic_name"],
                  topic.get("syllabus_weight", paper_weight)))
            topics_inserted += 1

            for sub in topic.get("subtopics", []):
                sid = sub["topic_id"]
                conn.execute("""
                    INSERT OR IGNORE INTO topics
                        (topic_id, exam_id, paper_id, topic_name, subtopic_of, topic_level, syllabus_weight)
                    VALUES (?, ?, ?, ?, ?, 'subtopic', ?)
                """, (sid, exam_id, paper_id, sub["topic_name"],
                      tid, topic.get("syllabus_weight", paper_weight)))
                subtopics_inserted += 1

    conn.commit()
    return topics_inserted, subtopics_inserted


def prepopulate_gap_states(conn: sqlite3.Connection, data: dict) -> int:
    exam_id = data["exam_id"]
    rows = 0

    for paper in data["papers"]:
        paper_id = paper["paper_id"]
        for topic in paper["topics"]:
            # Gap states run at topic level only (not subtopic)
            conn.execute("""
                INSERT OR IGNORE INTO gap_states
                    (user_id, topic_id, exam_id, paper_id, state, urgency_multiplier)
                VALUES (?, ?, ?, ?, 'UNVISITED', 1.0)
            """, (USER_ID, topic["topic_id"], exam_id, paper_id))
            rows += 1

    conn.commit()
    return rows


def prepopulate_attempt_summary(conn: sqlite3.Connection, data: dict) -> int:
    exam_id = data["exam_id"]
    rows = 0

    for paper in data["papers"]:
        for topic in paper["topics"]:
            conn.execute("""
                INSERT OR IGNORE INTO topic_attempt_summary
                    (user_id, topic_id, exam_id)
                VALUES (?, ?, ?)
            """, (USER_ID, topic["topic_id"], exam_id))
            rows += 1

    conn.commit()
    return rows


def seed_user_mastery(conn: sqlite3.Connection, data: dict) -> int:
    exam_id = data["exam_id"]
    rows = 0

    for paper in data["papers"]:
        for topic in paper["topics"]:
            conn.execute("""
                INSERT OR IGNORE INTO user_mastery
                    (user_id, topic_id, exam_id, mastery_level, claimed_level, sar_score)
                VALUES (?, ?, ?, 0.0, 0.5, 0.5)
            """, (USER_ID, topic["topic_id"], exam_id))
            rows += 1

    conn.commit()
    return rows


def seed_paper_preferences(conn: sqlite3.Connection, data: dict) -> int:
    exam_id = data["exam_id"]
    rows = 0

    for paper in data["papers"]:
        conn.execute("""
            INSERT OR IGNORE INTO user_paper_preferences
                (user_id, exam_id, paper_id, enabled)
            VALUES (?, ?, ?, 1)
        """, (USER_ID, exam_id, paper["paper_id"]))
        rows += 1

    conn.commit()
    return rows


def verify(conn: sqlite3.Connection) -> None:
    topic_counts = conn.execute("""
        SELECT paper_id, topic_level, COUNT(*)
        FROM topics WHERE exam_id='ies_2026'
        GROUP BY paper_id, topic_level
        ORDER BY paper_id, topic_level
    """).fetchall()

    gap_count = conn.execute(
        "SELECT COUNT(*) FROM gap_states WHERE user_id=? AND exam_id='ies_2026'",
        (USER_ID,)
    ).fetchone()[0]

    mastery_count = conn.execute(
        "SELECT COUNT(*) FROM user_mastery WHERE user_id=? AND exam_id='ies_2026'",
        (USER_ID,)
    ).fetchone()[0]

    summary_count = conn.execute(
        "SELECT COUNT(*) FROM topic_attempt_summary WHERE user_id=? AND exam_id='ies_2026'",
        (USER_ID,)
    ).fetchone()[0]

    paper_prefs = conn.execute(
        "SELECT COUNT(*) FROM user_paper_preferences WHERE user_id=? AND exam_id='ies_2026'",
        (USER_ID,)
    ).fetchone()[0]

    print("\n── Stage 2 Sense Check ──────────────────────────")
    print("Topics by paper and level:")
    for paper_id, level, count in topic_counts:
        print(f"  {paper_id} | {level:10s} | {count:3d}")

    total_topics = conn.execute(
        "SELECT COUNT(*) FROM topics WHERE exam_id='ies_2026' AND topic_level='topic'"
    ).fetchone()[0]
    total_subtopics = conn.execute(
        "SELECT COUNT(*) FROM topics WHERE exam_id='ies_2026' AND topic_level='subtopic'"
    ).fetchone()[0]

    print(f"\nTotal topics     : {total_topics}")
    print(f"Total subtopics  : {total_subtopics}")
    print(f"\nPre-populated rows for user '{USER_ID}':")
    print(f"  gap_states            : {gap_count}")
    print(f"  user_mastery          : {mastery_count}")
    print(f"  topic_attempt_summary : {summary_count}")
    print(f"  paper_preferences     : {paper_prefs}")

    # Sanity checks
    assert gap_count == total_topics, f"gap_states count {gap_count} != topic count {total_topics}"
    assert mastery_count == total_topics, f"mastery count mismatch"
    assert summary_count == total_topics, f"summary count mismatch"
    assert paper_prefs == 4, f"expected 4 paper preferences, got {paper_prefs}"

    print("\n✓ All sanity checks passed")
    print("─────────────────────────────────────────────────\n")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print("DB not found. Run init_db.py first.")
        raise SystemExit(1)

    with open(CONFIG_PATH) as f:
        data = json.load(f)

    conn = get_connection()

    print("Seeding topics and subtopics...")
    topics_n, subtopics_n = seed_topics(conn, data)
    print(f"  Inserted {topics_n} topics, {subtopics_n} subtopics")

    print("Pre-populating gap_states...")
    g = prepopulate_gap_states(conn, data)
    print(f"  Inserted {g} gap_state rows")

    print("Pre-populating topic_attempt_summary...")
    s = prepopulate_attempt_summary(conn, data)
    print(f"  Inserted {s} summary rows")

    print("Seeding user_mastery with defaults...")
    m = seed_user_mastery(conn, data)
    print(f"  Inserted {m} mastery rows")

    print("Seeding paper preferences...")
    p = seed_paper_preferences(conn, data)
    print(f"  Inserted {p} preference rows")

    verify(conn)
    conn.close()
