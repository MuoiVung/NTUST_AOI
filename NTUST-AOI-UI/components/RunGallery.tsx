import React, { useEffect, useState, useRef, useCallback } from 'react';
import { inspectionService } from '../services/inspectionService';
import { InspectionStatus, RunDetail, CapturedImage } from '../types';
import { ImageViewer } from './ImageViewer';
import { formatTimestamp } from '../utils/formatters';

const PAGE_SIZE = 50;

export const RunGallery = ({ runId, onBack }: { runId: string, onEdit: (runId: string) => void, onBack: () => void }) => {
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

    // Load more
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

    const handleImageDelete = (imageId: string) => {
        setImages(imgs => imgs.filter(img => img.id !== imageId));
    };

    if (!detail && offset === 0) return <div className="p-10 font-medium text-slate-500">Loading data...</div>;
    if (!detail) return null;

    return (
        <div className="flex flex-col lg:flex-row flex-1 w-full max-w-[1600px] mx-auto h-full overflow-hidden">
            {/* Sidebar Metadata */}
            <aside className="hidden lg:flex flex-col w-80 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 shrink-0 h-full overflow-y-auto">
                <div className="flex flex-col gap-6 mb-8">
                    <div className="flex gap-4 items-start">
                        <div className="bg-slate-100 rounded-lg size-16 shrink-0 bg-cover bg-center shadow-sm flex items-center justify-center text-primary border border-slate-200" style={{ backgroundImage: images[0]?.imageUrl ? `url(${images[0]?.imageUrl})` : 'none' }}>
                            {!images[0]?.imageUrl && <span className="material-symbols-outlined">image</span>}
                        </div>
                        <div className="flex flex-col overflow-hidden">
                            <h1 className="text-slate-900 dark:text-white text-xl font-bold leading-tight truncate">{detail.runId}</h1>
                            <p className="text-slate-500 text-sm mt-1 truncate">Board: {detail.batchId}</p>
                        </div>
                    </div>
                    <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Global Status</p>
                        <div className="flex items-center gap-2">
                             <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-bold bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300`}>
                                <span className="mr-2 size-2 rounded-full bg-green-500"></span>
                                COMPLETED
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex flex-col gap-4">
                    <h3 className="text-slate-900 dark:text-white text-base font-bold border-b border-slate-100 dark:border-slate-800 pb-2">Run Details</h3>
                    <div className="grid grid-cols-[1fr_auto] gap-y-4 text-sm">
                        {[
                            ['Start Time', formatTimestamp(detail.startTime)],
                            ['End Time', formatTimestamp(detail.endTime)],
                            ['Machine ID', detail.operator]
                        ].map(([label, val]) => (
                            <div key={label as string} className="col-span-2 flex justify-between gap-2 overflow-hidden">
                                <p className="text-slate-500 whitespace-nowrap">{label as string}</p>
                                <p className="text-slate-900 dark:text-white font-medium truncate">{val}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex flex-col flex-1 bg-background-light dark:bg-background-dark min-w-0 overflow-hidden relative">
                <div className="flex-1 overflow-y-auto px-4 py-6 md:px-10">
                    <div className="flex flex-wrap items-center gap-2 mb-4">
                        <button onClick={onBack} className="text-slate-500 hover:text-primary text-sm font-medium flex items-center gap-1 group">
                            <span className="material-symbols-outlined text-sm transition-transform group-hover:-translate-x-1">arrow_back</span>
                            Inspection Runs
                        </button>
                        <span className="text-slate-400">/</span>
                        <span className="text-slate-900 dark:text-white text-sm font-medium truncate">{detail.runId}</span>
                    </div>

                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                        <h3 className="text-slate-900 dark:text-white text-2xl font-bold tracking-tight">Captured Images ({images.length})</h3>
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
                                    className={`group flex flex-col bg-white dark:bg-slate-900 rounded-xl overflow-hidden border ${isFail ? 'border-red-500 ring-2 ring-red-100' : 'border-slate-200 dark:border-slate-800'} hover:shadow-lg transition-all cursor-pointer`}
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
                                    <div className="p-3 border-t border-slate-100 dark:border-slate-800 flex flex-col gap-1 text-sm">
                                        <div className="flex justify-between items-center">
                                            <span className="font-bold text-slate-900 dark:text-white">{img.position}</span>
                                            <span className="text-[10px] text-slate-400 font-mono">ID: {img.id.split('-')[0]}</span>
                                        </div>
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
                    onDelete={handleImageDelete}
                />
            )}
        </div>
    );
};