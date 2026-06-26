export enum InspectionStatus {
    PASS = 'PASS',
    FAIL = 'FAIL',
    PENDING = 'PENDING'
}

export interface Alert {
    id: string;
    message: string;
    type: 'warning' | 'error' | 'info';
    timestamp: string;
}

export interface DashboardMetrics {
    totalScanned: number;
    totalScannedChange: number;
    passRate: number;
    passRateChange: number;
    defectCount: number;
    defectCountChange: number;
    throughputData: { time: string; value: number }[];
}

export interface Order {
    m_no: string;
    target_quantity: number;
    actual_quantity: number;
    status: string;
    created_at: string;
}

export interface BoardNumber {
    board_number: string;
    grid_rows: number;
    grid_cols: number;
    created_at: string;
}

export interface InspectionRun {
    run_number: string;
    serial_number: string;
    board_number?: string;
    m_no: string;
    status: string;
    machine_id: string;
    start_time: string;
    created_at: string;
    timestamp: string;
    is_latest: boolean;
}

export interface RunDetail {
    run_number: string;
    serial_number: string;
    m_no: string;
    machine_id: string;
    status: string;
    start_time: string;
    created_at: string;
    is_latest: boolean;
    images: CapturedImage[];
}

export interface CapturedImage {
    id?: string;
    image_id: string;
    run_number: string;
    side: 'Top' | 'Bottom';
    local_path: string | null;
    longterm_path: string | null;
    is_uploaded_longterm: boolean;
    row_idx: number;
    col_idx: number;
    condition: InspectionStatus;
    file_size_bytes: number;
    capture_time: string;
}

export interface SystemConfig {
    config_key: number;
    config_name: string;
    config_value: string;
    unit: string;
}