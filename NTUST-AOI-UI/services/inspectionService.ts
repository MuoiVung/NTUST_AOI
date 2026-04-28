import { DashboardMetrics, InspectionRun, RunDetail, Alert, InspectionStatus } from "../types";
import { MOCK_ALERTS, MOCK_METRICS } from "./mockData";

const getApiBaseUrl = () => {
    return import.meta.env.VITE_API_BASE_URL || (import.meta.env.PROD ? '/api' : 'http://127.0.0.1:8000');
};

const getImgBaseUrl = () => {
    return import.meta.env.VITE_IMG_BASE_URL || 'http://127.0.0.1:8000/images';
};

export const inspectionService = {
    getDashboardMetrics: async (): Promise<DashboardMetrics> => {
        // For now, continue to mock metrics as backend doesn't have an aggregation endpoint yet
        // In future: return fetch(`${API_BASE_URL}/stats`).then(res => res.json());
        return new Promise((resolve) => {
            setTimeout(() => resolve(MOCK_METRICS), 300);
        });
    },

    getRecentAlerts: async (): Promise<Alert[]> => {
        // Mock alerts for now
        return new Promise((resolve) => {
            setTimeout(() => resolve(MOCK_ALERTS), 300);
        });
    },

    getInspectionRuns: async (filters?: { board_code?: string, result?: string, date_str?: string, illumination?: string }): Promise<InspectionRun[]> => {
        try {
            const params = new URLSearchParams({ limit: '50' });
            if (filters?.board_code) params.append('board_code', filters.board_code);
            if (filters?.result) params.append('result', filters.result);
            if (filters?.date_str) params.append('date_str', filters.date_str);
            if (filters?.illumination) params.append('illumination', filters.illumination);

            const response = await fetch(`${getApiBaseUrl()}/runs/?${params.toString()}`);
            if (!response.ok) throw new Error('Failed to fetch runs');
            const data = await response.json();

            // Transform Backend API format to Frontend type
            return data.map((run: any) => ({
                id: run.run_code,
                timestamp: run.created_at || run.start_time,
                pcbSerial: run.board_code,
                result: (run.result === 'FAIL' ? InspectionStatus.FAIL : InspectionStatus.PASS) as InspectionStatus,
                operator: run.machine_id,
                defectType: run.note,
                illumination: run.illumination
            }));
        } catch (error) {
            console.error(error);
            return [];
        }
    },

    getRunDetail: async (runId: string, limit: number = 24, offset: number = 0): Promise<RunDetail> => {
        try {
            // Parallel fetch: Run Details + Paged Images
            const [runRes, imgsRes] = await Promise.all([
                fetch(`${getApiBaseUrl()}/runs/${runId}`),
                fetch(`${getApiBaseUrl()}/images/?run_code=${runId}&limit=${limit}&offset=${offset}`)
            ]);

            if (!runRes.ok) throw new Error('Failed to fetch run info');
            const runData = await runRes.json();
            const imagesData = await imgsRes.json();

            // Transform backend data to RunDetail type
            return {
                runId: runData.run_code,
                batchId: runData.board_code, // Using board_code as batch for now
                line: runData.machine_id,
                startTime: runData.start_time,
                endTime: runData.created_at,
                totalBoards: 1, // Placeholder
                defectRate: 0,
                operator: 'Admin',
                illumination: runData.illumination,
                images: imagesData.map((img: any) => ({
                    id: img.image_id,
                    position: `R${img.row_idx}-C${img.col_idx}`,
                    status: (img.condition === 'UNKNOWN' ? InspectionStatus.PASS : img.condition) as InspectionStatus,
                    imageUrl: `${getApiBaseUrl()}/images/proxy/${img.image_id}`,
                    label: img.file_name,
                    region: `Zone ${img.row_idx}-${img.col_idx}`,
                    note: img.note
                }))
            };

        } catch (error) {
            console.error(error);
            throw error;
        }
    },

    updateImage: async (imageId: string, update: { condition?: string, note?: string }): Promise<void> => {
        await fetch(`${getApiBaseUrl()}/images/${imageId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update)
        });
    },

    updateRun: async (runId: string, update: { illumination?: string, note?: string, board_code?: string }): Promise<void> => {
        await fetch(`${getApiBaseUrl()}/runs/${runId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update)
        });
    },

    deleteImage: async (imageId: string): Promise<void> => {
        await fetch(`${getApiBaseUrl()}/images/${imageId}`, { method: 'DELETE' });
    },

    deleteRun: async (runId: string): Promise<void> => {
        await fetch(`${getApiBaseUrl()}/runs/${runId}`, { method: 'DELETE' });
    }
};