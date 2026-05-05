'use client';

import { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { FileText, ChevronLeft, ChevronRight, ZoomIn, ZoomOut } from 'lucide-react';
import { Annotation } from '@/lib/types';
import { api } from '@/lib/api';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker using unpkg CDN
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const PAGE_WIDTH_INCHES  = 8.5;
const PAGE_HEIGHT_INCHES = 11.0;

interface RightPaneProps {
  selectedDoc: string | null;
  annotations: Annotation[];
  targetPage: number;
}

export function RightPane({ selectedDoc, annotations, targetPage }: RightPaneProps) {
  const containerRef   = useRef<HTMLDivElement>(null);
  const pageRefs       = useRef<Map<number, HTMLDivElement>>(new Map());

  const [numPages,        setNumPages]        = useState<number>(0);
  const [currentPage,     setCurrentPage]     = useState<number>(1);
  const [containerWidth,  setContainerWidth]  = useState<number>(0);
  const [scale,           setScale]           = useState<number>(1.0);

  const pdfUrl = useMemo(
    () => selectedDoc ? api.pdfUrl(selectedDoc) : null,
    [selectedDoc]
  );

  // Reset when document changes
  useEffect(() => {
    setNumPages(0);
    setCurrentPage(1);
    setScale(1.0);
  }, [selectedDoc]);

  // Scroll to targetPage when it changes (from audit/chat)
  useEffect(() => {
    if (targetPage < 1 || targetPage > numPages) return;
    setCurrentPage(targetPage);
    const el = pageRefs.current.get(targetPage);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [targetPage, numPages]);

  // Resize observer
  useEffect(() => {
    if (!containerRef.current) return;
    const update = (w: number) => setContainerWidth(w > 48 ? w - 48 : 600);
    update(containerRef.current.clientWidth);
    const obs = new ResizeObserver(entries => {
      if (entries[0]) update(entries[0].contentRect.width);
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // Scroll spy — update currentPage indicator
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const scrollTop = container.scrollTop;
    const viewMid   = scrollTop + container.clientHeight / 2;

    let closestPage = 1;
    let closestDist = Infinity;
    pageRefs.current.forEach((el, pg) => {
      const mid  = el.offsetTop + el.clientHeight / 2;
      const dist = Math.abs(mid - viewMid);
      if (dist < closestDist) { closestDist = dist; closestPage = pg; }
    });
    setCurrentPage(closestPage);
  }, []);

  const navigatePage = (delta: number) => {
    const next = Math.max(1, Math.min(numPages, currentPage + delta));
    setCurrentPage(next);
    const el = pageRefs.current.get(next);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const pageWidth = containerWidth * scale;

  // Annotation overlay helper
  const renderAnnotations = (pageNum: number) => {
    const pageH = pageWidth * (PAGE_HEIGHT_INCHES / PAGE_WIDTH_INCHES);
    return annotations
      .filter(a => a.page === pageNum)
      .map((ann, i) => {
        const pxX = (ann.x / PAGE_WIDTH_INCHES)  * pageWidth;
        const pxY = (ann.y / PAGE_HEIGHT_INCHES) * pageH;
        const pxW = (ann.width  / PAGE_WIDTH_INCHES)  * pageWidth;
        const pxH = (ann.height / PAGE_HEIGHT_INCHES) * pageH;
        const color = ann.color === 'orange' ? '#f59e0b' : '#ef4444';
        return (
          <div
            key={i}
            className="absolute z-10 pointer-events-none rounded-sm animate-pulse"
            style={{
              left:   `${pxX}px`,
              top:    `${pxY}px`,
              width:  `${pxW}px`,
              height: `${pxH}px`,
              backgroundColor: `${color}33`,
              border: `1.5px solid ${color}cc`,
              boxShadow: `0 0 12px ${color}55`,
              transition: 'all 0.4s ease',
            }}
          />
        );
      });
  };

  // ---- Empty State ----
  if (!selectedDoc) {
    return (
      <div className="flex-1 flex items-center justify-center h-full">
        <div className="text-center animate-fade-in">
          <div className="w-20 h-20 rounded-2xl mx-auto mb-4 flex items-center justify-center"
               style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-sm)' }}>
            <FileText className="w-8 h-8" style={{ color: 'var(--text-muted)' }} />
          </div>
          <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>No document selected</p>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Choose a PDF from the left panel to begin
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* ---- Viewer Toolbar ---- */}
      <div className="shrink-0 h-10 flex items-center px-3 gap-2 border-b"
           style={{ borderColor: 'var(--border-default)', background: 'var(--bg-secondary)' }}>
        <FileText className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
        <span className="text-xs font-medium truncate flex-1 mr-2" style={{ color: 'var(--text-primary)' }}>
          {selectedDoc}
        </span>

        {/* Annotation badge */}
        {annotations.length > 0 && (
          <span className="text-[10px] px-2 py-0.5 rounded-full shrink-0"
                style={{ background: 'rgba(220,38,38,0.12)', color: 'var(--accent-red)' }}>
            {annotations.length} highlight{annotations.length > 1 ? 's' : ''}
          </span>
        )}

        {/* Zoom controls */}
        <div className="flex items-center gap-1 ml-auto shrink-0">
          <button
            onClick={() => setScale(s => Math.max(0.5, +(s - 0.1).toFixed(1)))}
            disabled={scale <= 0.5}
            className="p-1 rounded hover:opacity-70 transition-opacity disabled:opacity-30"
            style={{ color: 'var(--text-secondary)' }} title="Zoom out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[10px] w-9 text-center tabular-nums"
                style={{ color: 'var(--text-muted)' }}>
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale(s => Math.min(2.5, +(s + 0.1).toFixed(1)))}
            disabled={scale >= 2.5}
            className="p-1 rounded hover:opacity-70 transition-opacity disabled:opacity-30"
            style={{ color: 'var(--text-secondary)' }} title="Zoom in"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Page navigation */}
        {numPages > 1 && (
          <div className="flex items-center gap-1 shrink-0 ml-2">
            <button
              onClick={() => navigatePage(-1)}
              disabled={currentPage <= 1}
              className="p-1 rounded hover:opacity-70 transition-opacity disabled:opacity-30"
              style={{ color: 'var(--text-secondary)' }} title="Previous page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="text-[10px] tabular-nums whitespace-nowrap"
                  style={{ color: 'var(--text-muted)' }}>
              {currentPage} / {numPages}
            </span>
            <button
              onClick={() => navigatePage(1)}
              disabled={currentPage >= numPages}
              className="p-1 rounded hover:opacity-70 transition-opacity disabled:opacity-30"
              style={{ color: 'var(--text-secondary)' }} title="Next page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* ---- Scrollable PDF Container ---- */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-6 flex flex-col items-center gap-4 min-h-0"
        style={{ background: '#1a1a2e' }}
      >
        {pdfUrl && containerWidth > 0 && (
          <Document
            file={pdfUrl}
            onLoadSuccess={({ numPages: n }) => setNumPages(n)}
            onLoadError={err => console.error('PDF load error:', err)}
            loading={
              <div className="text-white text-sm text-center p-10 animate-pulse">Loading PDF engine…</div>
            }
            error={
              <div className="text-red-400 text-sm text-center p-10 rounded-xl"
                   style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
                Failed to load PDF. Check the network console.
              </div>
            }
          >
            {Array.from({ length: numPages }, (_, i) => i + 1).map(pageNum => (
              <div
                key={pageNum}
                ref={el => { if (el) pageRefs.current.set(pageNum, el); else pageRefs.current.delete(pageNum); }}
                className="relative shadow-2xl rounded overflow-hidden"
                style={{ width: pageWidth }}
              >
                <Page
                  pageNumber={pageNum}
                  width={pageWidth}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                />
                {renderAnnotations(pageNum)}

                {/* Page number label */}
                <div className="absolute bottom-2 right-2 text-[10px] px-2 py-0.5 rounded-full pointer-events-none"
                     style={{ background: 'rgba(0,0,0,0.5)', color: 'rgba(255,255,255,0.7)' }}>
                  {pageNum}
                </div>
              </div>
            ))}
          </Document>
        )}

        {pdfUrl && containerWidth <= 0 && (
          <div className="text-white text-xs animate-pulse">Calculating layout…</div>
        )}
      </div>
    </div>
  );
}
