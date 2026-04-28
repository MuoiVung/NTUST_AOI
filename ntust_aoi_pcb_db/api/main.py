import os
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
IMAGE_WATCH_DIR = os.getenv("IMAGE_WATCH_DIR", r"C:\Users\OMNI-3125HTT-ADN\Desktop\images")

DB_DSN = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/pcb_aoi_db"

# ─── Connection Pool ──────────────────────────────────────────────────────────
# Reuses connections instead of opening/closing one per request.
_pool: pg_pool.SimpleConnectionPool | None = None

def get_pool() -> pg_pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = pg_pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DB_DSN,
        )
    return _pool

def get_db_connection():
    return get_pool().getconn()

def release_db_connection(conn):
    get_pool().putconn(conn)

# ─── App Lifecycle ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise pool on startup
    get_pool()
    yield
    # Close all connections on shutdown
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
    board_code: Optional[str] = None,
    result: Optional[str] = None,
    date_str: Optional[str] = None,
    illumination: Optional[str] = None,
):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT * FROM runs WHERE 1=1"
            params: list = []
            if board_code:
                query += " AND board_code ILIKE %s"
                params.append(f"%{board_code}%")
            if result:
                query += " AND status = %s"
                params.append(result)
            if date_str:
                query += " AND date_str = %s"
                params.append(date_str)
            if illumination:
                query += " AND illumination = %s"
                params.append(illumination)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()

            return [
                {
                    **dict(row),
                    "result": row.get("status"),
                    "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                    "start_time": row["start_time"].isoformat() if row.get("start_time") else None,
                }
                for row in rows
            ]
    finally:
        release_db_connection(conn)


@app.get("/runs/{run_code}")
def get_run(run_code: str):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM runs WHERE run_code = %s", (run_code,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Run not found")
            return {
                **dict(row),
                "result": row.get("status"),
                "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
                "start_time": row["start_time"].isoformat() if row.get("start_time") else None,
            }
    finally:
        release_db_connection(conn)


@app.get("/images/")
def get_images(run_code: str, limit: int = 50, offset: int = 0):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM images WHERE run_code = %s ORDER BY row_idx, col_idx LIMIT %s OFFSET %s",
                (run_code, limit, offset),
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
            if "note" in payload:
                updates.append("note = %s")
                params.append(payload["note"])
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


@app.put("/runs/{run_code}")
def update_run(run_code: str, payload: dict = Body(...)):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            updates, params = [], []
            if "illumination" in payload:
                updates.append("illumination = %s")
                params.append(payload["illumination"])
            if "note" in payload:
                updates.append("note = %s")
                params.append(payload["note"])
            if "board_code" in payload:
                updates.append("board_code = %s")
                params.append(payload["board_code"])
            if not updates:
                return {"message": "No updates provided"}
            cur.execute(
                f"UPDATE runs SET {', '.join(updates)} WHERE run_code = %s",
                [*params, run_code],
            )
            conn.commit()
            return {"message": "Updated successfully"}
    finally:
        release_db_connection(conn)


@app.delete("/images/{image_id}")
def delete_image(image_id: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM images WHERE image_id = %s", (image_id,))
            conn.commit()
            return {"message": "Deleted successfully"}
    finally:
        release_db_connection(conn)


@app.delete("/runs/{run_code}")
def delete_run(run_code: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM runs WHERE run_code = %s", (run_code,))
            conn.commit()
            return {"message": "Deleted successfully"}
    finally:
        release_db_connection(conn)


@app.get("/images/proxy/{image_id}")
def proxy_image(image_id: str):
    """Serves images directly from the local filesystem to avoid CORS issues."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT file_path FROM images WHERE image_id = %s", (image_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Image not found")
            file_path = row["file_path"]
    finally:
        release_db_connection(conn)

    abs_path = file_path if os.path.isabs(file_path) else os.path.join(IMAGE_WATCH_DIR, file_path)

    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail=f"File not found on disk: {abs_path}")

    return FileResponse(
        path=abs_path,
        media_type="image/jpeg",
        filename=os.path.basename(abs_path),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
