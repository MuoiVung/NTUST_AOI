import { DashboardMetrics, InspectionRun, RunDetail, Alert, InspectionStatus } from "../types";
import { MOCK_ALERTS, MOCK_METRICS } from "./mockData";

// ─── API Base URLs ────────────────────────────────────────────────────────────
const getApiBaseUrl = (): string =>
    import.meta.env.VITE_API_BASE_URL ||
    (import.meta.env.PROD ? '/api' : 'http://127.0.0.1:8000');

// ─── Typed API Response Shapes ────────────────────────────────────────────────
interface RunApiResponse {
    run_code: string;
    machine_id: string;
    board_code: string;
    date_str: string;
    side?: string;
    illumination?: string;
    status: string;        // 'PASS' | 'FAIL' | 'PENDING' | 'COMPLETED' in DB
    result?: string;       // mapped alias set by backend
    note?: string;
    start_time?: string;
    created_at?: string;
}

interface ImageApiResponse {
    image_id: string;
    run_code: string;
    file_path: string;
    file_name?: string;
    row_idx?: number;
    col_idx?: number;
    condition?: string;    // 'PASS' | 'FAIL' | 'PENDING' | 'UNKNOWN'
    capture_time?: string;
    file_size_bytes?: number;
    note?: string;
}

// ─── Status Mapping ───────────────────────────────────────────────────────────
const STATUS_MAP: Record<string, InspectionStatus> = {
    PASS:      InspectionStatus.PASS,
    FAIL:      InspectionStatus.FAIL,
    PENDING:   InspectionStatus.PENDING,
    COMPLETED: InspectionStatus.PASS,   // legacy DB status
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
        // TODO: replace with real endpoint /stats once backend supports it
        return new Promise(resolve => setTimeout(() => resolve(MOCK_METRICS), 300));
    },

    getRecentAlerts: async (): Promise<Alert[]> => {
        // TODO: replace with real endpoint once backend supports it
        return new Promise(resolve => setTimeout(() => resolve(MOCK_ALERTS), 300));
    },

    getInspectionRuns: async (filters?: {
        board_code?: string;
        result?: string;
        date_str?: string;
        illumination?: string;
    }): Promise<InspectionRun[]> => {
        const params = new URLSearchParams({ limit: '50' });
        if (filters?.board_code)  params.append('board_code',  filters.board_code);
        if (filters?.result)      params.append('result',      filters.result);
        if (filters?.date_str)    params.append('date_str',    filters.date_str);
        if (filters?.illumination) params.append('illumination', filters.illumination);

        const data = await apiFetch<RunApiResponse[]>(`/runs/?${params}`);

        return data.map(run => ({
            id:           run.run_code,
            timestamp:    run.created_at ?? run.start_time ?? '',
            pcbSerial:    run.board_code,
            result:       mapStatus(run.result ?? run.status),
            operator:     run.machine_id,
            defectType:   run.note,
            illumination: run.illumination,
        }));
    },

    getRunDetail: async (runId: string, limit = 24, offset = 0): Promise<RunDetail> => {
        const [runData, imagesData] = await Promise.all([
            apiFetch<RunApiResponse>(`/runs/${runId}`),
            apiFetch<ImageApiResponse[]>(
                `/images/?run_code=${runId}&limit=${limit}&offset=${offset}`
            ),
        ]);

        return {
            runId:       runData.run_code,
            batchId:     runData.board_code,
            line:        runData.machine_id,
            startTime:   runData.start_time ?? '',
            endTime:     runData.created_at ?? '',
            totalBoards: 1,
            defectRate:  0,
            operator:    runData.machine_id,
            illumination: runData.illumination,
            images: imagesData.map(img => ({
                id:       img.image_id,
                position: `R${img.row_idx ?? 0}-C${img.col_idx ?? 0}`,
                status:   mapStatus(img.condition),
                imageUrl: `${getApiBaseUrl()}/images/proxy/${img.image_id}`,
                label:    img.file_name,
                region:   `Zone ${img.row_idx ?? 0}-${img.col_idx ?? 0}`,
                note:     img.note,
            })),
        };
    },

    updateImage: async (imageId: string, update: { condition?: string; note?: string }): Promise<void> => {
        await apiFetch(`/images/${imageId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update),
        });
    },

    updateRun: async (
        runId: string,
        update: { illumination?: string; note?: string; board_code?: string }
    ): Promise<void> => {
        await apiFetch(`/runs/${runId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update),
        });
    },

    deleteImage: async (imageId: string): Promise<void> => {
        await apiFetch(`/images/${imageId}`, { method: 'DELETE' });
    },

    deleteRun: async (runId: string): Promise<void> => {
        await apiFetch(`/runs/${runId}`, { method: 'DELETE' });
    },
};