DB = "rbi"


def run(conn):
    conn.executescript("""

    CREATE INDEX IF NOT EXISTS idx_rbi_q_subject_topic
        ON rbi_questions(subject, topic);

    """)
    conn.commit()
