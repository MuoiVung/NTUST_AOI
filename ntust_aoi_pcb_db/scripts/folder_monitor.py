import os
import time
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
import psycopg2

# Configure Logging (Removed emojis for Windows compatibility)
log_file = os.path.join(os.path.dirname(__file__), "folder_monitor.log")
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()

# Database Config
DB_USER = os.getenv("DB_ROOT_USER")
DB_PASSWORD = os.getenv("DB_ROOT_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = "pcb_aoi_db"

# Folder Monitoring Config
WATCH_DIR = os.getenv("IMAGE_WATCH_DIR", "./images/raw_incoming")
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.jfif'}

import re

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def insert_image_record(file_path, file_name, file_size):
    # Regex to parse: [run_code]_[side]_r[row]_c[col].jpg
    match = re.search(r'^(.*)_(TOP|BOTTOM)_r(\d+)_c(\d+)\.(jpg|jpeg|png|bmp|jfif)$', file_name, re.IGNORECASE)
    
    if match:
        run_number = match.group(1)
        side = match.group(2)
        row_idx = int(match.group(3))
        col_idx = int(match.group(4))
    else:
        # Fallback if filename doesn't match
        run_number = "UNKNOWN_RUN"
        side = "TOP"
        row_idx = 0
        col_idx = 0

    conn = get_db_connection()
    if not conn: return

    try:
        # Ensure dependencies (Wait: pc_controller already ensures the run exists, so we don't need to create mock runs anymore!)
        with conn.cursor() as cur:
            logical_path = os.path.abspath(file_path)
            
            # Check for existing record to avoid duplicates
            cur.execute("SELECT image_id FROM images WHERE local_path = %s", (logical_path,))
            if cur.fetchone():
                logger.info(f"Record already exists for: {file_name}")
                return

            insert_img_sql = """
            INSERT INTO images (run_number, side, local_path, row_idx, col_idx, condition, file_size_bytes)
            VALUES (%s, %s, %s, %s, %s, 'UNKNOWN', %s)
            """
            cur.execute(insert_img_sql, (run_number, side.capitalize(), logical_path, row_idx, col_idx, file_size))
            conn.commit()
            logger.info(f"SUCCESS: Inserted record for '{file_name}' (Run: {run_number}, R{row_idx} C{col_idx})")
    except Exception as e:
        conn.rollback()
        logger.error(f"FAIL: Failed to insert record for '{file_name}': {e}")
    finally:
        conn.close()

class ImageHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.last_processed = {}

    def on_created(self, event):
        if event.is_directory: return
        self.process_file(event.src_path)
        
    def process_file(self, file_path):
        file_name = os.path.basename(file_path)
        logical_path = os.path.abspath(file_path)
        
        # Debounce (Khử nhiễu): Bỏ qua nếu file này vừa được xử lý trong 2 giây qua
        current_time = time.time()
        if logical_path in self.last_processed:
            if current_time - self.last_processed[logical_path] < 2.0:
                return
                
        self.last_processed[logical_path] = current_time
        
        _, ext = os.path.splitext(file_name)
        if ext.lower() in ALLOWED_EXTENSIONS:
            logger.info(f"Processing image: {file_name}")
            time.sleep(0.5)  # Chờ hệ điều hành nhả file lock
            try:
                file_size = os.path.getsize(file_path)
                insert_image_record(file_path, file_name, file_size)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
        else:
            logger.info(f"Skipping unsupported file: {file_name}")

def start_monitoring():
    os.makedirs(WATCH_DIR, exist_ok=True)
    logger.info(f"START: Monitoring directory: {WATCH_DIR}")
    
    handler = ImageHandler()
    # Initial scan
    for root, dirs, files in os.walk(WATCH_DIR):
        for f in files:
            handler.process_file(os.path.join(root, f))

    observer = Observer()
    observer.schedule(handler, WATCH_DIR, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_monitoring()
