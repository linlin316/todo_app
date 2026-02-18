import sqlite3
from pathlib import Path

db_path = Path("instance/app.db").resolve()
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("PRAGMA table_info(users)")
cols = [r[1] for r in cur.fetchall()]
print("users columns =", cols)

conn.close()