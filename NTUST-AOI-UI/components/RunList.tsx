import React, { useEffect, useState } from 'react';
import { inspectionService } from '../services/inspectionService';
import { InspectionRun, InspectionStatus } from '../types';

export const RunList = ({ onViewDetail, onCreate }: { onViewDetail: (id: string) => void, onCreate: () => void }) => {
    const [runs, setRuns] = useState<InspectionRun[]>([]);
    const [statusFilter, setStatusFilter] = useState<string>('All');
    const [boardFilter, setBoardFilter] = useState<string>('');
    const [dateFilter, setDateFilter] = useState<string>('');
    const [illuminationFilters, setIlluminationFilters] = useState<string[]>([]);

    const fetchRuns = () => {
        const filters: any = {};
        if (statusFilter !== 'All') filters.result = statusFilter;
        if (boardFilter) filters.board_code = boardFilter;
        if (dateFilter) filters.date_str = dateFilter.replace(/-/g, ''); // Format YYYYMMDD
        if (illuminationFilters.length > 0) filters.illumination = illuminationFilters.join(',');

        inspectionService.getInspectionRuns(filters).then(setRuns);
    };

    useEffect(() => {
        fetchRuns();
    }, [statusFilter, boardFilter, dateFilter, illuminationFilters]);

    const formatTimestamp = (ts: string) => {
        try {
            const date = new Date(ts);
            return date.toLocaleString('zh-TW', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        } catch (e) {
            return ts;
        }
    };

    const toggleIllumination = (code: string) => {
        setIlluminationFilters(prev =>
            prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
        );
    };

    const StatusBadge = ({ status }: { status: InspectionStatus }) => {
        const styles = status === InspectionStatus.PASS
            ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
            : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
        const dot = status === InspectionStatus.PASS ? "bg-green-500" : "bg-red-500";

        return (
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles}`}>
                <span className={`mr-1.5 size-1.5 rounded-full ${dot}`}></span>
                {status}
            </span>
        );
    };

    const IlluminationBadges = ({ illumination }: { illumination?: string }) => {
        if (!illumination) return <span className="text-slate-400">-</span>;

        // Split by comma or parse characters
        const activeChars = illumination.includes(',')
            ? illumination.split(',').map(s => s.trim().toUpperCase())
            : illumination.toUpperCase().split('').filter(s => s.trim());

        return (
            <div className="flex gap-1">
                {['L', 'R', 'T', 'B'].map(code => {
                    const isActive = activeChars.includes(code);
                    return (
                        <span
                            key={code}
                            title={isActive ? `Active: ${code}` : `Inactive: ${code}`}
                            className={`size-5 flex items-center justify-center rounded text-[10px] font-black border transition-colors ${isActive
                                ? 'bg-indigo-500 border-indigo-600 text-white shadow-sm'
                                : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-300 dark:text-slate-600'
                                }`}
                        >
                            {code}
                        </span>
                    );
                })}
            </div>
        );
    };

    return (
        <div className="flex-1 flex flex-col bg-background-light dark:bg-background-dark p-4 md:p-8 overflow-y-auto">
            <div className="max-w-[1400px] w-full mx-auto flex flex-col gap-6 pt-2 md:pt-0">

                 {/* Header Section */}
                <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-4">
                            <h1 className="text-2xl md:text-3xl lg:text-4xl font-display font-black leading-tight text-slate-900 dark:text-white">Dashboard</h1>
                            <button
                                onClick={fetchRuns}
                                title="Refresh data"
                                className="size-9 md:size-10 flex items-center justify-center rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-primary hover:bg-slate-50 dark:hover:bg-slate-700 transition-all hover:rotate-180 shadow-sm"
                            >
                                <span className="material-symbols-outlined text-[20px] md:text-[24px]">refresh</span>
                            </button>
                        </div>
                        <p className="text-slate-500 dark:text-slate-400 text-sm md:text-base">Manage and review PCB inspection data</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button onClick={onCreate} className="flex-1 md:flex-none h-10 items-center justify-center gap-2 rounded-lg bg-primary px-4 text-white hover:bg-blue-600 transition-colors font-medium">
                            <span className="material-symbols-outlined text-[20px]">add</span>
                            <span className="whitespace-nowrap">New Inspection</span>
                        </button>
                        <button className="flex-1 md:flex-none h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors font-medium text-slate-700 dark:text-slate-300">
                            <span className="material-symbols-outlined text-[20px]">download</span>
                            <span>Export</span>
                        </button>
                    </div>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-3 py-2 items-center">
                    <div className="flex flex-1 min-w-[140px] items-center gap-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 px-3 h-10">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Status</span>
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="bg-transparent text-sm font-medium text-slate-600 dark:text-slate-300 focus:outline-none cursor-pointer w-full"
                        >
                            <option value="All">All Status</option>
                            <option value="PASS">Pass Only</option>
                            <option value="FAIL">Fail Only</option>
                        </select>
                    </div>

                    <div className="flex flex-1 min-w-[200px] items-center gap-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 px-3 h-10">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Light</span>
                        <div className="flex gap-1">
                            {['L', 'R', 'T', 'B'].map(code => (
                                <button
                                    key={code}
                                    onClick={() => toggleIllumination(code)}
                                    className={`size-6 rounded flex items-center justify-center text-[10px] font-bold transition-all ${illuminationFilters.includes(code)
                                        ? 'bg-primary text-white shadow-sm ring-2 ring-primary/20'
                                        : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600'
                                        }`}
                                >
                                    {code}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="flex flex-1 min-w-[120px] items-center gap-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 px-3 h-10">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Model</span>
                        <input
                            type="text"
                            placeholder="e.g. M18"
                            value={boardFilter}
                            onChange={(e) => setBoardFilter(e.target.value)}
                            className="bg-transparent text-sm font-medium text-slate-600 dark:text-slate-300 focus:outline-none w-full"
                        />
                    </div>

                    <div className="flex flex-1 min-w-[160px] items-center gap-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 px-3 h-10">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Date</span>
                        <input
                            type="date"
                            value={dateFilter}
                            onChange={(e) => setDateFilter(e.target.value)}
                            className="bg-transparent text-sm font-medium text-slate-600 dark:text-slate-300 focus:outline-none w-full"
                        />
                    </div>

                    <button
                        onClick={() => { setStatusFilter('All'); setBoardFilter(''); setDateFilter(''); setIlluminationFilters([]); }}
                        className="text-xs font-bold text-primary hover:underline px-2"
                    >
                        Reset
                    </button>

                    <div className="w-full md:w-auto md:ml-auto flex items-center">
                        <div className="relative w-full">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-400 text-[20px]">search</span>
                            <input className="h-10 w-full md:w-64 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 pl-10 pr-4 text-sm focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none dark:text-white placeholder:text-slate-400 shadow-sm" placeholder="Search Serial Number..." type="text" />
                        </div>
                    </div>
                </div>

                {/* Table */}
                <div className="w-full overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm">
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[1000px]">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                                    {['Run ID', 'Timestamp', 'PCB Serial', 'Illumination', 'Result', 'Defect Type', 'Operator', 'Actions'].map(h => (
                                        <th key={h} className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-display last:text-right">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                {runs.map((run) => (
                                    <tr key={run.id} className="group hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                        <td className="px-6 py-4 text-sm font-medium text-slate-900 dark:text-white font-display">
                                            <button onClick={() => onViewDetail(run.id)} className="text-primary hover:underline">{run.id}</button>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap">{formatTimestamp(run.timestamp)}</td>
                                        <td className="px-6 py-4 text-sm font-mono text-slate-700 dark:text-slate-300">{run.pcbSerial}</td>
                                        <td className="px-6 py-4">
                                            <IlluminationBadges illumination={run.illumination} />
                                        </td>
                                        <td className="px-6 py-4"><StatusBadge status={run.result} /></td>
                                        <td className="px-6 py-4 text-sm text-slate-500 dark:text-slate-400">{run.defectType || '-'}</td>
                                        <td className="px-6 py-4 text-sm text-slate-700 dark:text-slate-300">
                                            <div className="flex items-center gap-2">
                                                <div className="size-6 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-[10px] font-bold text-indigo-700 dark:text-indigo-300">OP</div>
                                                <span>{run.operator}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <button onClick={() => onViewDetail(run.id)} className="flex items-center gap-1 rounded bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors">
                                                    <span className="material-symbols-outlined text-[16px]">visibility</span>
                                                    View
                                                </button>
                                                <button onClick={async (e) => {
                                                    e.stopPropagation();
                                                    if (confirm('Are you sure you want to delete this run?')) {
                                                        await inspectionService.deleteRun(run.id);
                                                        setRuns(prev => prev.filter(r => r.id !== run.id));
                                                    }
                                                }} className="flex items-center gap-1 rounded bg-red-50 dark:bg-red-900/20 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors">
                                                    <span className="material-symbols-outlined text-[16px]">delete</span>
                                                    Delete
                                                </button>
                                            </div>
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