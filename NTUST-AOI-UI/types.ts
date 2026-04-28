export enum InspectionStatus {
    PASS = 'PASS',
    FAIL = 'FAIL',
    PENDING = 'PENDING'
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

export interface Alert {
    id: string;
    code: string;
    type: string;
    time: string;
    lane: string;
    severity: 'critical' | 'warning' | 'info';
}

export interface InspectionRun {
    id: string;
    timestamp: string;
    pcbSerial: string;
    result: InspectionStatus;
    defectType?: string;
    operator: string;
    illumination?: string;
    thumbnailUrl?: string;
}

export interface CapturedImage {
    id: string;
    imageUrl: string;
    position: string; // e.g., "A-01"
    status: InspectionStatus;
    label?: string; // e.g., "Missing Component"
    region: string; // e.g., "Region B-4"
    note?: string;
}

export interface RunDetail {
    runId: string;
    batchId: string;
    line: string;
    startTime: string;
    endTime: string;
    totalBoards: number;
    defectRate: number;
    operator: string;
    illumination?: string;
    images: CapturedImage[];
}