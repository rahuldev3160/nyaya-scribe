DB = "upsc_eco_opt"


def run(conn):
    conn.executescript("""

    CREATE INDEX IF NOT EXISTS idx_eco_da_user_exam
        ON descriptive_attempts(user_id, exam_id, created_at DESC);

    CREATE INDEX IF NOT EXISTS idx_eco_pyq_paper_year
        ON pyq_questions(paper_id, year DESC);

    CREATE INDEX IF NOT EXISTS idx_eco_gs_user_state
        ON gap_states(user_id, exam_id, state);

    CREATE INDEX IF NOT EXISTS idx_eco_tbs_priority
        ON topic_base_scores(exam_id, base_priority_score DESC);

    CREATE INDEX IF NOT EXISTS idx_eco_rqa_user_topic
        ON return_quiz_attempts(user_id, topic_id, exam_id, created_at DESC);

    """)
    conn.commit()
