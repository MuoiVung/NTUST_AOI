import os
import uuid
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import Any, Optional, Dict
from dataclasses import dataclass, field
import socket

load_dotenv()

JsonDict = Dict[str, Any]

@dataclass
class RunInfo:
    run_code: str
    mode: str
    board_code: str = ""
    board_side: str = ""
    serial_number: str = ""
    production_work_order: str = ""
    packaging_work_order: str = ""
    semi_model: str = ""
    pcb_length_mm: Optional[float] = None
    pcb_width_mm: Optional[float] = None
    recipe_name: str = ""
    machine_id: str = field(default_factory=socket.gethostname)
    operator_id: str = ""
    image_root_path: str = ""
    note: str = ""
    api_has_data: str = ""
    api_msg: str = ""
    api_raw_response_json: Optional[JsonDict] = None

@dataclass
class StepInfo:
    step_index: int
    row_idx: Optional[int] = None
    col_idx: Optional[int] = None
    target_x_mm: Optional[float] = None
    target_y_mm: Optional[float] = None
    target_z_mm: Optional[float] = None
    status: str = "PENDING"
    note: str = ""

class PostgresDatabase:
    def __init__(self):
        import time
        max_retries = 15
        for attempt in range(max_retries):
            try:
                self.conn = psycopg2.connect(
                    dbname="pcb_aoi_db",
                    user=os.getenv("DB_ROOT_USER", "admin"),
                    password=os.getenv("DB_ROOT_PASSWORD", "aoi123!"),
                    host=os.getenv("DB_HOST", "127.0.0.1"),
                    port=os.getenv("DB_PORT", "5433")
                )
                self.conn.autocommit = True
                print("[DB] Connected to PostgreSQL successfully.")
                break
            except psycopg2.OperationalError as e:
                print(f"[DB] Database not ready, waiting... ({attempt+1}/{max_retries})")
                time.sleep(2)
        else:
            raise Exception("Failed to connect to PostgreSQL after multiple attempts. Is Docker running?")

        # Ensure basic tables exist if not already there, though the main system uses migrations
        self._ensure_dependencies()

    def _ensure_dependencies(self):
        try:
            with self.conn.cursor() as cur:
                # Basic tables
                cur.execute("INSERT INTO orders (order_number, target_quantity, status) VALUES (%s, 100, 'ACTIVE') ON CONFLICT DO NOTHING", ("AUTO_ORDER",))
                cur.execute("INSERT INTO board_numbers (board_number, grid_rows, grid_cols) VALUES (%s, 1, 1) ON CONFLICT DO NOTHING", ("AUTO_BOARD",))
                
                # Create run_steps table if not exists
                cur.execute("""
                CREATE TABLE IF NOT EXISTS run_steps (
                    step_id SERIAL PRIMARY KEY,
                    run_number VARCHAR(50) NOT NULL REFERENCES runs(run_number) ON DELETE CASCADE,
                    step_index INTEGER NOT NULL,
                    row_idx INTEGER,
                    col_idx INTEGER,
                    target_x_mm REAL,
                    target_y_mm REAL,
                    actual_x_mm REAL,
                    actual_y_mm REAL,
                    status VARCHAR(50) NOT NULL,
                    started_at TIMESTAMP,
                    position_reached_at TIMESTAMP,
                    capture_done_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_code INTEGER,
                    note TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_run_steps_run ON run_steps(run_number);
                """)
                
                # Create error_log table if not exists
                cur.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    error_id SERIAL PRIMARY KEY,
                    run_number VARCHAR(50) REFERENCES runs(run_number) ON DELETE SET NULL,
                    step_id INTEGER REFERENCES run_steps(step_id) ON DELETE SET NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_code INTEGER NOT NULL,
                    error_symbol VARCHAR(100),
                    error_category VARCHAR(100),
                    error_message TEXT,
                    source VARCHAR(50) NOT NULL,
                    recovery_action TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    details_json JSONB
                );
                CREATE INDEX IF NOT EXISTS idx_error_log_run ON error_log(run_number);
                """)
                
                # Create external_lookup_log table if not exists
                cur.execute("""
                CREATE TABLE IF NOT EXISTS external_lookup_log (
                    lookup_id SERIAL PRIMARY KEY,
                    run_number VARCHAR(50),
                    serial_number_query VARCHAR(50) NOT NULL,
                    query_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    api_endpoint TEXT,
                    http_status_code INTEGER,
                    has_data VARCHAR(10),
                    msg TEXT,
                    sn_returned VARCHAR(50),
                    semi_model VARCHAR(100),
                    pcb_length_mm REAL,
                    pcb_width_mm REAL,
                    accepted BOOLEAN DEFAULT FALSE,
                    raw_response_json JSONB,
                    error_message TEXT
                );
                """)
        except Exception as e:
            print(f"[DB] Error ensuring dependencies: {e}")

    def create_run(self, run_info: RunInfo) -> str:
        try:
            with self.conn.cursor() as cur:
                # pcb_aoi_db uses 'runs' table with: run_number, serial_number, board_number, order_number, machine_id, status, start_time
                cur.execute(
                    """
                    INSERT INTO runs (run_number, serial_number, board_number, order_number, machine_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_number) DO NOTHING
                    """,
                    (
                        run_info.run_code,
                        run_info.serial_number,
                        run_info.board_code or "AUTO_BOARD",
                        run_info.production_work_order or "AUTO_ORDER",
                        run_info.machine_id,
                        "RUNNING"
                    )
                )
        except Exception as e:
            print(f"[DB] Error creating run: {e}")
        return run_info.run_code

    def mark_run_status(self, run_code: str, status: str) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE runs SET status = %s WHERE run_number = %s", (status, run_code))
        except Exception as e:
            print(f"[DB] Error updating run status: {e}")

    def finish_run(self, run_code: str, status: str) -> None:
        self.mark_run_status(run_code, status)

    def create_step(self, run_code: str, step_info: StepInfo) -> int:
        # PostgreSQL schema doesn't use run_steps currently
        return step_info.step_index

    def update_step_status(self, step_id: int, status: str, step_index: int = None, **fields: Any) -> None:
        try:
            import json
            with self.conn.cursor() as cur:
                payload = json.dumps({"type": "step_status", "step_id": step_id, "step_index": step_index, "status": status})
                cur.execute(f"NOTIFY ui_update, '{payload}'")
        except Exception as e:
            print(f"[DB] Error sending notify for step status: {e}")

    def log_image(self, image_info: JsonDict) -> str:
        # In this architecture, folder_monitor.py will handle image insertions automatically
        # So we do nothing here, or just insert it if folder_monitor is disabled
        return str(uuid.uuid4())

    def log_event(self, event_info: JsonDict) -> None:
        try:
            import json
            with self.conn.cursor() as cur:
                payload = json.dumps({
                    "type": "event", 
                    "pc_state": event_info.get("pc_state"), 
                    "event_name": event_info.get("event_name"),
                    "mode": event_info.get("mode"),
                    "payload_json": event_info.get("payload_json")
                })
                cur.execute(f"NOTIFY ui_update, '{payload}'")
        except Exception as e:
            print(f"[DB] Error sending notify for event: {e}")

    def log_error(self, error_info: JsonDict) -> None:
        try:
            import json
            with self.conn.cursor() as cur:
                payload = json.dumps({
                    "type": "error", 
                    "error_code": error_info.get("error_code"), 
                    "error_message": error_info.get("error_message")
                })
                cur.execute(f"NOTIFY ui_update, '{payload}'")
        except Exception as e:
            print(f"[DB] Error sending notify for error: {e}")

    def log_external_lookup(self, lookup_info: JsonDict) -> None:
        pass

    def set_config(self, name: str, value: str) -> None:
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO system_configs (config_name, config_value) 
                    VALUES (%s, %s)
                    ON CONFLICT (config_name) DO UPDATE SET config_value = EXCLUDED.config_value
                """, (name, value))
        except Exception as e:
            print(f"[DB] Error setting config {name}: {e}")

    def close(self) -> None:
        self.conn.close()

def open_database() -> PostgresDatabase:
    return PostgresDatabase()
