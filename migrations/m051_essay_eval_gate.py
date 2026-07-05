"""m051 — Add essay_eval feature gate to nyaya.db"""

DB = "nyaya"


def run(conn):
    conn.execute(
        """INSERT OR IGNORE INTO feature_gates
               (gate_id, feature_name, description,
                is_enabled_for_free, is_enabled_for_pro,
                quota_free, quota_pro)
           VALUES (
               'essay_eval',
               'AI-powered essay evaluation',
               '4-dimension UPSC essay rubric scoring: intro, body, challenges+solutions, conclusion',
               1, 1, 15, NULL
           )"""
    )
    conn.commit()
