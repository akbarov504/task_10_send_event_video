import sqlite3
from core.config import DB_PATH

with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM videos")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM videos WHERE uploaded=0")
    unuploaded = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM videos WHERE uploaded=1")
    uploaded = c.fetchone()[0]

    c.execute("SELECT id, file_path, uploaded, retries, start_time FROM videos ORDER BY id DESC LIMIT 5")
    last5 = c.fetchall()

print(f"DB PATH   : {DB_PATH}")
print(f"Total     : {total}")
print(f"Uploaded  : {uploaded}")
print(f"Unuploaded: {unuploaded}")
print(f"\nLast 5 rows:")
for r in last5:
    print(f"  {r}")