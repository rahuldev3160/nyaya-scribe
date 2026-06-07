DB = "nyaya"


def run(conn):
    try:
        conn.execute("ALTER TABLE users ADD COLUMN phone_number TEXT")
        conn.commit()
    except Exception:
        pass  # Column already exists
