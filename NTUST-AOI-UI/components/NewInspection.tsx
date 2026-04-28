import React, { useState } from 'react';
import { inspectionService } from '../services/inspectionService';

interface NewInspectionProps {
    onSave: () => void;
    onCancel: () => void;
}

export const NewInspection = ({ onSave, onCancel }: NewInspectionProps) => {
    const [formData, setFormData] = useState({
        run_code: `RUN_${Math.floor(Date.now() / 1000)}`,
        board_code: '',
        machine_id: 'MAC-01',
        side: 'TOP',
        illumination: '',
        note: ''
    });
    const [isSaving, setIsSaving] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            // In a real app, we'd call an API to create a run. 
            // The backend has a POST /runs/ endpoint.
            const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');
            const runData = {
                ...formData,
                date_str: dateStr,
                status: 'COMPLETED'
            };

            const response = await fetch('/api/runs/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(runData)
            });

            if (!response.ok) throw new Error('Failed to create run');

            onSave();
        } catch (error) {
            console.error(error);
            alert('Failed to create new inspection run. Please ensure backend is running.');
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="flex-1 flex flex-col bg-background-light dark:bg-background-dark p-8 overflow-y-auto">
            <div className="max-w-[800px] w-full mx-auto flex flex-col gap-8">

                {/* Header */}
                <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2 mb-2">
                        <button onClick={onCancel} className="text-slate-500 hover:text-primary text-sm font-medium flex items-center gap-1">
                            <span className="material-symbols-outlined text-sm">arrow_back</span>
                            Back to List
                        </button>
                    </div>
                    <h1 className="text-3xl font-display font-black text-slate-900 dark:text-white">Start New Inspection</h1>
                    <p className="text-slate-500 dark:text-slate-400">Initialize a new PCB inspection sequence</p>
                </div>

                {/* Form Card */}
                <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                    <div className="p-8 space-y-6">

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Run ID (Auto-generated)</label>
                                <input
                                    className="w-full h-11 px-4 bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-slate-400 font-mono cursor-not-allowed"
                                    value={formData.run_code}
                                    readOnly
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">PCB Board Model</label>
                                <input
                                    required
                                    placeholder="e.g. M18-V3-A"
                                    className="w-full h-11 px-4 bg-slate-50 dark:bg-slate-800 border border-transparent focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none rounded-xl text-slate-900 dark:text-white transition-all"
                                    value={formData.board_code}
                                    onChange={e => setFormData({ ...formData, board_code: e.target.value })}
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Machine ID</label>
                                <select
                                    className="w-full h-11 px-4 bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-slate-900 dark:text-white focus:ring-1 focus:ring-primary focus:outline-none"
                                    value={formData.machine_id}
                                    onChange={e => setFormData({ ...formData, machine_id: e.target.value })}
                                >
                                    <option value="MAC-01">MAC-01 (Main Line)</option>
                                    <option value="MAC-02">MAC-02 (Secondary)</option>
                                    <option value="AOI-PRO-1">AOI Pro - 1</option>
                                </select>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Board Side</label>
                                <div className="flex gap-2">
                                    {['TOP', 'BOTTOM'].map(side => (
                                        <button
                                            key={side}
                                            type="button"
                                            onClick={() => setFormData({ ...formData, side })}
                                            className={`flex-1 h-11 rounded-xl text-sm font-bold transition-all ${formData.side === side
                                                ? 'bg-primary text-white shadow-lg shadow-primary/20'
                                                : 'bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
                                                }`}
                                        >
                                            {side}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Illumination (Light Direction)</label>
                                <div className="flex flex-col gap-2">
                                    <div className="flex flex-wrap gap-2">
                                        {[
                                            { id: 'L', label: 'Left (L)' },
                                            { id: 'R', label: 'Right (R)' },
                                            { id: 'T', label: 'Top (T)' },
                                            { id: 'B', label: 'Back (B)' }
                                        ].map(light => {
                                            const isActive = formData.illumination.split(',').map(s => s.trim()).includes(light.id);
                                            return (
                                                <button
                                                    key={light.id}
                                                    type="button"
                                                    onClick={() => {
                                                        const parts = formData.illumination.split(',').map(s => s.trim()).filter(Boolean);
                                                        const next = parts.includes(light.id)
                                                            ? parts.filter(p => p !== light.id)
                                                            : [...parts, light.id];
                                                        setFormData({ ...formData, illumination: next.join(', ') });
                                                    }}
                                                    className={`px-4 h-9 rounded-lg text-xs font-bold transition-all ${isActive
                                                        ? 'bg-primary text-white shadow-md shadow-primary/20'
                                                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200'
                                                        }`}
                                                >
                                                    {light.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <input
                                        placeholder="Other (Manual Input)"
                                        className="w-full h-11 px-4 bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-slate-900 dark:text-white focus:ring-1 focus:ring-primary focus:outline-none text-sm"
                                        value={formData.illumination}
                                        onChange={e => setFormData({ ...formData, illumination: e.target.value.toUpperCase() })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-bold uppercase tracking-widest text-slate-500">Inspection Notes</label>
                                <textarea
                                    placeholder="Any context about this inspection run..."
                                    className="w-full h-32 p-4 bg-slate-50 dark:bg-slate-800 border border-transparent focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none rounded-xl text-slate-900 dark:text-white transition-all resize-none"
                                    value={formData.note}
                                    onChange={e => setFormData({ ...formData, note: e.target.value })}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="p-8 bg-slate-50 dark:bg-slate-800/50 flex flex-col-reverse md:flex-row justify-end gap-3">
                        <button
                            type="button"
                            onClick={onCancel}
                            className="h-12 px-8 rounded-xl text-sm font-bold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={isSaving}
                            className="h-12 px-10 rounded-xl text-sm font-bold bg-primary hover:bg-blue-600 text-white shadow-lg shadow-primary/25 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                        >
                            <span className="material-symbols-outlined text-[20px]">{isSaving ? 'sync' : 'play_arrow'}</span>
                            {isSaving ? 'Initializing...' : 'Start Inspection'}
                        </button>
                    </div>
                </form>

                {/* Footer Info */}
                <div className="flex items-start gap-4 p-6 rounded-2xl bg-blue-500/5 border border-blue-500/10">
                    <span className="material-symbols-outlined text-blue-500 mt-1">info</span>
                    <div>
                        <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-1">Database Connectivity</h4>
                        <p className="text-xs text-slate-500 leading-relaxed">Starting a new inspection will create a new entry in the PostgreSQL database. Image capture simulations will begin automatically based on the selected Board Model.</p>
                    </div>
                </div>

            </div>
        </div>
    );
};
