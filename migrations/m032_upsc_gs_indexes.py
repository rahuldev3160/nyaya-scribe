"""Performance indexes for upsc_gs.db."""

DB = "upsc_gs"


def run(conn):
    conn.executescript("""

    CREATE INDEX IF NOT EXISTS idx_uggs_topics_paper
        ON topics(exam_id, paper_id);

    CREATE INDEX IF NOT EXISTS idx_uggs_pyq_topic
        ON pyq_questions(exam_id, topic_id, year DESC);

    CREATE INDEX IF NOT EXISTS idx_uggs_pyq_paper_year
        ON pyq_questions(paper_id, year DESC);

    CREATE INDEX IF NOT EXISTS idx_uggs_gap_states_user
        ON gap_states(user_id, exam_id, state);

    CREATE INDEX IF NOT EXISTS idx_uggs_gap_states_paper
        ON gap_states(exam_id, paper_id, state);

    CREATE INDEX IF NOT EXISTS idx_uggs_user_mastery
        ON user_mastery(user_id, exam_id);

    CREATE INDEX IF NOT EXISTS idx_uggs_descriptive_attempts
        ON descriptive_attempts(user_id, exam_id, created_at DESC);

    CREATE INDEX IF NOT EXISTS idx_uggs_topic_base_scores
        ON topic_base_scores(exam_id, base_priority_score DESC);

    CREATE INDEX IF NOT EXISTS idx_uggs_ca_events_date
        ON ca_events(event_date DESC, is_stale);

    CREATE INDEX IF NOT EXISTS idx_uggs_ca_topic_links
        ON ca_topic_links(topic_id, paper_id);

    CREATE INDEX IF NOT EXISTS idx_uggs_topic_links_source
        ON topic_links(source_topic_id, source_paper_id);

    CREATE INDEX IF NOT EXISTS idx_uggs_topic_links_target
        ON topic_links(target_topic_id, target_paper_id);

    CREATE INDEX IF NOT EXISTS idx_uggs_gs4_question_keywords
        ON gs4_question_keywords(keyword_id, is_primary);

    CREATE INDEX IF NOT EXISTS idx_uggs_return_quiz_topic
        ON return_quiz_questions(topic_id, exam_id, quiz_tier);

    CREATE INDEX IF NOT EXISTS idx_uggs_return_quiz_attempts
        ON return_quiz_attempts(user_id, topic_id, exam_id, created_at DESC);

    """)
    conn.commit()
