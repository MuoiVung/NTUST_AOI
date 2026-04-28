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

# Mock Metadata (Matching New Schema)
MOCK_RUN_NUMBER = "RUN_AUTO_001"
MOCK_SERIAL = "SN-AUTO-MONITOR"
MOCK_BOARD_NUMBER = "AUTO_BOARD_DEF"
MOCK_ORDER_NUMBER = "AUTO_ORDER_001"
MOCK_MACHINE_ID = "HMI_MONITOR_01"

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        return None

def ensure_dependencies_exist(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO orders (order_number, target_quantity, status)
                VALUES (%s, 100, 'ACTIVE') ON CONFLICT (order_number) DO NOTHING;
            """, (MOCK_ORDER_NUMBER,))
            cur.execute("""
                INSERT INTO board_numbers (board_number, grid_rows, grid_cols)
                VALUES (%s, 1, 1) ON CONFLICT (board_number) DO NOTHING;
            """, (MOCK_BOARD_NUMBER,))
            cur.execute("""
                INSERT INTO runs (run_number, serial_number, board_number, order_number, machine_id, status)
                VALUES (%s, %s, %s, %s, %s, 'COMPLETED') ON CONFLICT (run_number) DO NOTHING;
            """, (MOCK_RUN_NUMBER, MOCK_SERIAL, MOCK_BOARD_NUMBER, MOCK_ORDER_NUMBER, MOCK_MACHINE_ID))
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error ensuring dependencies: {e}")

def insert_image_record(file_path, file_name, file_size):
    conn = get_db_connection()
    if not conn: return

    try:
        ensure_dependencies_exist(conn)
        with conn.cursor() as cur:
            logical_path = os.path.abspath(file_path)
            
            # Check for existing record to avoid duplicates
            cur.execute("SELECT image_id FROM images WHERE local_path = %s", (logical_path,))
            if cur.fetchone():
                logger.info(f"Record already exists for: {file_name}")
                return

            insert_img_sql = """
            INSERT INTO images (run_number, side, local_path, row_idx, col_idx, condition, file_size_bytes)
            VALUES (%s, 'Top', %s, 0, 0, 'PASS', %s)
            """
            cur.execute(insert_img_sql, (MOCK_RUN_NUMBER, logical_path, file_size))
            conn.commit()
            logger.info(f"SUCCESS: Inserted record for '{file_name}'")
    except Exception as e:
        conn.rollback()
        logger.error(f"FAIL: Failed to insert record for '{file_name}': {e}")
    finally:
        conn.close()

class ImageHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        self.process_file(event.src_path)
        
    def process_file(self, file_path):
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_name)
        if ext.lower() in ALLOWED_EXTENSIONS:
            logger.info(f"Processing image: {file_name}")
            time.sleep(0.5)
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
