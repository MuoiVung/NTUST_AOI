import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { SystemConfig } from '../types';

const CONFIG_LABELS: Record<string, { label: string, description: string, icon: string }> = {
    'longterm_sync_interval': {
        label: 'Data Retention Policy',
        description: 'How long to keep images locally before archiving to cloud/longterm storage.',
        icon: 'shutter_speed'
    },
    'sync_retry_interval': {
        label: 'Cloud Sync Retry',
        description: 'Interval between attempts to re-upload if the network is unstable.',
        icon: 'sync_problem'
    },
    'camera_fov_step_mm': {
        label: 'Camera FOV (Field of View)',
        description: 'The physical size in mm that the camera captures in one frame.',
        icon: 'camera'
    },
    'camera_margin_mm': {
        label: 'Camera Scan Margin',
        description: 'The margin from the edge of the PCB to start scanning (in mm).',
        icon: 'crop_free'
    }
};

const UNITS = [
    { label: 'Days',    value: 86400 },
    { label: 'Hours',   value: 3600 },
    { label: 'Minutes', value: 60 },
    { label: 'Seconds', value: 1 }
];

// Helper to find best display unit
const getBestUnit = (seconds: number) => {
    if (seconds === 0) return UNITS[2]; // Default to Minutes for zero
    for (const unit of UNITS) {
        if (seconds % unit.value === 0) return unit;
    }
    return UNITS[3];
};

export const Settings = () => {
    const [configs, setConfigs] = useState<SystemConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [editingKey, setEditingKey] = useState<string | null>(null);
    
    // Form state
    const [editValue, setEditValue] = useState<number>(0);
    const [editUnit, setEditUnit] = useState<number>(1);
    const [initializing, setInitializing] = useState(false);
    const [serviceStatus, setServiceStatus] = useState({ sync_service: 'loading', monitor_service: 'loading' });

    useEffect(() => {
        fetchConfigs();
        fetchServiceStatus();
        
        // Poll service status every 5 seconds
        const interval = setInterval(fetchServiceStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchServiceStatus = async () => {
        try {
            const status = await api.getServicesStatus();
            setServiceStatus(status);
        } catch (error) {
            console.error('Failed to fetch service status', error);
        }
    };

    const fetchConfigs = async () => {
        try {
            const data = await api.getConfigs();
            setConfigs(data);
        } catch (error) {
            console.error('Failed to fetch configs', error);
        } finally {
            setLoading(false);
        }
    };

    const handleInitialize = async () => {
        setInitializing(true);
        try {
            const response = await fetch('http://localhost:8000/configs/init', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to init');
            await fetchConfigs();
        } catch (error) {
            alert('Initialization failed.');
        } finally {
            setInitializing(false);
        }
    };

    const startEditing = (config: SystemConfig) => {
        if (config.unit === 'mm') {
            setEditValue(parseFloat(config.config_value) || 0);
            setEditUnit(-1); // Special flag for non-time
        } else {
            const totalSeconds = parseInt(config.config_value) || 0;
            const unit = getBestUnit(totalSeconds);
            setEditValue(totalSeconds / unit.value);
            setEditUnit(unit.value);
        }
        setEditingKey(config.config_name);
    };

    const handleSave = async (name: string) => {
        try {
            let finalValue = editValue.toString();
            if (editUnit !== -1) {
                finalValue = Math.round(editValue * editUnit).toString();
            }
            await api.updateConfig(name, finalValue);
            setEditingKey(null);
            fetchConfigs();
        } catch (error) {
            alert('Failed to save configuration');
        }
    };

    if (loading) return (
        <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
            <span className="material-symbols-outlined animate-spin text-4xl">sync</span>
            <p className="font-medium">Loading system configurations...</p>
        </div>
    );

    return (
        <div className="flex-1 flex flex-col p-4 md:p-8 bg-background-light dark:bg-background-dark overflow-y-auto">
            <div className="max-w-4xl w-full mx-auto flex flex-col gap-8">
                
                <div className="flex flex-col gap-2">
                    <h2 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white font-display">System Settings</h2>
                    <p className="text-slate-500 dark:text-slate-400">Configure time-based policies using automatic unit conversion.</p>
                </div>

                {configs.length === 0 ? (
                    <div className="p-12 rounded-3xl border-2 border-dashed border-slate-200 dark:border-slate-800 flex flex-col items-center justify-center text-center gap-6 bg-white/50 dark:bg-slate-900/50">
                        <div className="size-20 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                            <span className="material-symbols-outlined text-4xl">settings_suggest</span>
                        </div>
                        <div className="flex flex-col gap-2 max-w-md">
                            <h3 className="text-xl font-bold">No Configurations Found</h3>
                            <p className="text-slate-500 text-sm">Initialize the system keys to start configuring your AOI machine.</p>
                        </div>
                        <button 
                            onClick={handleInitialize}
                            disabled={initializing}
                            className="px-8 py-3 bg-primary text-white rounded-xl font-bold shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50"
                        >
                            {initializing ? 'Initializing...' : 'Initialize System Keys'}
                        </button>
                    </div>
                ) : (
                    <div className="grid gap-4">
                        {configs.map((config) => {
                            const isEditing = editingKey === config.config_name;
                            const isTimeBased = config.unit !== 'mm';
                            
                            let displayValue: string | number;
                            let displayUnitLabel: string;
                            let unitValue: number;

                            if (isTimeBased) {
                                const totalSeconds = parseInt(config.config_value) || 0;
                                const unit = getBestUnit(totalSeconds);
                                displayValue = totalSeconds / unit.value;
                                displayUnitLabel = unit.label;
                                unitValue = unit.value;
                            } else {
                                displayValue = parseFloat(config.config_value) || 0;
                                displayUnitLabel = config.unit || 'mm';
                                unitValue = -1;
                            }
                            
                                    const info = CONFIG_LABELS[config.config_name] || {
                                        label: config.config_name.replace(/_/g, ' '),
                                        description: 'General system setting',
                                        icon: 'settings'
                                    };

                                    const isSyncDisabled = config.config_name === 'longterm_sync_interval' && serviceStatus.sync_service !== 'running';

                                    return (
                                        <div key={config.config_key} className={`
                                            p-6 rounded-2xl border transition-all duration-300
                                            ${isEditing ? 'border-primary ring-4 ring-primary/5 bg-white dark:bg-slate-900 shadow-xl' : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/50 shadow-sm'}
                                            ${isSyncDisabled ? 'opacity-70 grayscale-[0.5]' : ''}
                                        `}>
                                    <div className="flex flex-col sm:flex-row gap-6 items-start sm:items-center">
                                        <div className={`size-12 rounded-xl flex items-center justify-center shrink-0 ${isEditing ? 'bg-primary text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'}`}>
                                            <span className="material-symbols-outlined">{info.icon}</span>
                                        </div>
                                        
                                        <div className="flex-1 flex flex-col gap-1 min-w-0">
                                            <h3 className="font-bold text-slate-900 dark:text-white text-lg">{info.label}</h3>
                                            <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed">{info.description}</p>
                                        </div>

                                            {isSyncDisabled ? (
                                                <div className="flex items-center gap-3 bg-amber-50 dark:bg-amber-900/20 px-4 py-2 rounded-xl border border-amber-100 dark:border-amber-800/50">
                                                    <span className="material-symbols-outlined text-amber-500 text-sm">warning</span>
                                                    <span className="text-[10px] font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider">Enable Sync Service in Launcher to edit</span>
                                                </div>
                                            ) : isEditing ? (
                                                <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
                                                    <div className="flex gap-1">
                                                        <input
                                                            type="number"
                                                            value={editValue}
                                                            onChange={(e) => setEditValue(parseFloat(e.target.value) || 0)}
                                                            className="w-24 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white font-bold outline-none"
                                                        />
                                                        {isTimeBased ? (
                                                            <select
                                                                value={editUnit}
                                                                onChange={(e) => setEditUnit(parseInt(e.target.value))}
                                                                className="px-2 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-bold outline-none"
                                                            >
                                                                {UNITS.map(u => <option key={u.label} value={u.value}>{u.label}</option>)}
                                                            </select>
                                                        ) : (
                                                            <div className="flex items-center px-3 text-slate-400 font-bold bg-slate-50 dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                                                                {displayUnitLabel}
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div className="flex gap-2">
                                                        <button 
                                                            onClick={() => handleSave(config.config_name)}
                                                            className="flex-1 sm:flex-none px-4 bg-primary text-white rounded-xl font-bold hover:bg-primary-dark"
                                                        >
                                                            Save
                                                        </button>
                                                        <button 
                                                            onClick={() => setEditingKey(null)}
                                                            className="px-3 bg-slate-100 dark:bg-slate-800 text-slate-500 rounded-xl hover:bg-slate-200"
                                                        >
                                                            <span className="material-symbols-outlined">close</span>
                                                        </button>
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="flex items-center gap-6">
                                                    <div className="flex flex-col items-end">
                                                        <span className="text-2xl font-black text-primary">{displayValue}</span>
                                                        <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{displayUnitLabel}</span>
                                                    </div>
                                                    <button 
                                                        onClick={() => startEditing(config)}
                                                        className="size-10 flex items-center justify-center rounded-xl border border-slate-200 dark:border-slate-700 hover:border-primary hover:text-primary transition-all group"
                                                    >
                                                        <span className="material-symbols-outlined text-[20px] group-hover:rotate-12 transition-transform">edit</span>
                                                    </button>
                                                </div>
                                            )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                <div className="p-6 rounded-2xl bg-indigo-50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-800/50 flex gap-4">
                    <span className="material-symbols-outlined text-indigo-500">database</span>
                    <div className="flex flex-col gap-1">
                        <p className="text-sm font-bold text-indigo-900 dark:text-indigo-200">Storage Optimization</p>
                        <p className="text-sm text-indigo-700/80 dark:text-indigo-400 leading-relaxed">
                            System values are stored in <b>Seconds</b> internally to ensure high-precision scheduling, while being displayed in your preferred unit.
                        </p>
                    </div>
                </div>

            </div>
        </div>
    );
};
