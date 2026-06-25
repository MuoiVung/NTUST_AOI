import { DashboardMetrics, InspectionRun, RunDetail, Alert, InspectionStatus, SystemConfig } from "../types";
import { MOCK_ALERTS, MOCK_METRICS } from "./mockData";

// ─── API Base URLs ────────────────────────────────────────────────────────────
const getApiBaseUrl = (): string =>
    import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.PROD ? '/api' : 'http://127.0.0.1:8000');

// ─── Typed API Response Shapes ────────────────────────────────────────────────
interface RunApiResponse {
    run_number: string;
    serial_number: string;
    board_number: string;
    order_number: string;
    machine_id: string;
    status: string;
    start_time?: string;
    created_at?: string;
}

interface ImageApiResponse {
    image_id: string;
    run_number: string;
    side: 'Top' | 'Bottom';
    local_path: string | null;
    longterm_path: string | null;
    is_uploaded_longterm: boolean;
    row_idx?: number;
    col_idx?: number;
    condition?: string;
    capture_time?: string;
    file_size_bytes?: number;
}

// ─── Status Mapping ───────────────────────────────────────────────────────────
const STATUS_MAP: Record<string, InspectionStatus> = {
    PASS:      InspectionStatus.PASS,
    FAIL:      InspectionStatus.FAIL,
    PENDING:   InspectionStatus.PENDING,
    COMPLETED: InspectionStatus.PASS,
    UNKNOWN:   InspectionStatus.PENDING,
};

function mapStatus(raw?: string): InspectionStatus {
    return STATUS_MAP[raw?.toUpperCase() ?? ''] ?? InspectionStatus.PENDING;
}

// ─── Generic Fetch Helper ─────────────────────────────────────────────────────
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${getApiBaseUrl()}${path}`, options);
    if (!res.ok) {
        const text = await res.text().catch(() => res.statusText);
        throw new Error(`API ${path} → ${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
}

// ─── Service ──────────────────────────────────────────────────────────────────
export const inspectionService = {

    getDashboardMetrics: async (): Promise<DashboardMetrics> => {
        return new Promise(resolve => setTimeout(() => resolve(MOCK_METRICS), 300));
    },

    getRecentAlerts: async (): Promise<Alert[]> => {
        return new Promise(resolve => setTimeout(() => resolve(MOCK_ALERTS), 300));
    },

    getInspectionRuns: async (filters?: {
        board_number?: string;
        order_number?: string;
        status?: string;
        serial_number?: string;
    }): Promise<InspectionRun[]> => {
        const params = new URLSearchParams({ limit: '50' });
        if (filters?.board_number)  params.append('board_number',  filters.board_number);
        if (filters?.order_number)  params.append('order_number',  filters.order_number);
        if (filters?.status)        params.append('status',        filters.status);
        if (filters?.serial_number) params.append('serial_number', filters.serial_number);

        const data = await apiFetch<RunApiResponse[]>(`/runs/?${params}`);

        return data.map(run => ({
            run_number:    run.run_number,
            serial_number: run.serial_number,
            board_number:  run.board_number,
            order_number:  run.order_number,
            timestamp:    run.created_at ?? run.start_time ?? '',
            status:       run.status,
            machine_id:   run.machine_id,
            start_time:   run.start_time ?? '',
            created_at:   run.created_at ?? '',
        }));
    },

    getRunDetail: async (runNumber: string, limit = 50, offset = 0): Promise<RunDetail> => {
        const [runData, imagesData] = await Promise.all([
            apiFetch<RunApiResponse>(`/runs/${runNumber}`),
            apiFetch<ImageApiResponse[]>(
                `/images/?run_number=${runNumber}&limit=${limit}&offset=${offset}`
            ),
        ]);

        return {
            runId:       runData.run_number,
            batchId:     runData.board_number,
            line:        runData.machine_id,
            startTime:   runData.start_time ?? '',
            endTime:     runData.created_at ?? '',
            totalBoards: 1,
            defectRate:  0,
            operator:    runData.machine_id,
            images: imagesData.map(img => ({
                id:       img.image_id,
                position: `${img.side} (R${img.row_idx ?? 0}-C${img.col_idx ?? 0})`,
                status:   mapStatus(img.condition),
                imageUrl: `${getApiBaseUrl()}/images/proxy/${img.image_id}`,
                region:   `${img.side} Zone ${img.row_idx ?? 0}-${img.col_idx ?? 0}`,
            })),
        };
    },

    // Configs
    getConfigs: async (): Promise<SystemConfig[]> => {
        return apiFetch<SystemConfig[]>('/configs/');
    },

    updateConfig: async (configName: string, configValue: string): Promise<void> => {
        await apiFetch(`/configs/${configName}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config_value: configValue }),
        });
    },

    updateImage: async (imageId: string, update: { condition?: string }): Promise<void> => {
        await apiFetch(`/images/${imageId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update),
        });
    },

    deleteImage: async (imageId: string): Promise<void> => {
        await apiFetch(`/images/${imageId}`, { method: 'DELETE' });
    },

    deleteRun: async (runNumber: string): Promise<void> => {
        await apiFetch(`/runs/${runNumber}`, { method: 'DELETE' });
    },
};