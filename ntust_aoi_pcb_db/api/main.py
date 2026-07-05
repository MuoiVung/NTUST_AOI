import asyncio
import select

import os
import time
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List, Optional
import psycopg2

class RunStartRequest(BaseModel):
    serial_number: str

class ImageCreateRequest(BaseModel):
    run_number: str
    side: str
    row_idx: int
    col_idx: int
    file_size_bytes: int
    local_path: str

from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query, Body, WebSocket, WebSocketDisconnect
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
IMAGE_WATCH_DIR = os.getenv("IMAGE_WATCH_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "watch_dir")))

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
    asyncio.create_task(listen_pg_notifications())
    yield
    # Close pool on shutdown
    if _pool:
        _pool.closeall()

app = FastAPI(title="AOI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.router.redirect_slashes = False

# ─── WebSocket Connection Manager ─────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# ─── PG Notify Listener ───────────────────────────────────────────────────────
async def listen_pg_notifications():
    print("[WS] PG notification listener task started")
    while True:
        conn = None
        try:
            conn = psycopg2.connect(DB_DSN)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            with conn.cursor() as cur:
                cur.execute("LISTEN ui_update;")
            print("[WS] Connected and listening to PG NOTIFY ui_update")
            while True:
                r, _, _ = select.select([conn], [], [], 1.0)
                if r:
                    conn.poll()
                    while conn.notifies:
                        notify = conn.notifies.pop(0)
                        await manager.broadcast(notify.payload)
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[WS] Error/Disconnect in pg notification listener: {e}")
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            print("[WS] Reconnecting to database in 3 seconds...")
            await asyncio.sleep(3)

@app.websocket("/ws/ui-updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)



# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/runs/")
def get_runs(
    limit: int = 50,
    offset: int = 0,
    board_number: Optional[str] = None,
    m_no: Optional[str] = None,
    status: Optional[str] = None,
    serial_number: Optional[str] = None,
):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conn.commit()
            base_query = " FROM runs WHERE 1=1"
            params: list = []
            if board_number:
                base_query += " AND board_number ILIKE %s"
                params.append(f"%{board_number}%")
            if m_no:
                base_query += " AND m_no ILIKE %s"
                params.append(f"%{m_no}%")
            if status:
                base_query += " AND status = %s"
                params.append(status)
            if serial_number:
                base_query += " AND serial_number ILIKE %s"
                params.append(f"%{serial_number}%")

            # Get total count
            count_query = "SELECT COUNT(*)" + base_query
            cur.execute(count_query, params)
            total_count = cur.fetchone()["count"]

            # Get paginated data
            query = "SELECT *" + base_query + " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cur.execute(query, params)
            rows = cur.fetchall()

            data = [
                {
                    **dict(row),
                    "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                    "start_time": row["start_time"].isoformat() if row.get("start_time") else None,
                }
                for row in rows
            ]
            
            return {"data": data, "total": total_count}
    finally:
        release_db_connection(conn)


@app.get("/runs/{run_number}")
def get_run(run_number: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conn.commit()
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
            conn.commit()
            cur.execute(
                "SELECT * FROM images WHERE run_number = %s ORDER BY side, row_idx, col_idx LIMIT %s OFFSET %s",
                (run_number, limit, offset),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        release_db_connection(conn)


@app.post("/images/")
def create_image(img: ImageCreateRequest):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            insert_sql = """
            INSERT INTO images (run_number, side, local_path, row_idx, col_idx, condition, file_size_bytes)
            VALUES (%s, %s, %s, %s, %s, 'UNKNOWN', %s)
            RETURNING image_id
            """
            cur.execute(insert_sql, (
                img.run_number,
                img.side.capitalize(),
                img.local_path,
                img.row_idx,
                img.col_idx,
                img.file_size_bytes
            ))
            image_id = cur.fetchone()[0]
            conn.commit()
            return {"status": "success", "image_id": image_id}
    except psycopg2.IntegrityError:
        conn.rollback()
        return {"status": "ignored", "detail": "Record already exists"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
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

@app.post("/runs/start")
def start_machine_run(req: RunStartRequest):
    """
    Called by Operator Dashboard to trigger a run.
    Saves the pending serial number into DB so PC Controller can pick it up.
    """
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    try:
        with conn.cursor() as cur:
            # 1. Validation: Prevent new run if machine is currently processing
            cur.execute("SELECT COUNT(*) FROM runs WHERE status IN ('PENDING', 'RUNNING')")
            if cur.fetchone()[0] > 0:
                raise HTTPException(status_code=400, detail="Máy đang quét (Machine is currently processing). Không thể nhập mã mới lúc này!")

            # Upsert into system_configs
            cur.execute("""
                INSERT INTO system_configs (config_name, config_value) 
                VALUES ('pending_run_sn', %s)
                ON CONFLICT (config_name) DO UPDATE SET config_value = EXCLUDED.config_value
            """, (req.serial_number,))
            
            # Try to lookup from Shopfloor API synchronously for UI immediate feedback
            import urllib.request
            import urllib.parse
            import json
            m_no = "-"
            actual_qty = 0
            try:
                # Use environment variable or fallback to mock
                base_url = os.environ.get("SHOPFLOOR_API_URL", "http://127.0.0.1:9090/api/v1/shopfloor/info")
                query = urllib.parse.urlencode({"sn": req.serial_number})
                url = f"{base_url}?{query}"
                req_api = urllib.request.Request(url)
                with urllib.request.urlopen(req_api, timeout=1.5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode())
                        if data.get("HasData") == "1" or data.get("M_NO"):
                            m_no = data.get("M_NO") or "-"
            except Exception as e:
                print(f"Warning: Synchronous API lookup failed in start_run: {e}")

            # Get actual quantity for this order
            if m_no != "-":
                cur.execute("SELECT actual_quantity FROM orders WHERE m_no = %s", (m_no,))
                ord_row = cur.fetchone()
                if ord_row:
                    actual_qty = ord_row[0]  # Tuple cursor
            else:
                cur.execute("SELECT COUNT(*) FROM runs WHERE (m_no IS NULL OR m_no = '' OR m_no = '-') AND status NOT IN ('PENDING', 'RUNNING') AND is_latest = TRUE")
                actual_qty = cur.fetchone()[0]

            # Send asynchronous notification to PC Controller
            # Using psycopg2's NOTIFY functionality
            cur.execute("SELECT pg_notify('new_run_sn', %s)", (req.serial_number,))
            
            conn.commit()
            return {
                "status": "success", 
                "message": f"Run queued for {req.serial_number}",
                "m_no": m_no,
                "actual_quantity": actual_qty
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            release_db_connection(conn)

@app.delete("/runs/{run_number}")
def delete_run(run_number: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conn.commit()
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
            
            # 3. Fetch m_no and sn before deleting
            cur.execute("SELECT m_no, serial_number FROM runs WHERE run_number = %s", (run_number,))
            run_row = cur.fetchone()
            m_no = run_row["m_no"] if run_row else None
            sn = run_row["serial_number"] if run_row else None

            # 3.5 Delete physical run directory and parent SN directory if empty
            if m_no and sn:
                import shutil
                run_dir = os.path.join(IMAGE_WATCH_DIR, m_no, sn, run_number)
                if os.path.exists(run_dir):
                    shutil.rmtree(run_dir, ignore_errors=True)
                
                sn_dir = os.path.join(IMAGE_WATCH_DIR, m_no, sn)
                if os.path.exists(sn_dir):
                    try:
                        if not os.listdir(sn_dir):
                            os.rmdir(sn_dir)
                    except Exception as e:
                        print(f"Warning: Failed to remove SN directory {sn_dir}: {e}")

            # 4. Delete the run from DB
            cur.execute("DELETE FROM runs WHERE run_number = %s", (run_number,))
            
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Run not found")
                
            # 5. Update actual_quantity
            if m_no:
                cur.execute("""
                    UPDATE orders
                    SET actual_quantity = (
                        SELECT COUNT(*) FROM runs WHERE m_no = %s AND status != 'PENDING' AND is_latest = TRUE
                    )
                    WHERE m_no = %s
                """, (m_no, m_no))
                
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
            conn.commit()
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

@app.get("/system/status")
def get_system_status():
    import socket
    import urllib.request
    
    # Check PLC simulator from DB
    plc_status = "ERROR"
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conn.commit()
            cur.execute("SELECT config_value FROM system_configs WHERE config_name = 'plc_status'")
            row = cur.fetchone()
            if row and row["config_value"]:
                plc_status = row["config_value"]
    except Exception:
        pass
    finally:
        if conn:
            release_db_connection(conn)
        
    # Check Shopfloor API
    api_status = "ERROR"
    try:
        import os
        base_url = os.environ.get("SHOPFLOOR_API_URL", "http://127.0.0.1:9090")
        ping_url = base_url.split("/ashx")[0] + "/ping" if "/ashx" in base_url else "http://127.0.0.1:9090/ping"
        req = urllib.request.Request(ping_url)
        with urllib.request.urlopen(req, timeout=0.5) as response:
            if response.status == 200:
                api_status = "OK"
    except Exception:
        pass
        
    # Camera is hardcoded OK for now
    camera_status = "OK"
    
    current_order = "-"
    actual_quantity = 0
    is_processing = False
    active_sn = ""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Force a fresh transaction snapshot
            conn.commit()
            
            # Get latest run info
            cur.execute("SELECT m_no, serial_number, status FROM runs ORDER BY start_time DESC LIMIT 1")
            run_row = cur.fetchone()
            if run_row:
                current_order = run_row["m_no"] or "-"
                active_sn = run_row["serial_number"] or ""
            # Note: is_processing is now derived from the DB status to survive page reloads.
            cur.execute("SELECT COUNT(*) as count FROM runs WHERE status IN ('PENDING', 'RUNNING')")
            if cur.fetchone()["count"] > 0:
                is_processing = True
                
            # Get actual quantity for this order
            if current_order and current_order != "-":
                cur.execute("SELECT actual_quantity FROM orders WHERE m_no = %s", (current_order,))
                ord_row = cur.fetchone()
                if ord_row:
                    actual_quantity = ord_row["actual_quantity"]
            else:
                # If there's no specific order, just count completed runs that have no order
                cur.execute("SELECT COUNT(*) as count FROM runs WHERE (m_no IS NULL OR m_no = '' OR m_no = '-') AND status NOT IN ('PENDING', 'RUNNING') AND is_latest = TRUE")
                actual_quantity = cur.fetchone()["count"]
    except Exception as e:
        print(f"Error in /system/status DB query: {e}")
        pass
    finally:
        if conn:
            release_db_connection(conn)
            
    return {
        "plc": plc_status,
        "shopfloor": api_status,
        "camera": camera_status,
        "current_order": current_order,
        "active_sn": active_sn,
        "actual_quantity": actual_quantity,
        "is_processing": is_processing
    }


@app.get("/configs/")
def get_configs():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conn.commit()
            cur.execute("SELECT * FROM system_configs WHERE config_name NOT IN ('pending_run_sn', 'plc_status') ORDER BY config_key")
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
                ('sync_retry_interval', '0', 'Seconds'),
                ('camera_fov_step_mm', '40.0', 'mm'),
                ('camera_margin_mm', '10.0', 'mm')
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
