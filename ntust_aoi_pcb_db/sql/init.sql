CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: runs
CREATE TABLE runs (
    run_code VARCHAR(50) PRIMARY KEY,
    machine_id VARCHAR(50) NOT NULL,
    board_code VARCHAR(20) NOT NULL,
    date_str CHAR(8) NOT NULL, -- YYYYMMDD
    side VARCHAR(10),
    illumination VARCHAR(20),
    status VARCHAR(20) DEFAULT 'COMPLETED',
    note TEXT,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for 'runs'
CREATE INDEX idx_runs_date ON runs(date_str);
CREATE INDEX idx_runs_board_date ON runs(board_code, date_str DESC);

-- Table: images
CREATE TABLE images (
    image_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_code VARCHAR(50) NOT NULL REFERENCES runs(run_code) ON DELETE CASCADE,
    file_path TEXT NOT NULL, -- Storing the absolute or relative path
    row_idx INTEGER,
    col_idx INTEGER,
    condition VARCHAR(10), -- PASS/FAIL
    capture_time TIMESTAMP,
    file_name VARCHAR(255),
    file_size_bytes BIGINT,
    checksum VARCHAR(64),
    
    -- Extra flexibility (Optional, matches Mongo's dynamic nature)
    -- extra_metadata JSONB 
    
    CONSTRAINT fk_run FOREIGN KEY (run_code) REFERENCES runs(run_code)
);

-- Indexes for 'images'
CREATE INDEX idx_images_run_code ON images(run_code);
CREATE INDEX idx_images_condition ON images(condition);
