"""Add self_rating to descriptive_attempts — supports post-submit model answer comparison."""
DB = "ies"


def run(conn):
    conn.execute("ALTER TABLE descriptive_attempts ADD COLUMN self_rating TEXT")
    conn.commit()
