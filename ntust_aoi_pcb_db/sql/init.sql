CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: orders
CREATE TABLE orders (
    order_number    VARCHAR(50) PRIMARY KEY,
    target_quantity INT NOT NULL DEFAULT 0,
    actual_quantity INT NOT NULL DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'ACTIVE',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 2: board_numbers
CREATE TABLE board_numbers (
    board_number    VARCHAR(30) PRIMARY KEY,
    grid_rows       SMALLINT NOT NULL,
    grid_cols       SMALLINT NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 3: runs
CREATE TABLE runs (
    run_number      VARCHAR(50) PRIMARY KEY,
    serial_number   VARCHAR(50) NOT NULL,
    board_number    VARCHAR(30) NOT NULL REFERENCES board_numbers(board_number),
    order_number    VARCHAR(50) NOT NULL REFERENCES orders(order_number),
    machine_id      VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'COMPLETED',
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
CREATE INDEX idx_runs_order  ON runs(order_number);
CREATE INDEX idx_images_run  ON images(run_number);
