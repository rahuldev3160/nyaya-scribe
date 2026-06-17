"""
Stage 2 (UPSC): Seed topic taxonomy from config/topics_upsc_eco.json.
Run: python3 scripts/upsc/02_seed_topics_upsc.py

Seeds 16 topics + 64 subtopics across 2 papers.
Pre-populates gap_states, user_mastery, topic_attempt_summary for user 'rahul'.
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "upsc_eco_opt.db"
CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "topics_upsc_eco.json"
EXAM_ID = "upsc_eco_opt"
USER_ID = "rahul"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def seed_topics(conn: sqlite3.Connection, data: dict) -> tuple:
    exam_id = data["exam_id"]
    topics_n = subtopics_n = 0

    for paper in data["papers"]:
        paper_id = paper["paper_id"]
        default_sw = paper["syllabus_weight_default"]

        for topic in paper["topics"]:
            tid = topic["topic_id"]
            conn.execute("""
                INSERT OR IGNORE INTO topics
                    (topic_id, exam_id, paper_id, topic_name, subtopic_of, topic_level, syllabus_weight)
                VALUES (?, ?, ?, ?, NULL, 'topic', ?)
            """, (tid, exam_id, paper_id, topic["topic_name"],
                  topic.get("syllabus_weight", default_sw)))
            topics_n += 1

            for sub in topic.get("subtopics", []):
                conn.execute("""
                    INSERT OR IGNORE INTO topics
                        (topic_id, exam_id, paper_id, topic_name, subtopic_of, topic_level, syllabus_weight)
                    VALUES (?, ?, ?, ?, ?, 'subtopic', ?)
                """, (sub["topic_id"], exam_id, paper_id, sub["topic_name"],
                      tid, topic.get("syllabus_weight", default_sw)))
                subtopics_n += 1

    conn.commit()
    return topics_n, subtopics_n


def prepopulate_user_rows(conn: sqlite3.Connection, data: dict) -> dict:
    exam_id = data["exam_id"]
    counts = {"gap_states": 0, "user_mastery": 0, "topic_attempt_summary": 0, "paper_prefs": 0}

    for paper in data["papers"]:
        paper_id = paper["paper_id"]
        conn.execute("""
            INSERT OR IGNORE INTO user_paper_preferences (user_id, exam_id, paper_id, enabled)
            VALUES (?, ?, ?, 1)
        """, (USER_ID, exam_id, paper_id))
        counts["paper_prefs"] += 1

        for topic in paper["topics"]:
            tid = topic["topic_id"]
            conn.execute("""
                INSERT OR IGNORE INTO gap_states
                    (user_id, topic_id, exam_id, paper_id, state, urgency_multiplier)
                VALUES (?, ?, ?, ?, 'UNVISITED', 1.0)
            """, (USER_ID, tid, exam_id, paper_id))
            counts["gap_states"] += 1

            conn.execute("""
                INSERT OR IGNORE INTO user_mastery
                    (user_id, topic_id, exam_id, mastery_level, claimed_level, sar_score)
                VALUES (?, ?, ?, 0.0, 0.5, 0.5)
            """, (USER_ID, tid, exam_id))
            counts["user_mastery"] += 1

            conn.execute("""
                INSERT OR IGNORE INTO topic_attempt_summary (user_id, topic_id, exam_id)
                VALUES (?, ?, ?)
            """, (USER_ID, tid, exam_id))
            counts["topic_attempt_summary"] += 1

    # Seed default user record
    conn.execute("""
        INSERT OR IGNORE INTO users (user_id, display_name, exam_target, created_at)
        VALUES (?, 'Rahul Singh', 'upsc_mains_2026', datetime('now'))
    """, (USER_ID,))

    conn.commit()
    return counts


def verify(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT paper_id, topic_level, COUNT(*) as cnt
        FROM topics WHERE exam_id=?
        GROUP BY paper_id, topic_level ORDER BY paper_id, topic_level
    """, (EXAM_ID,)).fetchall()

    total_topics = conn.execute(
        "SELECT COUNT(*) FROM topics WHERE exam_id=? AND topic_level='topic'", (EXAM_ID,)
    ).fetchone()[0]
    total_subs = conn.execute(
        "SELECT COUNT(*) FROM topics WHERE exam_id=? AND topic_level='subtopic'", (EXAM_ID,)
    ).fetchone()[0]
    gap_cnt = conn.execute(
        "SELECT COUNT(*) FROM gap_states WHERE exam_id=? AND user_id=?", (EXAM_ID, USER_ID)
    ).fetchone()[0]

    print("\n── Stage 2 (UPSC) Sense Check ──────────────────────")
    print("Topics by paper and level:")
    for paper_id, level, cnt in rows:
        print(f"  {paper_id} | {level:10s} | {cnt:3d}")
    print(f"\nTotal topics     : {total_topics}")
    print(f"Total subtopics  : {total_subs}")
    print(f"gap_states (rahul): {gap_cnt}")

    assert total_topics == 16, f"Expected 16 topics, got {total_topics}"
    assert gap_cnt == 16, f"Expected 16 gap_state rows, got {gap_cnt}"
    print("\n✓ All sanity checks passed")
    print("────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    if not DB_PATH.exists():
        print("DB not found. Run 01_init_upsc_db.py first.")
        raise SystemExit(1)

    with open(CONFIG_PATH) as f:
        data = json.load(f)

    conn = get_connection()

    print("Seeding topics and subtopics...")
    t, s = seed_topics(conn, data)
    print(f"  Inserted {t} topics, {s} subtopics")

    print("Pre-populating user rows (rahul)...")
    counts = prepopulate_user_rows(conn, data)
    for k, v in counts.items():
        print(f"  {k}: {v}")

    verify(conn)
    conn.close()
