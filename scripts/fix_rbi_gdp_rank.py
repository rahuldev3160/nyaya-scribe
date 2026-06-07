import sqlite3, os

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "rbi.db")
conn = sqlite3.connect(db_path)

conn.execute(
    "UPDATE rbi_key_data SET item_value=?, item_note=? WHERE data_id=?",
    (
        "6th globally (IMF 2025)",
        "Ahead: USA, China, Germany, Japan, UK. Aspiration: 3rd by early 2030s.",
        "ine_01",
    ),
)
conn.commit()

row = conn.execute(
    "SELECT data_id, item_value, item_note FROM rbi_key_data WHERE data_id='ine_01'"
).fetchone()
print("Updated:", row)
conn.close()
