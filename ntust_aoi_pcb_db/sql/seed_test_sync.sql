-- SEED DATA FOR SYNC TESTING
-- Scenario: Create an old run that should be moved to long-term storage

-- 1. Create a Test Order
INSERT INTO orders (m_no, target_quantity, actual_quantity, status, created_at)
VALUES ('TEST-ORDER-001', 100, 1, 'ACTIVE', CURRENT_TIMESTAMP - INTERVAL '40 days');

-- 2. Create a Test Board Recipe
INSERT INTO board_numbers (board_number, grid_rows, grid_cols, created_at)
VALUES ('TEST-BOARD-5X5', 5, 5, CURRENT_TIMESTAMP - INTERVAL '40 days');

-- 3. Create a Test Run (Set to 40 days ago)
INSERT INTO runs (run_number, serial_number, board_number, m_no, machine_id, status, start_time, created_at)
VALUES (
    'RUN_SYNC_TEST_001', 
    'SN-TEST-999', 
    'TEST-BOARD-5X5', 
    'TEST-ORDER-001', 
    'AOI-MACHINE-01', 
    'COMPLETED', 
    CURRENT_TIMESTAMP - INTERVAL '40 days 1 hour',
    CURRENT_TIMESTAMP - INTERVAL '40 days'
);

-- 4. Create Test Images (Not yet uploaded to long-term)
INSERT INTO images (image_id, run_number, side, local_path, longterm_path, is_uploaded_longterm, row_idx, col_idx, condition, file_size_bytes, capture_time)
VALUES 
(
    '550e8400-e29b-41d4-a716-446655440000', 
    'RUN_SYNC_TEST_001', 
    'Top', 
    'TEST-ORDER-001/SN-TEST-999/Top/1_1.jpg', 
    NULL, 
    FALSE, 
    1, 1, 'PASS', 102400, 
    CURRENT_TIMESTAMP - INTERVAL '40 days'
),
(
    '550e8400-e29b-41d4-a716-446655440001', 
    'RUN_SYNC_TEST_001', 
    'Top', 
    'TEST-ORDER-001/SN-TEST-999/Top/1_2.jpg', 
    NULL, 
    FALSE, 
    1, 2, 'FAIL', 105600, 
    CURRENT_TIMESTAMP - INTERVAL '40 days'
),
(
    '550e8400-e29b-41d4-a716-446655440002', 
    'RUN_SYNC_TEST_001', 
    'Bottom', 
    'TEST-ORDER-001/SN-TEST-999/Bottom/1_1.jpg', 
    NULL, 
    FALSE, 
    1, 1, 'PASS', 98400, 
    CURRENT_TIMESTAMP - INTERVAL '40 days'
);
