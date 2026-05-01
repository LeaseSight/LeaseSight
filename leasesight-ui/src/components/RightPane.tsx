'use client';

import { useEffect, useRef, useState, useMemo } from 'react';
import { FileText } from 'lucide-react';
import { Annotation } from '@/lib/types';
import { api } from '@/lib/api';
import { DiffViewer } from './DiffViewer';

interface RightPaneProps {
  selectedDoc: string | null;
  annotations: Annotation[];
  targetPage: number;
}

export function RightPane({ selectedDoc, annotations, targetPage }: RightPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [numPages, setNumPages] = useState<number>(0);
  const [pdfLoaded, setPdfLoaded] = useState(false);
  const [compareMode, setCompareMode] = useState(false);
  const [internalTargetPage, setInternalTargetPage] = useState<number>(targetPage);

  // PDF.js dimensions — standard US Letter at 72 DPI = 612x792 points
  const PAGE_WIDTH = 612;
  const PAGE_HEIGHT = 792;

  const pdfUrl = useMemo(
    () => selectedDoc ? api.pdfUrl(selectedDoc) : null,
    [selectedDoc]
  );

  // Sync external target page
  useEffect(() => {
    setInternalTargetPage(targetPage);
  }, [targetPage]);

  // Auto-scroll to target page
  useEffect(() => {
    if (!containerRef.current || !pdfLoaded) return;
    const pageEl = containerRef.current.querySelector(`[data-page="${internalTargetPage}"]`);
    if (pageEl) {
      pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [internalTargetPage, pdfLoaded, annotations]);

  // Detect number of pages using a simple iframe approach
  // For production, use react-pdf — this is a lightweight fallback
  useEffect(() => {
    if (!pdfUrl) {
      setPdfLoaded(false);
      setNumPages(0);
      return;
    }
    setPdfLoaded(false);
    // We'll use the embed approach for robust PDF rendering
    const timer = setTimeout(() => {
      setPdfLoaded(true);
      setNumPages(1); // iframe handles all pages internally
    }, 500);
    return () => clearTimeout(timer);
  }, [pdfUrl]);

  if (!selectedDoc) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-20 h-20 rounded-full mx-auto mb-4 flex items-center justify-center"
               style={{ background: 'var(--bg-secondary)' }}>
            <FileText className="w-8 h-8" style={{ color: 'var(--text-secondary)' }} />
          </div>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Select a document to preview
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Viewer Header */}
      <div className="h-10 flex items-center px-4 border-b"
           style={{ borderColor: 'var(--border-default)', background: 'var(--bg-secondary)' }}>
        <FileText className="w-3.5 h-3.5 mr-2" style={{ color: 'var(--text-secondary)' }} />
        <span className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
          {selectedDoc}
        </span>
        {annotations.length > 0 && (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(239, 68, 68, 0.15)', color: 'var(--accent-red)' }}>
            {annotations.length} highlight{annotations.length > 1 ? 's' : ''}
          </span>
        )}
        <button 
          onClick={() => setCompareMode(!compareMode)} 
          className="ml-4 text-[10px] font-bold uppercase tracking-wider px-2 py-1 rounded transition-colors" 
          style={{ background: compareMode ? 'var(--accent-primary)' : 'var(--bg-card)', color: compareMode ? '#fff' : 'var(--text-primary)', border: '1px solid var(--border-default)' }}>
          {compareMode ? 'Exit Compare' : 'Compare Mode'}
        </button>
      </div>

      <div className="flex-1 flex min-h-0 relative">
        {compareMode && (
          <DiffViewer 
            selectedDoc={selectedDoc} 
            onSelectDiff={setInternalTargetPage} 
            onClose={() => setCompareMode(false)} 
          />
        )}
        {/* PDF Container with overlays */}
        <div ref={containerRef} className="flex-1 overflow-auto relative"
             style={{ background: '#1a1a2e' }}>
        {pdfUrl && (
          <div className="relative w-full h-full">
            {/* PDF rendered via iframe (most reliable cross-browser) */}
            <iframe
              src={`${pdfUrl}#page=${internalTargetPage}`}
              className="w-full h-full border-none"
              title="PDF Preview"
              style={{ background: '#2a2a3e' }}
            />

            {/* Annotation overlays — rendered as floating indicators */}
            {annotations.length > 0 && (
              <div className="absolute top-2 right-2 space-y-1 z-10">
                {annotations.map((ann, i) => (
                  <div key={i} className="flex items-center gap-2 px-2 py-1 rounded-md text-xs glass"
                       style={{ color: ann.color === 'orange' ? 'var(--accent-orange)' : 'var(--accent-red)' }}>
                    <div className="w-2 h-2 rounded-full animate-pulse-dot"
                         style={{ background: ann.color === 'orange' ? 'var(--accent-orange)' : 'var(--accent-red)' }} />
                    Page {ann.page} — Highlighted
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
