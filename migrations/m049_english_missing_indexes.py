DB = "english"


def run(conn):
    conn.executescript("""

    CREATE INDEX IF NOT EXISTS idx_eng_q_type
        ON english_questions(type_id);

    CREATE INDEX IF NOT EXISTS idx_eng_kw_question
        ON english_keywords(question_id);

    """)
    conn.commit()
