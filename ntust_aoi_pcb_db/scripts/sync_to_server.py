import os
import time
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from minio import Minio
from dotenv import load_dotenv

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# DB Config
DB_USER = os.getenv("DB_ROOT_USER")
DB_PASS = os.getenv("DB_ROOT_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = "pcb_aoi_db"

# MinIO Config
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "192.168.40.21:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY", "aoi_admin")
MINIO_SECRET = os.getenv("MINIO_SECRET_KEY", "aoi@1234")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "aoi-images")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )

def get_minio_client():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS,
        secret_key=MINIO_SECRET,
        secure=MINIO_SECURE
    )

def sync_images():
    conn = None
    try:
        conn = get_db_connection()
        client = get_minio_client()
        
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Get Retention Policy
            cur.execute("SELECT config_value FROM system_configs WHERE config_name = 'longterm_sync_interval'")
            row = cur.fetchone()
            # If not found or empty, default to a very long time (no sync) to be safe
            retention_seconds = int(row['config_value']) if (row and row['config_value']) else 999999999
            
            # 2. Find images to sync (only those that still have a local_path)
            # Use database-side time calculation to avoid timezone mismatch between host and docker
            cur.execute("""
                SELECT image_id, run_number, local_path, capture_time 
                FROM images 
                WHERE is_uploaded_longterm = FALSE 
                AND local_path IS NOT NULL
                AND capture_time <= (NOW() - (INTERVAL '1 second' * %s))
                LIMIT 50
            """, (retention_seconds,))
            
            images_to_sync = cur.fetchall()
            
            if not images_to_sync:
                return

            logger.info(f"Syncing {len(images_to_sync)} images to MinIO (Policy: {retention_seconds}s)...")

            for img in images_to_sync:
                local_file = img['local_path']
                if not os.path.exists(local_file):
                    logger.warning(f"File missing, marking as skipped: {local_file}")
                    cur.execute("UPDATE images SET local_path = NULL WHERE image_id = %s", (img['image_id'],))
                    conn.commit()
                    continue

                file_name = os.path.basename(local_file)
                object_name = f"runs/{img['run_number']}/{file_name}"

                try:
                    # A. Upload to MinIO
                    client.fput_object(MINIO_BUCKET, object_name, local_file)
                    
                    # B. Delete local file
                    os.remove(local_file)
                    logger.info(f"DELETED local file: {local_file}")
                    
                    # C. Update DB: Mark as uploaded and CLEAR local_path
                    cur.execute("""
                        UPDATE images 
                        SET is_uploaded_longterm = TRUE, 
                            longterm_path = %s,
                            local_path = NULL
                        WHERE image_id = %s
                    """, (f"{MINIO_BUCKET}/{object_name}", img['image_id']))
                    
                    conn.commit()
                    logger.info(f"SUCCESS: {file_name} moved to Cloud.")
                    
                except Exception as e:
                    logger.error(f"Failed to move {file_name}: {e}")
                    conn.rollback()

    except Exception as e:
        logger.error(f"Sync error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    logger.info("Cloud Sync Service Started.")
    while True:
        try:
            sync_images()
        except Exception as e:
            logger.error(f"Loop error: {e}")
        time.sleep(10)
