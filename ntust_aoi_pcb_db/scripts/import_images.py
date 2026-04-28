import os
import sys
import uuid
import datetime
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_USER = os.getenv("DB_ROOT_USER")
DB_PASS = os.getenv("DB_ROOT_PASSWORD")
APP_DOMAIN = os.getenv("APP_DOMAIN", "")

if not DB_USER or not DB_PASS:
    print("❌ Error: DB_ROOT_USER or DB_ROOT_PASSWORD not found in environment variables.")
    sys.exit(1)

DB_PORT = os.getenv("DB_PORT", "5433")
CONN_STR = f"postgresql://{DB_USER}:{DB_PASS}@localhost:{DB_PORT}/pcb_aoi_db"

def get_db_connection():
    try:
        conn = psycopg2.connect(CONN_STR)
        return conn
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        sys.exit(1)

def parse_run_from_path(rel_path):
    """
    Parses metadata from relative path. 
    Supports two formats:
    1. Standard: board_code/date_str/side/illumination/run_code/filename
    2. Flat: filename (img_ID_YYYY-MM-DD_HH-mm-ss-mmm.jpg)
    """
    parts = rel_path.split(os.sep)
    
    # 1. Check for standard 6-part structure
    if len(parts) == 6:
        return {
            "board_code": parts[0],
            "date_str": parts[1],
            "side": parts[2],
            "illumination": parts[3],
            "run_code": parts[4],
            "filename": parts[5],
            "rel_dir": os.path.dirname(rel_path)
        }
    
    # 2. Check for flat structure (just filename)
    filename = parts[-1]
    if filename.startswith("img_") and filename.endswith(".jpg"):
        # Pattern: img_0_2026-03-02_09-42-01-294.jpg
        name_parts = filename.replace(".jpg", "").split("_")
        if len(name_parts) >= 3:
            date_part = name_parts[2] # "2026-03-02"
            clean_date = date_part.replace("-", "")
            return {
                "board_code": "GENERAL",
                "date_str": clean_date,
                "side": "TOP",
                "illumination": "LR",
                "run_code": f"RUN_{clean_date}_FLAT",
                "filename": filename,
                "rel_dir": "."
            }
            
    return None

def import_images():
    base_images_path = os.getenv("IMAGE_WATCH_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "images")))
    print(f"📂 Scanning images in: {os.path.relpath(base_images_path)}")
    
    if not os.path.exists(base_images_path):
        print("❌ 'images' directory not found.")
        return

    # Group files by run
    runs_to_import = {} # run_code -> { metadata, images: [] }

    for root, dirs, files in os.walk(base_images_path):
        for file in files:
            if file.startswith(".") or file in ["sample.png", "sample.jpg", "sample.jpeg"]:
                continue
                
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, base_images_path)
            
            meta = parse_run_from_path(rel_path)
            if not meta:
                # print(f"⚠️ Skipping non-standard file structure: {rel_path}")
                continue
                
            run_code = meta["run_code"]
            
            if run_code not in runs_to_import:
                runs_to_import[run_code] = {
                    "run_code": run_code,
                    "board_code": meta["board_code"],
                    "date_str": meta["date_str"],
                    "side": meta["side"],
                    "illumination": meta["illumination"],
                    "machine_id": "IMPORTED",
                    "status": "COMPLETED",
                    "note": "Imported from filesystem",
                    "start_time": datetime.datetime.now(), # Estimate
                    "images": []
                }
            
            # File info
            try:
                size_bytes = os.path.getsize(abs_path)
            except:
                size_bytes = 0
            
            # Condition (PASS/FAIL) usually in filename? 
            # E.g. M18-F-T-LR-0-0.jpg (F=Fail, P=Pass)
            condition = "UNKNOWN"
            parts_name = meta["filename"].split("-")
            if len(parts_name) > 1:
                cond_code = parts_name[1]
                if cond_code == "F": condition = "FAIL"
                elif cond_code == "P": condition = "PASS"

            # Parse row/col from filename if possible: M18-F-T-LR-{row}-{col}.jpg
            row = 0
            col = 0
            if len(parts_name) >= 6:
                try:
                    row = int(parts_name[-2])
                    col = int(parts_name[-1].split(".")[0])
                except:
                    pass

            runs_to_import[run_code]["images"].append({
                "image_id": str(uuid.uuid4()),
                "file_path": rel_path,
                "file_name": meta["filename"],
                "file_size_bytes": size_bytes,
                "condition": condition,
                "row_idx": row,
                "col_idx": col,
                "capture_time": datetime.datetime.now() # Estimate
            })

    print(f"🔎 Found {len(runs_to_import)} runs to process.")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        total_runs_added = 0
        total_images_added = 0

        for run_code, data in runs_to_import.items():
            # 1. UPSERT Run
            # We use ON CONFLICT DO NOTHING to simple skip if exists
            run_sql = """
                INSERT INTO runs (
                    run_code, machine_id, board_code, date_str, side, illumination, 
                    status, note, start_time
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_code) DO NOTHING
            """
            cursor.execute(run_sql, (
                data["run_code"], data["machine_id"], data["board_code"], 
                data["date_str"], data["side"], data["illumination"],
                data["status"], data["note"], data["start_time"]
            ))
            
            if cursor.rowcount > 0:
                total_runs_added += 1

            # 2. Get existing images for this run to avoid duplicates? 
            # Or just blindly insert with ON CONFLICT? 
            # Our images table schema: image_id is PK (UUID). 
            # We don't have a unique constraint on file_path in schema... 
            # Wait, let's check init.sql. 
            # No unique index on file_path. So we could get duplicates if we re-import.
            # We should check if file_path exists for this run.
            
            # Let's do a bulk check or just check by file_path.
            # Since importing is batch, let's query existing paths for this run first.
            cursor.execute("SELECT file_path FROM images WHERE run_code = %s", (run_code,))
            existing_paths = set(r[0] for r in cursor.fetchall())

            images_to_insert = []
            for img in data["images"]:
                if img["file_path"] not in existing_paths:
                    images_to_insert.append((
                        img["image_id"], run_code, img["file_path"],
                        img["row_idx"], img["col_idx"], img["condition"],
                        img["capture_time"], img["file_name"], img["file_size_bytes"]
                    ))
            
            if images_to_insert:
                img_sql = """
                    INSERT INTO images (
                        image_id, run_code, file_path, row_idx, col_idx, 
                        condition, capture_time, file_name, file_size_bytes
                    ) VALUES %s
                """
                execute_values(cursor, img_sql, images_to_insert)
                total_images_added += len(images_to_insert)

        conn.commit()
        print(f"✅ Import Complete!")
        print(f"   Runs Added: {total_runs_added}")
        print(f"   Images Added: {total_images_added}")

    except Exception as e:
        conn.rollback()
        print(f"❌ Import Failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import_images()
