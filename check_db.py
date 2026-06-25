import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'machine_control'))
from database_pg import open_database
db = open_database()
with db.conn.cursor() as cur:
    cur.execute("SELECT * FROM runs ORDER BY start_time DESC LIMIT 5")
    print("Runs:", cur.fetchall())
    cur.execute("SELECT * FROM images ORDER BY captured_at DESC LIMIT 5")
    print("Images:", len(cur.fetchall()))
