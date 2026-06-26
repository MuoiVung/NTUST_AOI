import React, { useState, useEffect, useRef, useCallback } from 'react';

type SystemStatus = 'OK' | 'ERROR' | 'IDLE';

interface WorkflowStep {
    id: number;
    label: string;
    status: 'pending' | 'active' | 'completed' | 'error';
}

const initialSteps: WorkflowStep[] = [
    { id: 1, label: 'Verify Serial Number', status: 'pending' },
    { id: 2, label: 'Initialize & Calculate Scan Points', status: 'pending' },
    { id: 3, label: 'Scanning PCB', status: 'pending' },
    { id: 4, label: 'Save Results', status: 'pending' },
];

export function OperatorDashboard() {
    const [mode, setMode] = useState<'SCANNER' | 'MANUAL'>('SCANNER');
    const [serialNumber, setSerialNumber] = useState('');
    const [isProcessing, setIsProcessing] = useState(false);

    // Status indicators
    const [plcStatus, setPlcStatus] = useState<SystemStatus>('IDLE');
    const [apiStatus, setApiStatus] = useState<SystemStatus>('IDLE');
    const [cameraStatus, setCameraStatus] = useState<SystemStatus>('IDLE');

    // Order info
    const [currentOrder, setCurrentOrder] = useState<string>('-');
    const [actualQuantity, setActualQuantity] = useState<number>(0);
    const [activeSn, setActiveSn] = useState<string>('');

    const inputRef = useRef<HTMLInputElement>(null);
    const isProcessingRef = useRef(false);

    const [steps, setSteps] = useState<WorkflowStep[]>(initialSteps);
    const [totalPoints, setTotalPoints] = useState<number>(0);
    const [currentPoint, setCurrentPoint] = useState<number>(0);
    const [hasInitialized, setHasInitialized] = useState<boolean>(false);

    // Keep ref in sync with state
    const updateProcessing = useCallback((val: boolean) => {
        setIsProcessing(val);
        isProcessingRef.current = val;
    }, []);

    const fetchStatus = useCallback(async () => {
        try {
            const res = await fetch('http://localhost:8000/system/status');
            if (res.ok) {
                const data = await res.json();
                setPlcStatus(data.plc as SystemStatus);
                setApiStatus(data.shopfloor as SystemStatus);
                setCameraStatus(data.camera as SystemStatus);
                if (data.current_order) setCurrentOrder(data.current_order);
                if (data.actual_quantity !== undefined) setActualQuantity(data.actual_quantity);
                if (data.active_sn) setActiveSn(data.active_sn);

                // isProcessing is managed only by WebSocket events (RUN_COMPLETE, PC_IDLE, etc.)
                // fetchStatus() does NOT touch isProcessing to avoid polling conflicts.

                if (!hasInitialized) {
                    setHasInitialized(true);
                    if (!data.is_processing && data.active_sn) {
                        setSteps(initialSteps.map(s => ({ ...s, status: 'completed' })));
                    }
                }
            } else {
                setPlcStatus('ERROR'); setApiStatus('ERROR'); setCameraStatus('ERROR');
            }
        } catch {
            setPlcStatus('ERROR'); setApiStatus('ERROR'); setCameraStatus('ERROR');
        }
    }, [hasInitialized, updateProcessing]);

    // WebSocket connection with auto-reconnect
    useEffect(() => {
        let ws: WebSocket;
        let reconnectTimer: NodeJS.Timeout;
        let alive = true;

        const connect = () => {
            if (!alive) return;
            ws = new WebSocket('ws://localhost:8000/ws/ui-updates');

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log("WebSocket event:", data);
                    if (data.type === 'event' || data.type === 'step_status') {
                        if (data.plc_status) setPlcStatus(data.plc_status);

                        const state = data.pc_state || "";
                        const eventName = data.event_name || "";

                        let activeStepId = 0;
                        if (state === "PC_SEMI_SELECT" || state === "PC_SEMI_START_RUN") activeStepId = 1;
                        if (eventName === "RECIPE_DOWNLOAD_START" || state === "PC_SEMI_DOWNLOAD_RECIPE" || eventName === "RECIPE_LOADED") {
                            activeStepId = 2;
                            if (eventName === "RECIPE_DOWNLOAD_START" && data.payload_json && data.payload_json.length > 0) {
                                setTotalPoints(data.payload_json[0]);
                            }
                        }
                        if (state === "PC_SEMI_MONITOR_RUN" || 
                            ["SEMI_AUTO_STEP_STARTED", "POSITION_REACHED", "CAPTURE_AUTH_REQUEST", "CAPTURE_WINDOW_OPEN", "CAPTURE_DONE", "STEP_COMPLETE"].includes(eventName)) {
                            activeStepId = 3;
                        }
                        if (eventName === "RUN_COMPLETE") {
                            // Briefly show 'Reporting Results' as active
                            setSteps(prev => prev.map(s => {
                                if (s.id < 4) return { ...s, status: 'completed' };
                                if (s.id === 4) return { ...s, status: 'active' };
                                return { ...s, status: 'pending' };
                            }));
                            // Then complete the whole workflow after a short delay
                            setTimeout(() => {
                                setSteps(initialSteps.map(s => ({ ...s, status: 'completed' })));
                                fetchStatus();
                            }, 1500);
                            return;
                        }
                        if (state === "PC_IDLE") {
                            updateProcessing(false);
                            activeStepId = 5; // Completes steps 1-4
                        }

                        if (data.type === 'step_status' && data.step_index !== undefined) {
                            setCurrentPoint(data.step_index);
                        }

                        if (activeStepId > 0) {
                            setSteps(prev => prev.map(s => {
                                if (s.id < activeStepId) return { ...s, status: 'completed' };
                                if (s.id === activeStepId) return { ...s, status: 'active' };
                                return { ...s, status: 'pending' };
                            }));
                        }
                    } else if (data.type === 'error') {
                        setSteps(prev => prev.map(s => s.status === 'active' ? { ...s, status: 'error' } : s));
                        alert(`System Error: ${data.error_message}`);
                        updateProcessing(false);
                        fetchStatus();
                    }
                } catch (e) {
                    console.error("WS parse error", e);
                }
            };

            ws.onclose = () => {
                if (alive) {
                    console.warn('[WS] Disconnected, reconnecting in 2s...');
                    reconnectTimer = setTimeout(connect, 2000);
                }
            };

            ws.onerror = () => ws.close();
        };

        connect();
        return () => {
            alive = false;
            clearTimeout(reconnectTimer);
            ws?.close();
        };
    }, [fetchStatus, updateProcessing]);

    useEffect(() => {
        if (mode === 'SCANNER' && inputRef.current) {
            inputRef.current.focus();
        }
    }, [mode]);

    useEffect(() => {
        let buffer = '';
        let timeoutId: NodeJS.Timeout;

        const handleGlobalKeyDown = (e: KeyboardEvent) => {
            if (mode !== 'SCANNER') return;
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
                if (e.target !== inputRef.current) return;
            }
            if (e.key === 'Enter') {
                if (buffer.length > 0) {
                    setSerialNumber(buffer);
                    startRun(buffer);
                    buffer = '';
                }
            } else if (e.key.length === 1) {
                buffer += e.key;
                clearTimeout(timeoutId);
                timeoutId = setTimeout(() => { buffer = ''; }, 100);
            }
        };

        window.addEventListener('keydown', handleGlobalKeyDown);
        return () => {
            window.removeEventListener('keydown', handleGlobalKeyDown);
            clearTimeout(timeoutId);
        };
    }, [mode]);

    const startRun = async (sn: string) => {
        if (!sn.trim()) return;
        updateProcessing(true);
        setSerialNumber('');
        await fetchStatus();

        try {
            const response = await fetch('http://localhost:8000/runs/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ serial_number: sn }),
            });

            if (!response.ok) throw new Error('Failed to start run via API');

            setSteps(initialSteps.map(s => s.id === 1 ? { ...s, status: 'active' } : s));
            setTimeout(fetchStatus, 1000);
        } catch (error) {
            console.error("Error starting run:", error);
            updateProcessing(false);
            alert("Failed to start run. Is backend running?");
        }
    };

    // Fetch once on mount + polling every 5s as safety net
    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, [fetchStatus]);

    const StatusIndicator = ({ label, status }: { label: string, status: SystemStatus }) => {
        const colors = {
            OK: 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.6)]',
            ERROR: 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.6)]',
            IDLE: 'bg-slate-500'
        };
        return (
            <div className="flex items-center gap-2 bg-slate-100 dark:bg-slate-800 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700">
                <div className={`w-3 h-3 rounded-full ${colors[status]} transition-all duration-300`} />
                <span className="text-sm font-medium">{label}</span>
            </div>
        );
    };


    return (
        <div className="flex flex-col h-full overflow-hidden bg-slate-50 dark:bg-[#0d1117] p-4 lg:p-6">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 lg:mb-8 gap-4">
                    <div>
                        <h1 className="text-xl lg:text-2xl font-bold text-slate-900 dark:text-white">Operator Dashboard</h1>
                        <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-slate-500 dark:text-slate-400">
                            <span className="flex items-center gap-1 font-mono bg-slate-200 dark:bg-slate-800 px-2 py-1 rounded text-primary">
                                <span className="material-symbols-outlined text-[16px]">receipt_long</span> 
                                <span className="text-slate-500 dark:text-slate-400 font-sans text-xs font-bold tracking-wider mr-1">Manufacturing Order:</span>
                                {currentOrder}
                            </span>
                            <span className="font-semibold text-slate-700 dark:text-slate-300">
                                Scanned: <span className="text-primary text-base">{actualQuantity}</span> PCBs
                            </span>
                            {activeSn && activeSn !== '-' && (
                                <span className="font-semibold text-slate-700 dark:text-slate-300 border-l border-slate-300 dark:border-slate-700 pl-4">
                                    Current S/N: <span className="text-primary text-base font-mono">{activeSn}</span>
                                </span>
                            )}
                        </div>
                    </div>
                    <div className="flex flex-col items-start md:items-end w-full md:w-auto">
                        <h3 className="text-xs lg:text-sm font-bold mb-2 text-slate-500 uppercase tracking-wider hidden md:block">Connection Status</h3>
                        <div className="flex flex-wrap gap-2 lg:gap-4 w-full md:w-auto">
                            <StatusIndicator label="PLC" status={plcStatus} />
                            <StatusIndicator label="Shopfloor" status={apiStatus} />
                            <StatusIndicator label="Camera" status={cameraStatus} />
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 overflow-y-auto pb-8">
                    {/* Left Column: Input Control */}
                    <div className="lg:col-span-4 xl:col-span-3 flex flex-col gap-6">
                        <div className="bg-white dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] rounded-xl p-6 shadow-sm">
                            <div className="flex flex-wrap items-center justify-between mb-6 gap-4">
                                <h2 className="text-lg font-semibold whitespace-nowrap">Input Mode</h2>
                                <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1 shrink-0">
                                    <button
                                        onClick={() => setMode('SCANNER')}
                                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${mode === 'SCANNER' ? 'bg-white dark:bg-[#21262d] shadow-sm text-primary' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                                    >
                                        <span className="flex items-center gap-2"><span className="material-symbols-outlined text-[18px]">barcode_scanner</span> Scanner</span>
                                    </button>
                                    <button
                                        onClick={() => setMode('MANUAL')}
                                        className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${mode === 'MANUAL' ? 'bg-white dark:bg-[#21262d] shadow-sm text-primary' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                                    >
                                        <span className="flex items-center gap-2"><span className="material-symbols-outlined text-[18px]">keyboard</span> Manual</span>
                                    </button>
                                </div>
                            </div>

                            <div className="flex flex-col gap-4">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                    Serial Number (S/N)
                                </label>

                                {mode === 'SCANNER' ? (
                                    <div className="relative">
                                        <input
                                            ref={inputRef}
                                            type="text"
                                            value={serialNumber}
                                            readOnly
                                            placeholder="Waiting for scanner input..."
                                            className="w-full px-4 py-3 rounded-lg border-2 border-primary/50 bg-primary/5 text-primary focus:outline-none focus:ring-0 placeholder:text-primary/40 font-mono text-lg"
                                        />
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2 animate-pulse text-primary">
                                            <span className="material-symbols-outlined">barcode_scanner</span>
                                        </div>
                                    </div>
                                ) : (
                                    <input
                                        type="text"
                                        value={serialNumber}
                                        onChange={(e) => setSerialNumber(e.target.value)}
                                        placeholder="Enter S/N manually..."
                                        className="w-full px-4 py-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-primary font-mono text-lg"
                                        disabled={isProcessing}
                                    />
                                )}

                                {mode === 'MANUAL' && (
                                    <button
                                        onClick={() => startRun(serialNumber)}
                                        disabled={isProcessing || !serialNumber.trim()}
                                        className="w-full mt-2 bg-primary hover:bg-primary-dark disabled:bg-slate-300 dark:disabled:bg-slate-700 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
                                    >
                                        {isProcessing ? (
                                            <><span className="material-symbols-outlined animate-spin">refresh</span> Processing...</>
                                        ) : (
                                            <><span className="material-symbols-outlined">play_arrow</span> Start Inspection</>
                                        )}
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Right Column: Workflow Progress */}
                    <div className="lg:col-span-8 xl:col-span-9">
                        <div className="bg-white dark:bg-[#161b22] border border-slate-200 dark:border-[#30363d] rounded-xl p-6 shadow-sm h-full">
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-6 gap-4">
                                <h2 className="text-lg font-semibold flex items-center gap-2">
                                    <span className="material-symbols-outlined">account_tree</span>
                                    Process Workflow
                                </h2>
                            </div>

                            <div className="relative pl-6">
                                {/* Vertical Line */}
                                <div className="absolute left-[15px] top-4 bottom-4 w-0.5 bg-slate-200 dark:bg-slate-800" />

                                <div className="flex flex-col gap-6">
                                    {steps.map((step) => (
                                        <div key={step.id} className="relative flex items-center gap-4">
                                            {/* Status Dot */}
                                            <div className={`
                                                absolute -left-6 z-10 size-6 rounded-full border-4 border-white dark:border-[#161b22] flex items-center justify-center
                                                ${step.status === 'completed' ? 'bg-green-500' :
                                                  step.status === 'active' ? 'bg-primary animate-pulse' :
                                                  step.status === 'error' ? 'bg-red-500' : 'bg-slate-200 dark:bg-slate-700'}
                                            `}>
                                                {step.status === 'completed' && <span className="material-symbols-outlined text-[12px] text-white font-bold">check</span>}
                                            </div>

                                            {/* Step Content */}
                                            <div className={`
                                                flex-1 p-4 rounded-lg border transition-all duration-300
                                                ${step.status === 'active' ? 'border-primary bg-primary/5 shadow-sm' :
                                                  step.status === 'completed' ? 'border-green-500/30 bg-green-500/5' :
                                                  'border-transparent'}
                                            `}>
                                                <div className="flex items-center justify-between">
                                                    <h3 className={`text-sm font-medium ${
                                                        step.status === 'active' ? 'text-blue-600 dark:text-blue-400' :
                                                        step.status === 'completed' ? 'text-slate-900 dark:text-white' :
                                                        step.status === 'error' ? 'text-red-600 dark:text-red-400' :
                                                        'text-slate-500'
                                                    }`}>
                                                        {step.id === 3 && step.status === 'active' && totalPoints > 0
                                                            ? `${step.label} (Point ${currentPoint}/${totalPoints})`
                                                            : step.label}
                                                    </h3>
                                                    {step.status === 'active' && (
                                                        <span className="text-xs font-semibold text-primary bg-primary/10 px-2 py-1 rounded">IN PROGRESS</span>
                                                    )}
                                                    {step.status === 'completed' && (
                                                        <span className="text-xs font-semibold text-green-600 dark:text-green-400">DONE</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
        </div>
    );
}
