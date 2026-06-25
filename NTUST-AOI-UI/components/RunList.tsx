import React, { useEffect, useState } from 'react';
import { inspectionService } from '../services/inspectionService';
import { InspectionRun } from '../types';
import { formatTimestamp } from '../utils/formatters';

export const RunList = ({ onViewDetail }: { onViewDetail: (id: string) => void, onCreate: () => void }) => {
    const [runs, setRuns] = useState<InspectionRun[]>([]);
    const [statusFilter, setStatusFilter] = useState<string>('All');
    const [boardFilter, setBoardFilter] = useState<string>('');
    const [orderFilter, setOrderFilter] = useState<string>('');
    const [serialFilter, setSerialFilter] = useState<string>('');
    const [loading, setLoading] = useState(false);

    const fetchRuns = async () => {
        setLoading(true);
        try {
            const filters: any = {};
            if (statusFilter !== 'All') filters.status = statusFilter;
            if (boardFilter) filters.board_number = boardFilter;
            if (orderFilter) filters.order_number = orderFilter;
            if (serialFilter) filters.serial_number = serialFilter;

            const data = await inspectionService.getInspectionRuns(filters);
            setRuns(data);
        } catch (error) {
            console.error('Failed to fetch runs', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRuns();
    }, [statusFilter, boardFilter, orderFilter]);

    const StatusBadge = ({ status }: { status: string }) => {
        const isPass = status === 'COMPLETED' || status === 'PASS';
        const styles = isPass
            ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
            : "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300";
        const dot = isPass ? "bg-green-500" : "bg-amber-500";

        return (
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${styles}`}>
                <span className={`mr-1.5 size-1.5 rounded-full ${dot}`}></span>
                {status}
            </span>
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
                                disabled={loading}
                                className={`size-9 md:size-10 flex items-center justify-center rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-primary hover:bg-slate-50 dark:hover:bg-slate-700 transition-all ${loading ? 'animate-spin' : 'hover:rotate-180'} shadow-sm`}
                            >
                                <span className="material-symbols-outlined text-[20px] md:text-[24px]">refresh</span>
                            </button>
                        </div>
                        <p className="text-slate-500 dark:text-slate-400 text-sm md:text-base">Manage and review PCB inspection data</p>
                    </div>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-3 py-2 items-center">
                    <div className="flex flex-1 min-w-[140px] items-center gap-3 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 px-3 h-10 shadow-sm">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Status</span>
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="bg-transparent text-sm font-medium text-slate-600 dark:text-slate-300 focus:outline-none cursor-pointer w-full"
                        >
                            <option value="All">All Status</option>
                            <option value="COMPLETED">Completed</option>
                            <option value="PENDING">Pending</option>
                        </select>
                    </div>

                    <div className="flex flex-1 min-w-[150px] items-center gap-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 px-3 h-10 shadow-sm">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Board ID</span>
                        <input
                            type="text"
                            placeholder="Search board..."
                            value={boardFilter}
                            onChange={(e) => setBoardFilter(e.target.value)}
                            className="bg-transparent text-sm font-medium text-slate-600 dark:text-slate-300 focus:outline-none w-full"
                        />
                    </div>

                    <div className="flex flex-1 min-w-[150px] items-center gap-2 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 px-3 h-10 shadow-sm">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Order</span>
                        <input
                            type="text"
                            placeholder="Search order..."
                            value={orderFilter}
                            onChange={(e) => setOrderFilter(e.target.value)}
                            className="bg-transparent text-sm font-medium text-slate-600 dark:text-slate-300 focus:outline-none w-full"
                        />
                    </div>

                    <div className="w-full md:w-auto md:ml-auto flex items-center">
                        <div className="relative w-full">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 material-symbols-outlined text-slate-400 text-[20px]">search</span>
                            <input 
                                className="h-10 w-full md:w-64 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 pl-10 pr-4 text-sm focus:border-primary focus:ring-1 focus:ring-primary focus:outline-none dark:text-white placeholder:text-slate-400 shadow-sm" 
                                placeholder="Search S/N..." 
                                type="text"
                                value={serialFilter}
                                onChange={(e) => setSerialFilter(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && fetchRuns()}
                            />
                        </div>
                    </div>
                </div>

                {/* Table */}
                <div className="w-full overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shadow-sm">
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[1000px]">
                            <thead>
                                <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                                    {['Run Number', 'Timestamp', 'Serial Number', 'Board ID', 'Order ID', 'Status', 'Machine', 'Actions'].map(h => (
                                        <th key={h} className="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-display last:text-right">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                                {runs.map((run) => (
                                    <tr key={run.run_number} className="group hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                        <td className="px-6 py-4 text-sm font-medium text-slate-900 dark:text-white font-display">
                                            <button onClick={() => onViewDetail(run.run_number)} className="text-primary hover:underline">{run.run_number}</button>
                                        </td>
                                        <td className="px-6 py-4 text-sm text-slate-500 dark:text-slate-400 whitespace-nowrap">{formatTimestamp(run.timestamp)}</td>
                                        <td className="px-6 py-4 text-sm font-mono text-slate-700 dark:text-slate-300">{run.serial_number}</td>
                                        <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-300">{run.board_number}</td>
                                        <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-300">{run.order_number}</td>
                                        <td className="px-6 py-4"><StatusBadge status={run.status} /></td>
                                        <td className="px-6 py-4 text-sm text-slate-700 dark:text-slate-300">
                                            <div className="flex items-center gap-2">
                                                <div className="size-6 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center text-[10px] font-bold text-indigo-700 dark:text-indigo-300">IPC</div>
                                                <span>{run.machine_id}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 flex justify-end gap-2">
                                            <button onClick={() => onViewDetail(run.run_number)} className="inline-flex items-center gap-1 rounded bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors">
                                                <span className="material-symbols-outlined text-[16px]">visibility</span>
                                                View Detail
                                            </button>
                                            <button 
                                                onClick={async () => {
                                                    if(window.confirm(`⚠️ Are you sure you want to PERMANENTLY delete run ${run.run_number} and ALL its associated images?`)) {
                                                        try {
                                                            await inspectionService.deleteRun(run.run_number);
                                                            fetchRuns();
                                                        } catch (error) {
                                                            console.error('Error deleting run', error);
                                                            alert('Failed to delete this run!');
                                                        }
                                                    }
                                                }}
                                                className="inline-flex items-center gap-1 rounded bg-red-500/10 px-2 py-1.5 text-xs font-medium text-red-500 hover:bg-red-500/20 transition-colors"
                                                title="Delete Run"
                                            >
                                                <span className="material-symbols-outlined text-[16px]">delete</span>
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