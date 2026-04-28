/**
 * Shared utility functions for formatting and parsing.
 */

/**
 * Parse an illumination string (e.g. "LRTB", "L, R, T") into an array of
 * active light-source codes.
 */
export function parseIllumination(value?: string | null): string[] {
    if (!value) return [];
    if (value.includes(',')) {
        return value.split(',').map(s => s.trim().toUpperCase()).filter(Boolean);
    }
    return value.toUpperCase().split('').filter(s => s.trim().length > 0);
}

/**
 * Converts an array of codes back to a comma-separated string.
 */
export function serializeIllumination(codes: string[]): string {
    return codes.join(', ');
}

/**
 * Format an ISO timestamp string for display using zh-TW locale
 * (YYYY/MM/DD HH:mm:ss).
 */
export function formatTimestamp(ts?: string | null): string {
    if (!ts) return '—';
    try {
        const date = new Date(ts);
        if (isNaN(date.getTime())) return ts;
        return date.toLocaleString('zh-TW', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        });
    } catch {
        return ts;
    }
}
