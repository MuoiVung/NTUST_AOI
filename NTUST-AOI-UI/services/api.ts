import { InspectionRun, CapturedImage, SystemConfig, Order, BoardNumber } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000';

export const api = {
    // Runs
    getRuns: async (limit = 50): Promise<InspectionRun[]> => {
        const response = await fetch(`${API_BASE_URL}/runs/?limit=${limit}`);
        if (!response.ok) throw new Error('Failed to fetch runs');
        return response.json();
    },
    
    getRunDetail: async (runNumber: string): Promise<InspectionRun> => {
        const response = await fetch(`${API_BASE_URL}/runs/${runNumber}`);
        if (!response.ok) throw new Error('Failed to fetch run details');
        return response.json();
    },

    // Images
    getImagesByRun: async (runNumber: string): Promise<CapturedImage[]> => {
        const response = await fetch(`${API_BASE_URL}/images/?run_number=${runNumber}`);
        if (!response.ok) throw new Error('Failed to fetch images');
        return response.json();
    },

    updateImageCondition: async (imageId: string, condition: string): Promise<void> => {
        const response = await fetch(`${API_BASE_URL}/images/${imageId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ condition })
        });
        if (!response.ok) throw new Error('Failed to update image condition');
    },

    // Configs (Add backend endpoints if needed, for now we can use a generic settings fetch if implemented)
    getConfigs: async (): Promise<SystemConfig[]> => {
        // Note: We need to implement this endpoint in main.py
        const response = await fetch(`${API_BASE_URL}/configs/`);
        if (!response.ok) return [];
        return response.json();
    },

    updateConfig: async (configName: string, configValue: string): Promise<void> => {
        const response = await fetch(`${API_BASE_URL}/configs/${configName}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config_value: configValue })
        });
        if (!response.ok) throw new Error('Failed to update config');
    },

    getServicesStatus: async (): Promise<{ sync_service: string; monitor_service: string }> => {
        const response = await fetch(`${API_BASE_URL}/services/status`);
        if (!response.ok) return { sync_service: 'unknown', monitor_service: 'unknown' };
        return response.json();
    },

    // Helper to get image URL
    getImageUrl: (image: CapturedImage): string => {
        // Always use the proxy endpoint. The backend handles local vs cloud detection.
        return `${API_BASE_URL}/images/proxy/${image.image_id}`;
    }
};
