import React, { useEffect, useState, useRef, useCallback } from 'react';
import { inspectionService } from '../services/inspectionService';
import { InspectionStatus, RunDetail, CapturedImage } from '../types';
import { ImageViewer } from './ImageViewer';

const PAGE_SIZE = 24;

export const RunGallery = ({ runId, onEdit, onBack }: { runId: string, onEdit: (runId: string) => void, onBack: () => void }) => {
    const [detail, setDetail] = useState<RunDetail | null>(null);
    const [images, setImages] = useState<CapturedImage[]>([]);
    const [selectedImage, setSelectedImage] = useState<CapturedImage | null>(null);
    const [loading, setLoading] = useState(false);
    const [hasMore, setHasMore] = useState(true);
    const [offset, setOffset] = useState(0);

    const observer = useRef<IntersectionObserver | null>(null);
    const lastImageElementRef = useCallback((node: HTMLDivElement) => {
        if (loading) return;
        if (observer.current) observer.current.disconnect();
        observer.current = new IntersectionObserver(entries => {
            if (entries[0].isIntersecting && hasMore) {
                setOffset(prevOffset => prevOffset + PAGE_SIZE);
            }
        });
        if (node) observer.current.observe(node);
    }, [loading, hasMore]);

    // Initial Load
    useEffect(() => {
        setLoading(true);
        inspectionService.getRunDetail(runId, PAGE_SIZE, 0)
            .then(data => {
                setDetail(data);
                setImages(data.images);
                setHasMore(data.images.length === PAGE_SIZE);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [runId]);

    // Load more when offset changes
    useEffect(() => {
        if (offset === 0) return;
        setLoading(true);
        inspectionService.getRunDetail(runId, PAGE_SIZE, offset)
            .then(data => {
                setImages(prev => [...prev, ...data.images]);
                setHasMore(data.images.length === PAGE_SIZE);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [runId, offset]);

    const handleImageUpdate = (updatedImage: CapturedImage) => {
        setImages(imgs => imgs.map(img => img.id === updatedImage.id ? updatedImage : img));
        setSelectedImage(updatedImage);
    };

    const formatTimestamp = (ts: string) => {
        try {
            const date = new Date(ts);
            return date.toLocaleString('zh-TW', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
            });
        } catch (e) { return ts; }
    };

    if (!detail && offset === 0) return <div className="p-10">Loading Details...</div>;
    if (!detail) return null;

    return (
        <div className="flex flex-col lg:flex-row flex-1 w-full max-w-[1600px] mx-auto h-full overflow-hidden">
            {/* Left Sidebar Metadata - Hidden on small screens, or adjust layout */}
            <aside className="hidden lg:flex flex-col w-80 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 shrink-0 h-full overflow-y-auto">
                <div className="flex flex-col gap-6 mb-8">
                    <div className="flex gap-4 items-start">
                        <div className="bg-slate-200 rounded-lg size-16 shrink-0 bg-cover bg-center shadow-sm" style={{ backgroundImage: images[0]?.imageUrl ? `url(${images[0]?.imageUrl})` : 'none' }}></div>
                        <div className="flex flex-col overflow-hidden">
                            <h1 className="text-slate-900 dark:text-white text-xl font-bold leading-tight truncate">{detail.runId}</h1>
                            <p className="text-slate-500 text-sm mt-1 truncate">{detail.batchId}</p>
                        </div>
                    </div>
                    <button onClick={() => onEdit(runId)} className="flex items-center justify-center gap-3 px-3 py-2.5 rounded-xl bg-primary hover:bg-blue-600 text-white transition-all w-full shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95">
                        <span className="material-symbols-outlined text-[18px]">edit</span>
                        <span className="text-sm font-bold">Edit Run Statuses</span>
                    </button>
                </div>

                <div className="flex flex-col gap-4">
                    <h3 className="text-slate-900 dark:text-white text-base font-bold">Run Details</h3>
                    <div className="grid grid-cols-[1fr_auto] gap-y-4 text-sm">
                        {[
                            ['Start Time', formatTimestamp(detail.startTime)],
                            ['End Time', formatTimestamp(detail.endTime)],
                            ['Operator', detail.operator]
                        ].map(([label, val]) => (
                            <div key={label as string} className="border-t border-slate-100 dark:border-slate-700 col-span-2 pt-3 flex justify-between gap-2 overflow-hidden">
                                <p className="text-slate-500 whitespace-nowrap">{label as string}</p>
                                <p className="text-slate-900 dark:text-white font-medium truncate">{val}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex flex-col flex-1 bg-background-light dark:bg-background-dark min-w-0 overflow-hidden relative">
                {/* Mobile Metadata Summary */}
                <div className="lg:hidden px-4 pt-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 pb-3">
                    <div className="flex items-center gap-3 overflow-hidden">
                        <div className="size-10 rounded-lg bg-cover bg-center border border-slate-200" style={{ backgroundImage: images[0]?.imageUrl ? `url(${images[0]?.imageUrl})` : 'none' }}></div>
                        <div className="flex flex-col overflow-hidden">
                            <h2 className="text-sm font-bold truncate">{detail.runId}</h2>
                            <p className="text-[10px] text-slate-500 uppercase font-black">{detail.batchId}</p>
                        </div>
                    </div>
                    <button onClick={() => onEdit(runId)} className="size-10 flex items-center justify-center rounded-full bg-primary/10 text-primary">
                        <span className="material-symbols-outlined text-[20px]">edit</span>
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto px-4 py-6 md:px-10">
                    <div className="flex flex-wrap items-center gap-2 mb-4">
                        <button onClick={onBack} className="text-slate-500 hover:text-primary text-sm font-medium flex items-center gap-1 group">
                            <span className="material-symbols-outlined text-sm transition-transform group-hover:-translate-x-1">arrow_back</span>
                            Runs
                        </button>
                        <span className="text-slate-400">/</span>
                        <span className="text-slate-900 dark:text-white text-sm font-medium truncate">{detail.runId}</span>
                    </div>

                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                        <h3 className="text-slate-900 dark:text-white text-2xl font-bold tracking-tight">Captured Images ({images.length})</h3>
                        <div className="flex bg-white dark:bg-slate-900 rounded-lg p-1 border border-slate-200 dark:border-slate-700 w-fit">
                            <button className="px-4 py-1.5 rounded text-sm font-medium bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm">All</button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 md:gap-6 pb-20">
                        {images.map((img, index) => {
                            const isFail = img.status === InspectionStatus.FAIL;
                            const isLast = images.length === index + 1;
                            
                            return (
                                <div
                                    key={img.id}
                                    ref={isLast ? lastImageElementRef : null}
                                    onClick={() => setSelectedImage(img)}
                                    className={`group flex flex-col bg-white dark:bg-slate-900 rounded-xl overflow-hidden border ${isFail ? 'border-red-200 ring-2 ring-red-100' : 'border-slate-200 dark:border-slate-800'} hover:shadow-lg transition-all cursor-pointer`}
                                >
                                    <div className="relative aspect-[4/3] bg-slate-100 dark:bg-slate-950 overflow-hidden">
                                        <div className="absolute inset-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-105" style={{ backgroundImage: `url(${img.imageUrl})` }}></div>
                                        <div className="absolute top-2 right-2">
                                            <span className={`inline-flex items-center gap-1 text-[10px] font-black px-2 py-0.5 rounded-full shadow-sm ${isFail ? 'bg-red-500 text-white' : 'bg-green-500 text-white'}`}>
                                                <span className="material-symbols-outlined text-[12px]">{isFail ? 'cancel' : 'check_circle'}</span>
                                                {img.status}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="p-3 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center text-sm">
                                        <span className="font-bold">{img.position}</span>
                                        <span className="text-slate-400 truncate ml-2 text-xs">{img.label}</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                    {loading && <div className="text-center py-8 text-slate-500 font-medium">Loading more images...</div>}
                </div>
            </main>

            {selectedImage && (
                <ImageViewer
                    image={selectedImage}
                    onClose={() => setSelectedImage(null)}
                    onUpdate={handleImageUpdate}
                />
            )}
        </div>
    );
};