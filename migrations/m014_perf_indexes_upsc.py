DB = "upsc"


def run(conn):
    conn.executescript("""
        CREATE INDEX IF NOT EXISTS idx_pyq_exam_topic
            ON pyq_questions(exam_id, topic_id);
        CREATE INDEX IF NOT EXISTS idx_ma_exam_qid
            ON model_answers(exam_id, question_id);
        CREATE INDEX IF NOT EXISTS idx_topics_exam_level
            ON topics(exam_id, topic_level);
        CREATE INDEX IF NOT EXISTS idx_gs_user_exam
            ON gap_states(user_id, exam_id);
        CREATE INDEX IF NOT EXISTS idx_um_user_exam
            ON user_mastery(user_id, exam_id);
    """)
    conn.commit()
