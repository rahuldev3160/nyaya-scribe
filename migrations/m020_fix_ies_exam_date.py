DB = "ies"

def run(conn):
    conn.execute(
        "UPDATE exam_configurations SET exam_date=? WHERE exam_id=?",
        ("2026-06-19", "ies_2026")
    )
    conn.commit()
