import React, { useState } from 'react';
import { RunList } from './components/RunList';
import { RunGallery } from './components/RunGallery';
import { EditRun } from './components/EditRun';
import { NewInspection } from './components/NewInspection';
import { IMAGES } from './services/mockData';

enum View {
    RUN_LIST = 'RUN_LIST',
    RUN_DETAIL = 'RUN_DETAIL',
    RUN_EDIT = 'RUN_EDIT',
    NEW_INSPECTION = 'NEW_INSPECTION'
}

const Sidebar = ({
    currentView,
    onChangeView,
    isCollapsed,
    onToggle
}: {
    currentView: View,
    onChangeView: (v: View) => void,
    isCollapsed: boolean,
    onToggle: () => void
}) => {
    const NavItem = ({ view, icon, label }: { view: View, icon: string, label: string }) => {
        const isActive = currentView === view || (view === View.RUN_LIST && [View.RUN_DETAIL, View.RUN_EDIT].includes(currentView));
        return (
            <button
                onClick={() => onChangeView(view)}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg group transition-all duration-300 w-full ${isActive ? 'bg-slate-100 dark:bg-slate-800' : 'hover:bg-slate-50 dark:hover:bg-slate-800'}`}
                title={isCollapsed ? label : ""}
            >
                <span className={`material-symbols-outlined shrink-0 ${isActive ? 'text-primary' : 'text-slate-900 dark:text-slate-300 group-hover:text-primary'}`}>{icon}</span>
                {!isCollapsed && <p className={`text-sm font-medium leading-normal whitespace-nowrap overflow-hidden transition-all duration-300 ${isActive ? 'text-slate-900 dark:text-white' : 'text-slate-900 dark:text-slate-300'}`}>{label}</p>}
            </button>
        );
    };

    return (
        <aside className={`${isCollapsed ? 'w-20' : 'w-64'} shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col justify-between p-4 transition-all duration-300 relative z-20`}>
            <div className="flex flex-col gap-4">
                <div className="flex gap-3 justify-between items-center mb-6">
                    <div className="flex gap-3 items-center overflow-hidden">
                        <div className="bg-center bg-no-repeat bg-cover rounded-full size-10 shrink-0 bg-primary/10 flex items-center justify-center text-primary">
                            <span className="material-symbols-outlined">center_focus_strong</span>
                        </div>
                        {!isCollapsed && (
                            <div className="flex flex-col overflow-hidden transition-all duration-300">
                                <h1 className="text-slate-900 dark:text-white text-base font-bold leading-normal truncate">AOI System</h1>
                                <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-normal truncate">Line 1 - PCB</p>
                            </div>
                        )}
                    </div>
                    <button
                        onClick={onToggle}
                        className="size-8 hidden md:flex items-center justify-center rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors"
                    >
                        <span className="material-symbols-outlined text-[20px]">{isCollapsed ? 'tab_unselected' : 'menu_open'}</span>
                    </button>
                </div>
                <nav className="flex flex-col gap-2">
                    <NavItem view={View.RUN_LIST} icon="dashboard" label="Dashboard" />
                    <button className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 group transition-colors w-full" title={isCollapsed ? "Settings" : ""}>
                        <span className="material-symbols-outlined text-slate-900 dark:text-slate-300 group-hover:text-primary shrink-0">settings</span>
                        {!isCollapsed && <p className="text-slate-900 dark:text-slate-300 text-sm font-medium leading-normal whitespace-nowrap overflow-hidden transition-all duration-300">Settings</p>}
                    </button>
                </nav>
            </div>
            <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'} px-3 py-2 mt-auto border-t border-slate-200 dark:border-slate-800 pt-4 overflow-hidden`}>
                <div className="bg-center bg-no-repeat bg-cover rounded-full size-8 shrink-0" style={{ backgroundImage: `url(${IMAGES.userAvatar})` }}></div>
                {!isCollapsed && (
                    <div className="flex flex-col transition-all duration-300 overflow-hidden">
                        <p className="text-slate-900 dark:text-white text-sm font-medium truncate">Operator 1</p>
                        <p className="text-slate-500 dark:text-slate-400 text-xs truncate">Logged in</p>
                    </div>
                )}
            </div>
        </aside>
    );
};

export default function App() {
    const [currentView, setCurrentView] = useState<View>(View.RUN_LIST);
    const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    const handleViewDetail = (id: string) => {
        setSelectedRunId(id);
        setCurrentView(View.RUN_DETAIL);
    };

    const handleEditRun = (id: string) => {
        setSelectedRunId(id);
        setCurrentView(View.RUN_EDIT);
    };

    const renderContent = () => {
        switch (currentView) {
            case View.RUN_LIST:
                return <RunList onViewDetail={handleViewDetail} onCreate={() => setCurrentView(View.NEW_INSPECTION)} />;
            case View.RUN_DETAIL:
                return selectedRunId
                    ? <RunGallery runId={selectedRunId} onEdit={handleEditRun} onBack={() => setCurrentView(View.RUN_LIST)} />
                    : <RunList onViewDetail={handleViewDetail} onCreate={() => setCurrentView(View.NEW_INSPECTION)} />;
            case View.RUN_EDIT:
                return selectedRunId
                    ? <EditRun runId={selectedRunId} onSave={() => setCurrentView(View.RUN_DETAIL)} onCancel={() => setCurrentView(View.RUN_DETAIL)} />
                    : <RunList onViewDetail={handleViewDetail} onCreate={() => setCurrentView(View.NEW_INSPECTION)} />;
            case View.NEW_INSPECTION:
                return <NewInspection onSave={() => setCurrentView(View.RUN_LIST)} onCancel={() => setCurrentView(View.RUN_LIST)} />;
            default:
                return <RunList onViewDetail={handleViewDetail} onCreate={() => setCurrentView(View.NEW_INSPECTION)} />;
        }
    };

    return (
        <div className="flex h-screen w-full flex-row overflow-hidden bg-background-light dark:bg-background-dark text-slate-900 dark:text-white">
            {/* Mobile Header */}
            <header className="md:hidden fixed top-0 left-0 right-0 h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 z-30">
                <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-primary">center_focus_strong</span>
                    <span className="font-bold">AOI System</span>
                </div>
                <button
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    className="size-10 flex items-center justify-center rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                    <span className="material-symbols-outlined">{isMobileMenuOpen ? 'close' : 'menu'}</span>
                </button>
            </header>

            {/* Sidebar Desktop / Mobile Overlay */}
            <div className={`
                ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
                fixed inset-0 z-40 md:relative md:inset-auto md:z-auto transition-transform duration-300 ease-in-out flex flex-row
            `}>
                <Sidebar
                    currentView={currentView}
                    onChangeView={(v) => { setCurrentView(v); setIsMobileMenuOpen(false); }}
                    isCollapsed={isSidebarCollapsed}
                    onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                />
                {/* Mobile Backdrop */}
                <div
                    className={`${isMobileMenuOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'} fixed inset-0 bg-black/20 backdrop-blur-sm transition-opacity md:hidden -z-10`}
                    onClick={() => setIsMobileMenuOpen(false)}
                />
            </div>

            <main className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${isMobileMenuOpen ? 'blur-sm md:blur-none' : ''}`}>
                <div className="md:hidden h-16 shrink-0" /> {/* Spacer for mobile header */}
                {renderContent()}
            </main>
        </div>
    );
}