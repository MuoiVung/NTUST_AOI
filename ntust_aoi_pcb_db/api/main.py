import os
import time
from contextlib import asynccontextmanager
from typing import Optional
import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from dotenv import load_dotenv
from minio import Minio
import io
import mimetypes
import subprocess

load_dotenv()

DB_USER = os.getenv("DB_ROOT_USER", "admin")
DB_PASS = os.getenv("DB_ROOT_PASSWORD", "aoi123!")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")
IMAGE_WATCH_DIR = os.getenv("IMAGE_WATCH_DIR", "/Users/namtranviet/Desktop/images")

# MinIO Config
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "192.168.40.21:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS_KEY", "aoi_admin")
MINIO_SECRET = os.getenv("MINIO_SECRET_KEY", "aoi@1234")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "aoi-images")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS,
    secret_key=MINIO_SECRET,
    secure=MINIO_SECURE
)

DB_DSN = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/pcb_aoi_db"

# ─── Connection Pool ──────────────────────────────────────────────────────────
_pool: pg_pool.SimpleConnectionPool | None = None

def get_pool() -> pg_pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        # Retry logic for initial connection
        max_retries = 5
        for i in range(max_retries):
            try:
                _pool = pg_pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=DB_DSN,
                )
                print(f"Successfully connected to database on attempt {i+1}")
                break
            except Exception as e:
                if i == max_retries - 1:
                    print(f"Failed to connect to database after {max_retries} attempts.")
                    raise e
                print(f"Database not ready (attempt {i+1}/{max_retries}). Retrying in 2s...")
                time.sleep(2)
    return _pool

def get_db_connection():
    return get_pool().getconn()

def release_db_connection(conn):
    get_pool().putconn(conn)

# ─── App Lifecycle ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize pool on startup
    try:
        get_pool()
    except Exception as e:
        print(f"CRITICAL: Could not initialize database pool: {e}")
    yield
    # Close pool on shutdown
    if _pool:
        _pool.closeall()

app = FastAPI(title="AOI API", lifespan=lifespan)
app.router.redirect_slashes = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/runs/")
def get_runs(
    limit: int = 50,
    board_number: Optional[str] = None,
    order_number: Optional[str] = None,
    status: Optional[str] = None,
    serial_number: Optional[str] = None,
):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM runs WHERE 1=1"
            params: list = []
            if board_number:
                query += " AND board_number ILIKE %s"
                params.append(f"%{board_number}%")
            if order_number:
                query += " AND order_number ILIKE %s"
                params.append(f"%{order_number}%")
            if status:
                query += " AND status = %s"
                params.append(status)
            if serial_number:
                query += " AND serial_number ILIKE %s"
                params.append(f"%{serial_number}%")

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()

            return [
                {
                    **dict(row),
                    "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                    "start_time": row["start_time"].isoformat() if row.get("start_time") else None,
                }
                for row in rows
            ]
    finally:
        release_db_connection(conn)


@app.get("/runs/{run_number}")
def get_run(run_number: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM runs WHERE run_number = %s", (run_number,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Run not found")
            return {
                **dict(row),
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                "start_time": row["start_time"].isoformat() if row.get("start_time") else None,
            }
    finally:
        release_db_connection(conn)


@app.get("/images/")
def get_images(run_number: str, limit: int = 50, offset: int = 0):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM images WHERE run_number = %s ORDER BY side, row_idx, col_idx LIMIT %s OFFSET %s",
                (run_number, limit, offset),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_db_connection(conn)


@app.put("/images/{image_id}")
def update_image(image_id: str, payload: dict = Body(...)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            updates, params = [], []
            if "condition" in payload:
                updates.append("condition = %s")
                params.append(payload["condition"])
            if not updates:
                return {"message": "No updates provided"}
            cur.execute(
                f"UPDATE images SET {', '.join(updates)} WHERE image_id = %s",
                [*params, image_id],
            )
            conn.commit()
            return {"message": "Updated successfully"}
    finally:
        release_db_connection(conn)


@app.delete("/images/{image_id}")
def delete_image(image_id: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Get paths
            cur.execute("SELECT local_path, longterm_path, is_uploaded_longterm FROM images WHERE image_id = %s", (image_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Image not found")
            
            local_path = row["local_path"]
            longterm_path = row["longterm_path"]
            is_cloud = row["is_uploaded_longterm"]

            # 2. Delete local file
            if local_path:
                abs_path = local_path if os.path.isabs(local_path) else os.path.join(IMAGE_WATCH_DIR, local_path)
                if os.path.exists(abs_path):
                    try:
                        os.remove(abs_path)
                    except Exception as e:
                        print(f"Warning: Failed to delete local file {abs_path}: {e}")

            # 3. Delete from MinIO (Cloud)
            if is_cloud and longterm_path:
                try:
                    parts = longterm_path.split('/', 1)
                    if len(parts) == 2:
                        bucket = parts[0]
                        obj_name = parts[1]
                        minio_client.remove_object(bucket, obj_name)
                except Exception as e:
                    print(f"Warning: Failed to delete cloud file {longterm_path}: {e}")

            # 4. Delete DB record
            cur.execute("DELETE FROM images WHERE image_id = %s", (image_id,))
            conn.commit()
            
            return {"message": "Image deleted successfully"}
    finally:
        release_db_connection(conn)

@app.delete("/runs/{run_number}")
def delete_run(run_number: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Fetch all images for this run to delete physical files
            cur.execute("SELECT local_path, longterm_path, is_uploaded_longterm FROM images WHERE run_number = %s", (run_number,))
            images = cur.fetchall()
            
            for img in images:
                local_path = img["local_path"]
                longterm_path = img["longterm_path"]
                is_cloud = img["is_uploaded_longterm"]
                
                # Delete local
                if local_path:
                    abs_path = local_path if os.path.isabs(local_path) else os.path.join(IMAGE_WATCH_DIR, local_path)
                    if os.path.exists(abs_path):
                        try:
                            os.remove(abs_path)
                        except Exception as e:
                            print(f"Warning: Failed to delete local file {abs_path}: {e}")
                
                # Delete cloud
                if is_cloud and longterm_path:
                    try:
                        parts = longterm_path.split('/', 1)
                        if len(parts) == 2:
                            minio_client.remove_object(parts[0], parts[1])
                    except Exception as e:
                        print(f"Warning: Failed to delete cloud file {longterm_path}: {e}")

            # 2. Delete the images from DB
            cur.execute("DELETE FROM images WHERE run_number = %s", (run_number,))
            
            # 3. Delete the run from DB
            cur.execute("DELETE FROM runs WHERE run_number = %s", (run_number,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Run not found")
                
            conn.commit()
            return {"message": f"Run {run_number} and all its images deleted successfully"}
    finally:
        release_db_connection(conn)

@app.get("/images/proxy/{image_id}")
def proxy_image(image_id: str):
    """Serves images from local disk or fetches from MinIO if archived."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT local_path, longterm_path, is_uploaded_longterm FROM images WHERE image_id = %s", (image_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Image not found in database")
            
            local_path = row["local_path"]
            longterm_path = row["longterm_path"]
            is_cloud = row["is_uploaded_longterm"]
    finally:
        release_db_connection(conn)

    # 1. Try serving from LOCAL DISK first
    if local_path:
        abs_path = local_path if os.path.isabs(local_path) else os.path.join(IMAGE_WATCH_DIR, local_path)
        if os.path.isfile(abs_path):
            mime_type, _ = mimetypes.guess_type(abs_path)
            return FileResponse(
                path=abs_path,
                media_type=mime_type or "image/jpeg",
                filename=os.path.basename(abs_path),
                headers={"Access-Control-Allow-Origin": "*"}
            )

    # 2. If not on local disk, try fetching from MINIO
    if is_cloud and longterm_path:
        try:
            parts = longterm_path.split('/', 1)
            bucket = parts[0]
            obj_name = parts[1]
            
            # Detect mime type from file extension on cloud
            mime_type, _ = mimetypes.guess_type(obj_name)
            
            response = minio_client.get_object(bucket, obj_name)
            data = response.read()
            response.close()
            response.release_conn()
            
            return Response(
                content=data, 
                media_type=mime_type or "image/jpeg",
                headers={
                    "Cache-Control": "max-age=3600",
                    "Access-Control-Allow-Origin": "*"
                }
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Error fetching from Cloud: {str(e)}")

    raise HTTPException(status_code=404, detail="Image file not found locally or on Cloud")


@app.get("/configs/")
def get_configs():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM system_configs ORDER BY config_key")
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_db_connection(conn)


@app.put("/configs/{config_name}")
def update_config(config_name: str, payload: dict = Body(...)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if "config_value" not in payload:
                raise HTTPException(status_code=400, detail="Missing config_value")
            cur.execute(
                "UPDATE system_configs SET config_value = %s WHERE config_name = %s",
                (payload["config_value"], config_name),
            )
            conn.commit()
            return {"message": "Config updated successfully"}
    finally:
        release_db_connection(conn)


@app.get("/services/status")
def get_services_status():
    """Checks if specific AOI services are running in the OS."""
    try:
        # Check for sync_to_server.py in tasklist
        output = subprocess.check_output('wmic process where "commandline like \'%sync_to_server.py%\'" get commandline', shell=True).decode()
        is_sync_running = "sync_to_server.py" in output and "wmic" not in output
        
        # Check for folder_monitor.py
        output_monitor = subprocess.check_output('wmic process where "commandline like \'%folder_monitor.py%\'" get commandline', shell=True).decode()
        is_monitor_running = "folder_monitor.py" in output_monitor and "wmic" not in output_monitor

        return {
            "sync_service": "running" if is_sync_running else "stopped",
            "monitor_service": "running" if is_monitor_running else "stopped"
        }
    except Exception:
        return {
            "sync_service": "unknown",
            "monitor_service": "unknown"
        }


@app.post("/configs/init")
def init_configs():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Pre-register the mandatory keys with empty values if they don't exist
            configs = [
                ('longterm_sync_interval', '0', 'Seconds'),
                ('sync_retry_interval', '0', 'Seconds')
            ]
            for name, val, unit in configs:
                cur.execute(
                    "INSERT INTO system_configs (config_name, config_value, unit) VALUES (%s, %s, %s) ON CONFLICT (config_name) DO NOTHING",
                    (name, val, unit)
                )
            conn.commit()
            return {"message": "System keys initialized"}
    finally:
        release_db_connection(conn)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
