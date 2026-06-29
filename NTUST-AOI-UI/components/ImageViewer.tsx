import React, { useState } from 'react';
import { CapturedImage, InspectionStatus } from '../types';
import { inspectionService } from '../services/inspectionService';

interface ImageViewerProps {
    image: CapturedImage;
    onClose: () => void;
    onUpdate: (updatedImage: CapturedImage) => void;
    onDelete?: (imageId: string) => void;
}

export const ImageViewer = ({ image, onClose, onUpdate, onDelete }: ImageViewerProps) => {
    const [zoom, setZoom] = useState(1);
    const [offset, setOffset] = useState({ x: 0, y: 0 });
    const [isDragging, setIsDragging] = useState(false);
    const [startPos, setStartPos] = useState({ x: 0, y: 0 });

    const [showMobilePanel, setShowMobilePanel] = useState(false);

    const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.5, 5));
    const handleZoomOut = () => {
        const newZoom = Math.max(zoom - 0.5, 1);
        setZoom(newZoom);
        if (newZoom === 1) setOffset({ x: 0, y: 0 });
    };
    const handleReset = () => {
        setZoom(1);
        setOffset({ x: 0, y: 0 });
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        if (zoom <= 1) return;
        setIsDragging(true);
        setStartPos({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDragging) return;
        setOffset({
            x: e.clientX - startPos.x,
            y: e.clientY - startPos.y
        });
    };

    const handleMouseUp = () => {
        setIsDragging(false);
    };



    const handleDelete = async () => {
        if (!window.confirm("⚠️ Are you sure you want to PERMANENTLY delete this image?\nThis will remove the file from the local disk and database.")) return;
        
        try {
            await inspectionService.deleteImage(image.image_id);
            if (onDelete) onDelete(image.image_id);
            onClose();
        } catch (error) {
            console.error('Failed to delete image', error);
            alert('Failed to delete image');
        }
    };

    const handleToggleStatus = async () => {
        const newStatus = image.condition === InspectionStatus.PASS ? InspectionStatus.FAIL : InspectionStatus.PASS;
        try {
            await inspectionService.updateImage(image.image_id, { condition: newStatus });
            onUpdate({ ...image, condition: newStatus });
        } catch (error) {
            console.error('Failed to update status', error);
        }
    };

    const handleWheel = (e: React.WheelEvent) => {
        const zoomStep = 0.2;
        const newZoom = e.deltaY < 0
            ? Math.min(zoom + zoomStep, 5)
            : Math.max(zoom - zoomStep, 1);

        setZoom(newZoom);
        if (newZoom === 1) setOffset({ x: 0, y: 0 });
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm p-0 md:p-10">
            <div className="relative flex w-full h-full bg-slate-950 md:bg-slate-900 md:border md:border-slate-800 md:rounded-2xl overflow-hidden shadow-2xl">

                {/* Left Side: Image Display */}
                <div className="relative flex-1 bg-slate-950 overflow-hidden flex items-center justify-center min-h-0 w-full">

                    {/* Floating Controls (Top Left) */}
                    <div className="absolute top-4 left-4 z-10 flex gap-2">
                        <button onClick={handleZoomIn} className="p-2 bg-slate-800/80 hover:bg-slate-700 text-white rounded-lg transition-colors flex items-center justify-center shadow-lg">
                            <span className="material-symbols-outlined">zoom_in</span>
                        </button>
                        <button onClick={handleZoomOut} className="p-2 bg-slate-800/80 hover:bg-slate-700 text-white rounded-lg transition-colors flex items-center justify-center shadow-lg">
                            <span className="material-symbols-outlined">zoom_out</span>
                        </button>
                        <button onClick={handleReset} className="p-2 bg-slate-800/80 hover:bg-slate-700 text-white rounded-lg transition-colors flex items-center justify-center text-xs font-bold uppercase tracking-tighter shadow-lg">
                            1:1
                        </button>
                    </div>

                    {/* Floating Controls (Top Right) */}
                    <div className="absolute top-4 right-4 z-10 flex gap-2">
                        <button
                            onClick={() => setShowMobilePanel(!showMobilePanel)}
                            className={`md:hidden p-2 rounded-lg transition-colors flex items-center justify-center shadow-lg ${showMobilePanel ? 'bg-primary text-white' : 'bg-slate-800/80 text-white'}`}
                        >
                            <span className="material-symbols-outlined">info</span>
                        </button>
                        <button onClick={onClose} className="p-2 bg-slate-800/80 hover:bg-red-500/20 text-white hover:text-red-400 rounded-lg transition-colors flex items-center justify-center shadow-lg">
                            <span className="material-symbols-outlined">close</span>
                        </button>
                    </div>

                    <div
                        onMouseDown={handleMouseDown}
                        onMouseMove={handleMouseMove}
                        onMouseUp={handleMouseUp}
                        onMouseLeave={handleMouseUp}
                        onWheel={handleWheel}
                        className={`transition-transform duration-200 ease-out ${isDragging ? 'cursor-grabbing' : (zoom > 1 ? 'cursor-grab' : 'cursor-default')}`}
                        style={{
                            transform: `scale(${zoom}) translate(${offset.x / zoom}px, ${offset.y / zoom}px)`,
                        }}
                    >
                        <img
                            src={image.local_path || ''}
                            alt={`R${image.row_idx} C${image.col_idx}`}
                            className="max-h-[100vh] md:max-h-[85vh] max-w-full object-contain select-none shadow-dark"
                            draggable={false}
                            loading="lazy"
                        />
                    </div>
                </div>

                {/* Right Side: Details & Notes (Desktop: Static Sidebar, Mobile: Overlay Sheet) */}
                <div className={`
                    absolute md:static bottom-0 left-0 right-0 z-20 
                    w-full md:w-80 lg:w-96 
                    flex flex-col bg-slate-900/95 md:bg-slate-900 border-t md:border-t-0 md:border-l border-slate-700 md:border-slate-800
                    backdrop-blur-md md:backdrop-blur-none
                    transition-transform duration-300 ease-in-out
                    ${showMobilePanel ? 'translate-y-0' : 'translate-y-full md:translate-y-0'}
                    max-h-[60vh] md:max-h-full rounded-t-2xl md:rounded-none shadow-[0_-10px_40px_rgba(0,0,0,0.5)] md:shadow-none
                `}>
                    {/* Mobile Pull Handle */}
                    <div className="md:hidden flex justify-center py-2" onClick={() => setShowMobilePanel(false)}>
                        <div className="w-12 h-1.5 rounded-full bg-slate-700"></div>
                    </div>

                    <div className="p-6 border-b border-slate-800 flex justify-between items-center">
                        <div>
                            <h3 className="text-xl font-bold text-white font-display">Row {image.row_idx} / Col {image.col_idx}</h3>
                            <p className="text-sm text-slate-400 font-mono truncate">{image.side} Side</p>
                        </div>
                        {/* Desktop Close Button (hidden on mobile as we have floating one) */}
                        <button onClick={onClose} className="hidden md:flex p-2 hover:bg-slate-800 text-slate-400 hover:text-white rounded-full transition-colors items-center justify-center">
                            <span className="material-symbols-outlined">close</span>
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto p-6 space-y-6">
                        <div>
                            <label className="block text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">Inspection Status</label>
                            <button
                                onClick={handleToggleStatus}
                                className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border-2 transition-all ${image.condition === InspectionStatus.PASS
                                    ? 'bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20'
                                    : 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                                    }`}
                            >
                                <div className="flex items-center gap-3">
                                    <span className={`size-3 rounded-full ${image.condition === InspectionStatus.PASS ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]'}`}></span>
                                    <span className="font-bold">{image.condition}</span>
                                </div>
                                <span className="material-symbols-outlined text-sm">sync</span>
                            </button>
                        </div>

                            <button
                                onClick={handleDelete}
                                className="w-full flex items-center justify-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 font-bold py-3 rounded-xl transition-all shadow-lg mt-2"
                            >
                                <span className="material-symbols-outlined text-[20px]">delete</span>
                                <span>Delete Image</span>
                            </button>

                        <div className="pt-6 border-t border-slate-800 space-y-4 text-xs mt-4">
                            <div className="flex justify-between">
                                <span className="text-slate-500">File Size</span>
                                <span className="text-slate-300 font-medium">{Math.round(image.file_size_bytes / 1024)} KB</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500">Image ID</span>
                                <span className="text-slate-500 font-mono text-[10px] break-all ml-4">{image.image_id}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
