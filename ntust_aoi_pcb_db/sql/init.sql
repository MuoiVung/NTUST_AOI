CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: orders
CREATE TABLE orders (
    m_no    VARCHAR(50) PRIMARY KEY,
    target_quantity INT NOT NULL DEFAULT 0,
    actual_quantity INT NOT NULL DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'ACTIVE',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 2 (Removed board_numbers)

-- Table 3: runs
CREATE TABLE runs (
    run_number      VARCHAR(50) PRIMARY KEY,
    serial_number   VARCHAR(50) NOT NULL,
    semi_model      VARCHAR(100),
    m_no    VARCHAR(50) NOT NULL REFERENCES orders(m_no),
    machine_id      VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'COMPLETED',
    is_latest       BOOLEAN DEFAULT TRUE,
    start_time      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 4: images
CREATE TABLE images (
    image_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_number            VARCHAR(50) NOT NULL REFERENCES runs(run_number) ON DELETE CASCADE,
    side                  VARCHAR(10),
    local_path            TEXT,
    longterm_path         TEXT,
    is_uploaded_longterm  BOOLEAN DEFAULT FALSE,
    row_idx               INTEGER,
    col_idx               INTEGER,
    condition             VARCHAR(10), -- PASS / FAIL
    file_size_bytes       BIGINT,
    capture_time          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 5: system_configs
CREATE TABLE system_configs (
    config_key      SERIAL PRIMARY KEY,
    config_name     VARCHAR(100) UNIQUE NOT NULL,
    config_value    TEXT,
    unit            VARCHAR(20)
);

-- Indexes
CREATE INDEX idx_runs_serial ON runs(serial_number);
CREATE INDEX idx_runs_order  ON runs(m_no);
CREATE INDEX idx_images_run  ON images(run_number);

-- Table 6: run_steps
CREATE TABLE run_steps (
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
CREATE INDEX idx_run_steps_run ON run_steps(run_number);

-- Table 7: error_log
CREATE TABLE error_log (
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
CREATE INDEX idx_error_log_run ON error_log(run_number);

-- Table 8: external_lookup_log
CREATE TABLE external_lookup_log (
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

-- Trigger for auto-incrementing actual_quantity in orders table
CREATE OR REPLACE FUNCTION increment_order_quantity()
RETURNS TRIGGER AS $$
BEGIN
    -- Only increment when status changes to COMPLETED and it is the latest
    IF NEW.status = 'COMPLETED' AND NEW.is_latest = TRUE THEN
        IF OLD.status IS NULL OR OLD.status != 'COMPLETED' THEN
            UPDATE orders SET actual_quantity = actual_quantity + 1 WHERE m_no = NEW.m_no;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_increment_order_quantity ON runs;
CREATE TRIGGER trigger_increment_order_quantity
AFTER INSERT OR UPDATE ON runs
FOR EACH ROW EXECUTE FUNCTION increment_order_quantity();
