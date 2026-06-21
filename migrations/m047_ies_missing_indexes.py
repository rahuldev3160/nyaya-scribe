DB = "ies"


def run(conn):
    conn.executescript("""

    DROP TABLE IF EXISTS rbi_attempts_new;

    DROP TABLE IF EXISTS gs4_keywords_new;

    CREATE INDEX IF NOT EXISTS idx_ies_da_user_exam
        ON descriptive_attempts(user_id, exam_id);

    CREATE INDEX IF NOT EXISTS idx_ies_gse_user_topic
        ON gap_state_events(user_id, topic_id, exam_id);

    CREATE INDEX IF NOT EXISTS idx_ies_cp_user_topic
        ON context_packages(user_id, topic_id, exam_id);

    """)
    conn.commit()
