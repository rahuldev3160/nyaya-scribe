"""Add GS-specific columns to pyq_questions, model_answers, topics, question_rubrics in upsc_gs.db."""

DB = "upsc_gs"


def run(conn):
    alterations = [
        # pyq_questions — multi-topic questions (GS1 cross-topic ~30%), GS4 case preambles
        ("pyq_questions", "secondary_topic_ids",    "TEXT"),
        ("pyq_questions", "cross_paper_flag",       "INTEGER DEFAULT 0"),
        ("pyq_questions", "answer_word_count",      "INTEGER"),
        ("pyq_questions", "legal_provisions_flag",  "INTEGER DEFAULT 0"),
        ("pyq_questions", "case_study_preamble",    "TEXT"),
        ("pyq_questions", "staleness_flag",         "INTEGER DEFAULT 0"),
        # model_answers — CA staleness tracking + GS-specific answer types
        ("model_answers", "answer_type",            "TEXT DEFAULT 'descriptive'"),
        ("model_answers", "data_vintage_date",      "TEXT"),
        ("model_answers", "has_stale_ca",           "INTEGER DEFAULT 0"),
        ("model_answers", "ca_linked_events",       "TEXT"),
        # topics — CA sensitivity for staleness-driven refresh
        ("topics", "ca_sensitivity",    "TEXT DEFAULT 'static'"),
        ("topics", "refresh_cycle",     "TEXT"),
        # question_rubrics — GS-specific evaluation fields
        ("question_rubrics", "rubric_type",               "TEXT DEFAULT 'factual'"),
        ("question_rubrics", "constitutional_provisions", "TEXT"),
        ("question_rubrics", "current_affairs_hook",      "TEXT"),
        ("question_rubrics", "data_points_required",      "TEXT"),
        ("question_rubrics", "synthesis_paper_checks",    "TEXT"),
    ]

    for table, column, col_def in alterations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        except Exception:
            pass  # Column already exists — idempotent

    conn.commit()
