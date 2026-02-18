import sqlite3
from pathlib import Path

db_path = Path("instance/app.db").resolve()
print("DB =", db_path)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 1")
    print("✅ is_approved added")
except Exception as e:
    print("⚠️ maybe already exists:", e)

conn.commit()
conn.close()