DB = "rbi"

def run(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS exam_configurations (
            exam_id TEXT PRIMARY KEY,
            exam_date TEXT,
            exam_label TEXT
        );
    """)
    conn.execute(
        "INSERT OR REPLACE INTO exam_configurations (exam_id, exam_date, exam_label) VALUES (?,?,?)",
        ("rbi_depr", "2026-06-14", "RBI Grade B DEPR")
    )
    conn.commit()
