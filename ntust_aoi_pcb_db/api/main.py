import os
import time
from contextlib import asynccontextmanager
from typing import Optional
import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_ROOT_USER", "admin")
DB_PASS = os.getenv("DB_ROOT_PASSWORD", "aoi123!")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")
IMAGE_WATCH_DIR = os.getenv("IMAGE_WATCH_DIR", "/Users/namtranviet/Desktop/images")

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


@app.get("/images/proxy/{image_id}")
def proxy_image(image_id: str):
    """Serves images directly from the local filesystem."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT local_path FROM images WHERE image_id = %s", (image_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Image not found")
            file_path = row["local_path"]
    finally:
        release_db_connection(conn)

    if not file_path:
        raise HTTPException(status_code=404, detail="Image has been moved to longterm storage (local_path is NULL)")

    abs_path = file_path if os.path.isabs(file_path) else os.path.join(IMAGE_WATCH_DIR, file_path)

    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail=f"File not found on disk: {abs_path}")

    return FileResponse(
        path=abs_path,
        media_type="image/jpeg",
        filename=os.path.basename(abs_path),
    )


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
