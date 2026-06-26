import React, { useEffect, useState } from 'react';
import { inspectionService } from '../services/inspectionService';
import { InspectionStatus, RunDetail, CapturedImage } from '../types';
import { parseIllumination, serializeIllumination } from '../utils/formatters';

export const EditRun = ({ runId, onSave, onCancel }: { runId: string, onSave: () => void, onCancel: () => void }) => {
    const [detail, setDetail] = useState<RunDetail | null>(null);
    const [localImages, setLocalImages] = useState<CapturedImage[]>([]);
    const [selectedIds, setSelectedIds] = useState<string[]>([]);
    const [illuminationCodes, setIlluminationCodes] = useState<string[]>([]);
    const [boardCode, setBoardCode] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        // Fetch all images (large limit) so bulk edits capture the full run
        inspectionService.getRunDetail(runId, 500, 0).then(data => {
            setDetail(data);
            setLocalImages(data.images);
            setBoardCode(data.m_no || '');
        });
    }, [runId]);

    const handleStatusChange = (imageId: string, newStatus: InspectionStatus) => {
        setLocalImages(prev => prev.map(img =>
            img.image_id === imageId ? { ...img, condition: newStatus } : img
        ));
    };

    const toggleSelect = (id: string) => {
        setSelectedIds(prev =>
            prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
        );
    };

    const toggleSelectAll = () => {
        if (selectedIds.length === localImages.length && localImages.length > 0) {
            setSelectedIds([]);
        } else {
            setSelectedIds(localImages.map(img => img.image_id));
        }
    };

    const handleBulkPass = () => {
        setLocalImages(prev => prev.map(img =>
            selectedIds.includes(img.image_id) ? { ...img, condition: InspectionStatus.PASS } : img
        ));
        setSelectedIds([]);
    };

    const handleDeleteImage = async (id: string) => {
        if (confirm('Are you sure you want to delete this specific image?')) {
            try {
                // await inspectionService.deleteImage(id); // If available
                setLocalImages(prev => prev.filter(img => img.image_id !== id));
                setSelectedIds(prev => prev.filter(i => i !== id));
            } catch {
                alert('Failed to delete image. Please try again.');
            }
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            // Update run metadata only if something changed
            const runUpdates: Record<string, string> = {};
            if (boardCode !== (detail?.m_no || '')) runUpdates.m_no = boardCode;

            if (Object.keys(runUpdates).length > 0) {
                await inspectionService.updateRun(runId, runUpdates);
            }

            // Only push image updates where status actually changed
            const originalImages = detail?.images ?? [];
            const changedImages = localImages.filter(localImg => {
                const original = originalImages.find(o => o.image_id === localImg.image_id);
                return original && original.condition !== localImg.condition;
            });

            // await Promise.all(
            //     changedImages.map(img =>
            //         inspectionService.updateImage(img.image_id, { condition: img.condition })
            //     )
            // );

            onSave();
        } catch (error) {
            console.error(error);
            alert('Error saving changes. Please check your connection and try again.');
        } finally {
            setIsSaving(false);
        }
    };

    if (!detail) return <div className="p-10 font-medium">Loading Run Data...</div>;

    const StatusSelect = ({ current, onChange }: { current: InspectionStatus, onChange: (v: InspectionStatus) => void }) => {
        const colors: Record<InspectionStatus, string> = {
            [InspectionStatus.PASS]:    'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800',
            [InspectionStatus.FAIL]:    'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800',
            [InspectionStatus.PENDING]: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800',
        };

        return (
            <div className="relative">
                <select
                    value={current}
                    onChange={(e) => onChange(e.target.value as InspectionStatus)}
                    className={`w-full ${colors[current] ?? ''} text-sm font-bold rounded-lg py-2 pl-3 pr-8 cursor-pointer focus:ring-2 focus:ring-offset-1 appearance-none border transition-colors`}
                >
                    <option value={InspectionStatus.PENDING}>Pending</option>
                    <option value={InspectionStatus.PASS}>Pass</option>
                    <option value={InspectionStatus.FAIL}>Fail</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 opacity-50 text-current">
                    <span className="material-symbols-outlined text-lg">arrow_drop_down</span>
                </div>
            </div>
        );
    };

    return (
        <div className="flex-1 flex flex-col items-center py-5 px-4 md:px-8 overflow-y-auto bg-background-light dark:bg-background-dark">
            <div className="w-full max-w-[1200px] flex flex-col gap-6 pt-10 md:pt-0">
                <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-6">
                    <div className="flex flex-col gap-2">
                        <div className="flex gap-2 text-slate-500 text-xs font-medium">
                            <span>Runs</span> <span className="text-slate-300">/</span> <span>{runId}</span>
                        </div>
                        <h1 className="text-slate-900 dark:text-white text-2xl md:text-3xl lg:text-4xl font-black tracking-tight">Edit Run: {runId}</h1>
                        <p className="text-slate-500 dark:text-slate-400 text-sm md:text-base">Review anomalies and verify status before committing.</p>
                    </div>
                    <div className="flex gap-3 w-full lg:w-auto">
                        <button onClick={onCancel} className="flex-1 lg:flex-none rounded-xl h-12 px-6 bg-white border border-slate-200 hover:bg-slate-50 dark:bg-slate-800 dark:border-slate-700 dark:hover:bg-slate-700 text-slate-900 dark:text-white text-sm font-bold transition-all">
                            Cancel
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="flex-1 lg:flex-none rounded-xl h-12 px-8 bg-primary hover:bg-blue-600 disabled:bg-slate-300 text-white text-sm font-bold shadow-lg shadow-primary/20 transition-all transform active:scale-95"
                        >
                            {isSaving ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </div>

                <div className="flex flex-col xl:flex-row items-stretch xl:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                    <div className="flex flex-wrap items-center gap-3">
                        <div className="flex items-center gap-2 px-3 h-10 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Order</span>
                            <input
                                type="text"
                                value={boardCode}
                                onChange={(e) => setBoardCode(e.target.value)}
                                className="bg-transparent text-sm font-bold text-slate-700 dark:text-white focus:outline-none w-24"
                            />
                        </div>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                        <button
                            onClick={handleBulkPass}
                            disabled={selectedIds.length === 0}
                            className="flex items-center justify-center gap-2 rounded-xl h-10 px-4 bg-green-500 hover:bg-green-600 text-white text-sm font-bold transition-all disabled:opacity-30 disabled:grayscale shadow-sm"
                        >
                            <span className="material-symbols-outlined text-lg">check_circle</span>
                            Mark {selectedIds.length > 0 ? `(${selectedIds.length})` : ''} Selected as Pass
                        </button>
                    </div>
                </div>

                <div className="flex flex-col overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm mb-10">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[640px]">
                            <thead>
                                <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800">
                                    <th className="p-4 w-[60px] text-center">
                                        <input
                                            type="checkbox"
                                            checked={selectedIds.length === localImages.length && localImages.length > 0}
                                            onChange={toggleSelectAll}
                                            className="size-4 rounded text-primary border-slate-300 focus:ring-primary"
                                        />
                                    </th>
                                    <th className="p-4 w-[100px] text-[10px] font-black text-slate-400 uppercase tracking-widest">Image</th>
                                    <th className="p-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Metadata</th>
                                    <th className="p-4 w-[220px] text-[10px] font-black text-slate-400 uppercase tracking-widest">Status</th>
                                    <th className="p-4 w-[80px] text-center text-[10px] font-black text-slate-400 uppercase tracking-widest">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                {localImages.map((img) => (
                                    <tr key={img.image_id} className={`group transition-colors ${selectedIds.includes(img.image_id) ? 'bg-primary/5' : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'}`}>
                                        <td className="p-4 text-center">
                                            <input
                                                type="checkbox"
                                                checked={selectedIds.includes(img.image_id)}
                                                onChange={() => toggleSelect(img.image_id)}
                                                className="size-4 rounded text-primary border-slate-300 focus:ring-primary"
                                            />
                                        </td>
                                        <td className="p-4">
                                            <div className="h-14 w-14 rounded-xl bg-slate-100 dark:bg-slate-800 overflow-hidden border border-slate-200 dark:border-slate-700 relative shadow-sm">
                                                <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: `url(${img.local_path})` }}></div>
                                            </div>
                                        </td>
                                        <td className="p-4">
                                            <div className="flex flex-col overflow-hidden max-w-[200px]">
                                                <span className="text-slate-900 dark:text-white font-bold truncate">[{img.row_idx}, {img.col_idx}]</span>
                                                <span className="text-slate-500 text-xs mt-1 truncate">{img.side}</span>
                                                <span className="text-slate-400 text-[10px] font-mono mt-0.5 truncate">{img.image_id}</span>
                                            </div>
                                        </td>
                                        <td className="p-4">
                                            <StatusSelect
                                                current={img.condition}
                                                onChange={(newVal) => handleStatusChange(img.image_id, newVal)}
                                            />
                                        </td>
                                        <td className="p-4 text-center">
                                            <button
                                                onClick={() => handleDeleteImage(img.image_id)}
                                                className="size-9 flex items-center justify-center rounded-xl text-slate-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-900/40 transition-all mx-auto"
                                                title="Delete Image"
                                            >
                                                <span className="material-symbols-outlined text-[20px]">delete</span>
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};