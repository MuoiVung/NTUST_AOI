import os
import sys
import time
import requests
import psycopg2

def main():
    sn = "SN5434"
    print(f"=== Starting Integration Test for {sn} ===")
    
    # 1. Trigger the run via FastAPI
    url = "http://127.0.0.1:8000/runs/start"
    payload = {"serial_number": sn}
    try:
        print(f"Sending POST to {url} with payload: {payload}")
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
        result = resp.json()
        print("API Response:", result)
        if result.get("status") != "success":
            print("Failed to start run via API.")
            sys.exit(1)
        m_no = result.get("m_no")
        print(f"Assigned M_NO by simulator: {m_no}")
    except Exception as e:
        print(f"Error calling API: {e}")
        sys.exit(1)

    print("Waiting 15 seconds for PLC simulation and PC Controller to run through steps...")
    time.sleep(15)

    # 2. Check Database for runs
    print("Checking database records...")
    try:
        conn = psycopg2.connect(dbname="pcb_aoi_db", user="admin", password="aoi123!", host="127.0.0.1", port="5433")
        with conn.cursor() as cur:
            cur.execute("SELECT run_number, m_no, status FROM runs WHERE serial_number = %s ORDER BY created_at DESC LIMIT 1", (sn,))
            row = cur.fetchone()
            if not row:
                print("No run found in DB for SN:", sn)
                sys.exit(1)
            
            run_number, db_m_no, status = row
            print(f"Found Run: {run_number}, M_NO: {db_m_no}, Status: {status}")
            
            if status != "COMPLETED":
                print(f"Warning: Status is not COMPLETED (current: {status})")
            
            cur.execute("SELECT COUNT(*) FROM run_steps WHERE run_number = %s", (run_number,))
            total_steps = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM run_steps WHERE run_number = %s AND status = 'COMPLETED'", (run_number,))
            completed_steps = cur.fetchone()[0]
            
            print(f"Steps: {completed_steps}/{total_steps} completed in DB.")
            
    except Exception as e:
        print(f"Database check error: {e}")
        run_number = None
        db_m_no = m_no

    # 3. Check Image files in watch_dir
    print("Checking image files...")
    watch_dir = os.path.join(os.path.dirname(__file__), "watch_dir")
    
    if run_number and db_m_no:
        run_path_top = os.path.join(watch_dir, db_m_no, sn, run_number, "TOP")
        run_path_bot = os.path.join(watch_dir, db_m_no, sn, run_number, "BOTTOM")
        
        top_images = 0
        bot_images = 0
        if os.path.exists(run_path_top):
            top_images = len([f for f in os.listdir(run_path_top) if f.endswith(".jpg") or f.endswith(".png")])
        if os.path.exists(run_path_bot):
            bot_images = len([f for f in os.listdir(run_path_bot) if f.endswith(".jpg") or f.endswith(".png")])
            
        print(f"Images captured -> TOP: {top_images}, BOTTOM: {bot_images}")
        if top_images > 0 and bot_images > 0:
            print("SUCCESS: Images were properly generated and saved.")
        else:
            print("WARNING: Images not fully generated.")
    
    print("=== Integration Test Finished ===")

if __name__ == "__main__":
    main()
