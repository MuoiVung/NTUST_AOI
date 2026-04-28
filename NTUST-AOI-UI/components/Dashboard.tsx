import React, { useEffect, useState } from 'react';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { inspectionService } from '../services/inspectionService';
import { Alert, DashboardMetrics } from '../types';

const MetricCard = ({
    title,
    value,
    change,
    label,
    icon,
    trend,
    colorClass,
    bgClass
}: {
    title: string;
    value: string;
    change: number;
    label: string;
    icon: string;
    trend: 'up' | 'down';
    colorClass: string;
    bgClass: string;
}) => {
    const isPositive = change > 0;
    const isGood = (trend === 'up' && isPositive) || (trend === 'down' && !isPositive);
    const trendColor = isGood ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50';
    const trendIcon = change > 0 ? 'trending_up' : 'trending_down';

    return (
        <div className="flex flex-col gap-2 rounded-xl p-6 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm">
            <div className="flex items-center justify-between">
                <p className="text-slate-500 dark:text-slate-400 text-sm font-medium leading-normal uppercase tracking-wider">{title}</p>
                <span className={`material-symbols-outlined ${colorClass} ${bgClass} p-1 rounded-md`}>{icon}</span>
            </div>
            <div className="flex items-end gap-3 mt-2">
                <p className="text-slate-900 dark:text-white tracking-tight text-3xl font-bold leading-tight">{value}</p>
                <span className={`flex items-center px-1.5 py-0.5 rounded text-xs font-medium mb-1 ${trendColor}`}>
                    <span className="material-symbols-outlined text-[16px] mr-0.5">{trendIcon}</span>
                    {Math.abs(change)}%
                </span>
            </div>
            <p className="text-slate-500 dark:text-slate-500 text-xs mt-1">{label}</p>
        </div>
    );
};

const AlertItem: React.FC<{ alert: Alert }> = ({ alert }) => {
    let icon = 'error';
    let colorClass = 'text-red-600 bg-red-100';

    if (alert.severity === 'warning') {
        icon = 'warning';
        colorClass = 'text-orange-600 bg-orange-100';
    } else if (alert.severity === 'info') {
        icon = 'info';
        colorClass = 'text-blue-600 bg-blue-100';
    }

    return (
        <div className="flex items-center gap-4 px-4 py-4 border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer group last:border-0">
            <div className={`shrink-0 flex items-center justify-center rounded-lg ${colorClass} size-10`}>
                <span className="material-symbols-outlined">{icon}</span>
            </div>
            <div className="flex flex-col justify-center flex-1 min-w-0">
                <p className="text-slate-900 dark:text-white text-sm font-semibold leading-normal truncate group-hover:text-primary transition-colors">
                    Defect {alert.code} - {alert.type}
                </p>
                <p className="text-slate-500 dark:text-slate-400 text-xs font-normal leading-normal truncate">
                    {alert.time} - {alert.lane}
                </p>
            </div>
            <div className="shrink-0">
                <span className="material-symbols-outlined text-slate-400 dark:text-slate-500 text-lg">chevron_right</span>
            </div>
        </div>
    );
};


export const Dashboard = () => {
    const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
    const [alerts, setAlerts] = useState<Alert[]>([]);

    useEffect(() => {
        inspectionService.getDashboardMetrics().then(setMetrics);
        inspectionService.getRecentAlerts().then(setAlerts);
    }, []);

    if (!metrics) return <div className="p-10 text-center text-slate-500">Loading Dashboard...</div>;

    return (
        <div className="flex-1 flex flex-col h-full overflow-y-auto">
            <header className="px-6 py-5 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-10 flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Overview</h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">Real-time inspection metrics for Line 1</p>
                </div>
                <div className="flex items-center gap-4">
                    <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors text-slate-700 dark:text-slate-300">
                        <span className="material-symbols-outlined text-sm">calendar_today</span>
                        Last 24 Hours
                    </button>
                    <button className="flex items-center justify-center size-10 rounded-full bg-primary text-white shadow-lg hover:bg-blue-700 transition-colors">
                        <span className="material-symbols-outlined">notifications</span>                    </button>
                </div>
            </header>

            <div className="p-6 flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <MetricCard
                        title="Total Scanned"
                        value={metrics.totalScanned.toLocaleString()}
                        change={metrics.totalScannedChange}
                        label="vs. previous 24 hours"
                        icon="center_focus_weak"
                        trend="up"
                        colorClass="text-primary"
                        bgClass="bg-blue-50"
                    />
                    <MetricCard
                        title="Pass Rate"
                        value={`${metrics.passRate}%`}
                        change={metrics.passRateChange}
                        label="Target: >98.0%"
                        icon="check_circle"
                        trend="up"
                        colorClass="text-green-600"
                        bgClass="bg-green-100"
                    />
                    <MetricCard
                        title="Defect Count"
                        value={metrics.defectCount.toString()}
                        change={metrics.defectCountChange}
                        label="Units flagged for review"
                        icon="error"
                        trend="down" // Down is good for defects
                        colorClass="text-red-600"
                        bgClass="bg-red-100"
                    />
                </div>

                {/* Charts & Alerts Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1">
                    {/* Chart */}
                    <div className="lg:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col h-[450px]">
                        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
                            <div>
                                <h3 className="text-slate-900 dark:text-white text-lg font-bold">Inspection Trend</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Throughput over last 24 hours</p>
                            </div>
                            <div className="flex gap-2 items-center">
                                <span className="size-3 rounded-full bg-primary"></span>
                                <span className="text-xs text-slate-500 dark:text-slate-400">Units Processed</span>
                            </div>
                        </div>
                        <div className="flex-1 w-full p-4">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={metrics.throughputData}>
                                    <defs>
                                        <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#1173d4" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#1173d4" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                                    <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                                    <Area type="monotone" dataKey="value" stroke="#1173d4" strokeWidth={3} fillOpacity={1} fill="url(#colorValue)" />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </div>

                    {/* Alerts */}
                    <div className="lg:col-span-1 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm flex flex-col h-[450px]">
                        <div className="p-4 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center bg-slate-50 dark:bg-slate-800/50 rounded-t-xl">
                            <h3 className="text-slate-900 dark:text-white text-base font-bold">Recent Alerts</h3>
                            <button className="text-primary text-sm font-medium hover:underline">View All</button>
                        </div>
                        <div className="flex flex-col overflow-y-auto flex-1">
                            {alerts.map(alert => <AlertItem key={alert.id} alert={alert} />)}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};