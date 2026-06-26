import { DashboardMetrics, InspectionRun, RunDetail, InspectionStatus, SystemConfig, Alert } from "../types";
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
    m_no: string;
    machine_id: string;
    status: string;
    start_time?: string;
    created_at?: string;
    is_latest?: boolean;
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
        limit?: number;
        offset?: number;
        board_number?: string;
        m_no?: string;
        status?: string;
        serial_number?: string;
    }): Promise<{ data: InspectionRun[]; total: number }> => {
        const params = new URLSearchParams({ limit: (filters?.limit ?? 50).toString(), offset: (filters?.offset ?? 0).toString() });
        if (filters?.board_number)  params.append('board_number',  filters.board_number);
        if (filters?.m_no)  params.append('m_no',  filters.m_no);
        if (filters?.status)        params.append('status',        filters.status);
        if (filters?.serial_number) params.append('serial_number', filters.serial_number);

        const response = await apiFetch<{ data: RunApiResponse[]; total: number }>(`/runs/?${params}`);

        const runs = response.data.map(run => ({
            run_number:    run.run_number,
            serial_number: run.serial_number,
            board_number:  run.board_number,
            m_no:          run.m_no,
            timestamp:     run.start_time || run.created_at || '',
            status:        run.status,
            machine_id:    run.machine_id,
            start_time:    run.start_time ?? '',
            created_at:    run.created_at ?? '',
            is_latest:     run.is_latest !== false,
        }));
        
        return { data: runs, total: response.total };
    },

    getRunDetail: async (runNumber: string, limit = 50, offset = 0): Promise<RunDetail> => {
        const [runData, imagesData] = await Promise.all([
            apiFetch<RunApiResponse>(`/runs/${runNumber}`),
            apiFetch<ImageApiResponse[]>(
                `/images/?run_number=${runNumber}&limit=${limit}&offset=${offset}`
            ),
        ]);

        return {
            run_number:    runData.run_number,
            serial_number: runData.serial_number,
            m_no:  runData.m_no,
            machine_id:    runData.machine_id,
            status:        runData.status,
            start_time:    runData.start_time ?? '',
            created_at:    runData.created_at ?? '',
            is_latest:     runData.is_latest !== false,
            images: imagesData.map(img => ({
                image_id:             img.image_id,
                run_number:           img.run_number,
                side:                 img.side,
                local_path:           img.local_path ? `${getApiBaseUrl()}/images/proxy/${img.image_id}` : null,
                longterm_path:        img.longterm_path,
                is_uploaded_longterm: img.is_uploaded_longterm,
                row_idx:              img.row_idx ?? 0,
                col_idx:              img.col_idx ?? 0,
                condition:            mapStatus(img.condition),
                file_size_bytes:      img.file_size_bytes ?? 0,
                capture_time:         img.capture_time ?? ''
            })),
        };
    },

    // Configs
    getConfigs: async (): Promise<SystemConfig[]> => {
        return apiFetch<SystemConfig[]>('/configs/');
    },

    updateSystemConfig: async (configs: Partial<SystemConfig>): Promise<void> => {
        // Implementation for updating system config via API
        throw new Error('updateSystemConfig not fully implemented');
    },

    updateRun: async (runNumber: string, data: any): Promise<void> => {
        const response = await fetch(`${getApiBaseUrl()}/runs/${runNumber}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Failed to update run');
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