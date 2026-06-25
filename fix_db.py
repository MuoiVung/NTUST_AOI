import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'machine_control'))
from database_pg import open_database
db = open_database()
with db.conn.cursor() as cur:
    cur.execute("INSERT INTO board_numbers (board_number, length_mm, width_mm, top_camera_enabled, bottom_camera_enabled) VALUES ('AUTO-SIM-BOARD', 100, 60, true, true) ON CONFLICT DO NOTHING;")
db.conn.commit()
print("Fixed")
