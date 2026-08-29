"""m064 — ies.db: fix exam_configurations for the 2027 cycle

The old row (exam_name "Indian Economic Service 2026", exam_date 2026-06-19)
was already showing a negative countdown to real users -- that date has
passed. This was originally fixed by editing the local dev copy of ies.db
directly with sqlite3 CLI, which never reaches Railway's actual production
volume (a physically separate set of files) -- redone here as a proper
migration so it applies for real on deploy. exam_id stays 'ies_2026'
deliberately (see web/blueprints/dashboard_bp.py's docstring) -- it's a
stable internal slug, not a cycle tracker.
"""

DB = "ies"


def run(conn):
    conn.execute("""
        UPDATE exam_configurations
        SET exam_name = 'Indian Economic Service 2027',
            exam_date = '2027-06-18'
        WHERE exam_id = 'ies_2026'
    """)
    conn.commit()
