"""m056 — Register ethics_prac_1/2 in ethics_practice_papers.

62 practice questions (31 each) were seeded into ethics_questions by m052 but
never got a row in ethics_practice_papers, so the landing page's Practice
Papers tab had no way to link to them (BUG: content existed, unreachable).
"""

DB = "upsc_gs"


def run(conn):
    conn.executemany(
        "INSERT OR IGNORE INTO ethics_practice_papers "
        "(paper_id, paper_title, generation_year, difficulty, theme_focus) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("ethics_prac_1", "Practice Paper 1", 2026, "medium",
             "Integrity, constitutional morality, emotional intelligence, civil service values"),
            ("ethics_prac_2", "Practice Paper 2", 2026, "medium",
             "Applied ethics case studies and governance dilemmas"),
        ],
    )
