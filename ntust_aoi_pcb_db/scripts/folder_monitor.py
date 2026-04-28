import os
import time
import logging
import random
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv
import psycopg2

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load Environment Variables
load_dotenv()

# Database Config
DB_USER = os.getenv("DB_ROOT_USER")
DB_PASSWORD = os.getenv("DB_ROOT_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")  # Use localhost for direct script execution, or "postgres" if running inside Docker
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = "pcb_aoi_db"

# Folder Monitoring Config
WATCH_DIR = os.getenv("IMAGE_WATCH_DIR", "./images/raw_incoming")
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}

# Mock Metadata
MOCK_RUN_CODE = "RUN_AUTO_MONITOR"
MOCK_MACHINE_ID = "HMI_MONITOR_01"
MOCK_BOARD_CODE = "AUTO_BOARD"
MOCK_SIDE = "TOP"
MOCK_ILLUMINATION = "AUTO_LIGHT"


def get_db_connection():
    """Establish connection to PostgreSQL"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def ensure_mock_run_exists(conn):
    """Ensure that the mock run_code exists in the runs table to satisfy foreign key constraints."""
    try:
        with conn.cursor() as cur:
            today_str = datetime.now().strftime("%Y%m%d")
            
            # Use PostgreSQL UPSERT (ON CONFLICT DO NOTHING)
            insert_run_sql = """
            INSERT INTO runs (run_code, machine_id, board_code, date_str, side, illumination, status, note)
            VALUES (%s, %s, %s, %s, %s, %s, 'COMPLETED', 'Auto-created by folder monitor')
            ON CONFLICT (run_code) DO NOTHING;
            """
            cur.execute(insert_run_sql, (MOCK_RUN_CODE, MOCK_MACHINE_ID, MOCK_BOARD_CODE, today_str, MOCK_SIDE, MOCK_ILLUMINATION))
            conn.commit()
            logger.info(f"Ensured run_code '{MOCK_RUN_CODE}' exists in database.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error ensuring mock run exists: {e}")

def insert_image_record(file_path, file_name, file_size):
    """Insert a new image record into the database."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        ensure_mock_run_exists(conn)

        with conn.cursor() as cur:
            # As requested: Store the absolute path in the database
            logical_path = os.path.abspath(file_path)
            
            # Generate random mock data for grid position (4x4 grid)
            row_idx = random.randint(0, 3)
            col_idx = random.randint(0, 3)
            
            insert_img_sql = """
            INSERT INTO images (run_code, file_path, file_name, file_size_bytes, capture_time, condition, row_idx, col_idx)
            VALUES (%s, %s, %s, %s, %s, 'PASS', %s, %s)
            """
            capture_time = datetime.now()
            
            cur.execute(insert_img_sql, (MOCK_RUN_CODE, logical_path, file_name, file_size, capture_time, row_idx, col_idx))
            conn.commit()
            logger.info(f"✅ Successfully inserted record for '{file_name}' -> Path: {logical_path}")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Failed to insert record for '{file_name}': {e}")
    finally:
        conn.close()


class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Ignore directories
        if event.is_directory:
            return

        file_path = event.src_path
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_name)

        if ext.lower() in ALLOWED_EXTENSIONS:
            logger.info(f"📸 Detected new image: {file_name}")
            
            # Add a small delay to ensure the file is completely written to disk before reading its size
            time.sleep(0.5)
            
            try:
                file_size = os.path.getsize(file_path)
                insert_image_record(file_path, file_name, file_size)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")


def start_monitoring():
    # Ensure watch directory exists
    os.makedirs(WATCH_DIR, exist_ok=True)
    
    logger.info(f"🚀 Starting folder monitor on directory: {WATCH_DIR}")
    logger.info("Waiting for new images...")

    event_handler = ImageHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping monitor...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_monitoring()
