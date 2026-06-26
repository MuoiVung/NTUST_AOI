import psycopg2
conn = psycopg2.connect("dbname=pcb_aoi_db user=admin password=aoi123! host=127.0.0.1 port=5433")
cur = conn.cursor()
cur.execute("SELECT trigger_name, event_object_table FROM information_schema.triggers;")
for r in cur.fetchall(): print(r)

cur.execute("SELECT proname, prosrc FROM pg_proc WHERE proname = 'increment_order_quantity';")
for r in cur.fetchall(): print(r)
