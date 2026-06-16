"""Seed upsc_gs.db topics taxonomy from config/topics_upsc_gs.json."""
import json
from pathlib import Path

DB = "upsc_gs"

_TOPICS_JSON = Path(__file__).parent.parent / "config" / "topics_upsc_gs.json"
EXAM_ID = "upsc_gs_mains"


def run(conn):
    data = json.loads(_TOPICS_JSON.read_text())
    exam_id = data["exam_id"]

    for paper in data["papers"]:
        paper_id = paper["paper_id"]
        w_default = paper.get("syllabus_weight_default", 1.0)

        for topic in paper["topics"]:
            conn.execute("""
                INSERT OR IGNORE INTO topics
                    (topic_id, exam_id, paper_id, topic_name, subtopic_of, topic_level, syllabus_weight)
                VALUES (?,?,?,?,NULL,'topic',?)
            """, (topic["topic_id"], exam_id, paper_id,
                  topic["topic_name"], topic.get("syllabus_weight", w_default)))

            # Seed zero-row in topic_base_scores
            conn.execute("""
                INSERT OR IGNORE INTO topic_base_scores
                    (topic_id, exam_id, paper_id)
                VALUES (?,?,?)
            """, (topic["topic_id"], exam_id, paper_id))

            for sub in topic.get("subtopics", []):
                conn.execute("""
                    INSERT OR IGNORE INTO topics
                        (topic_id, exam_id, paper_id, topic_name, subtopic_of, topic_level, syllabus_weight)
                    VALUES (?,?,?,?,?,'subtopic',?)
                """, (sub["topic_id"], exam_id, paper_id,
                      sub["topic_name"], topic["topic_id"],
                      sub.get("syllabus_weight", topic.get("syllabus_weight", w_default))))

                conn.execute("""
                    INSERT OR IGNORE INTO topic_base_scores
                        (topic_id, exam_id, paper_id)
                    VALUES (?,?,?)
                """, (sub["topic_id"], exam_id, paper_id))

    conn.commit()
