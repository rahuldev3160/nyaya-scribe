DB = "upsc"


def run(conn):
    conn.execute(
        "UPDATE exam_configurations SET exam_date=? WHERE exam_id=?",
        ("2026-08-22", "upsc_eco_opt"),
    )
    conn.commit()
