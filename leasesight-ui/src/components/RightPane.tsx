'use client';

import { useEffect, useRef, useState, useMemo } from 'react';
import { FileText } from 'lucide-react';
import { Annotation } from '@/lib/types';
import { api } from '@/lib/api';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Configure PDF.js worker to use the local bundle
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface RightPaneProps {
  selectedDoc: string | null;
  annotations: Annotation[];
  targetPage: number;
}

export function RightPane({ selectedDoc, annotations, targetPage }: RightPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [internalTargetPage, setInternalTargetPage] = useState<number>(targetPage);
  const [containerWidth, setContainerWidth] = useState<number>(0);

  const pdfUrl = useMemo(
    () => selectedDoc ? api.pdfUrl(selectedDoc) : null,
    [selectedDoc]
  );

  // Sync external target page
  useEffect(() => {
    setInternalTargetPage(targetPage);
  }, [targetPage]);

  // Resize observer for page-specific scaling
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        // Leave some padding
        setContainerWidth(entries[0].contentRect.width - 32); 
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

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
      </div>

      {/* PDF Container */}
      <div 
        ref={containerRef} 
        className="flex-1 overflow-y-auto relative max-h-[800px] p-4 flex justify-center"
        style={{ background: '#1a1a2e' }}
      >
        {pdfUrl && containerWidth > 0 && (
          <div className="relative shadow-xl" style={{ width: containerWidth }}>
            <Document 
              file={pdfUrl} 
              onLoadError={(error) => console.error('Error while loading document!', error)}
              loading={<div className="text-white text-sm text-center p-10">Loading PDF engine...</div>}
              error={<div className="text-red-500 text-sm text-center p-10 bg-red-500/10 rounded-lg">Failed to load PDF. Check network console.</div>}
            >
              <Page 
                pageNumber={internalTargetPage} 
                width={containerWidth} 
                renderTextLayer={false} 
                renderAnnotationLayer={false} 
              />
              
              {/* Active Highlighting Overlays */}
              {annotations.filter(a => a.page === internalTargetPage).map((ann, i) => {
                // Formula: Pixel_X = (Inches_X / Page_Width_Inches) * Container_Width_Pixels
                const PAGE_WIDTH_INCHES = 8.5;
                const PAGE_HEIGHT_INCHES = 11.0;
                
                const pxX = (ann.x / PAGE_WIDTH_INCHES) * containerWidth;
                const pxY = (ann.y / PAGE_HEIGHT_INCHES) * (containerWidth * (PAGE_HEIGHT_INCHES / PAGE_WIDTH_INCHES));
                const pxW = (ann.width / PAGE_WIDTH_INCHES) * containerWidth;
                const pxH = (ann.height / PAGE_HEIGHT_INCHES) * (containerWidth * (PAGE_HEIGHT_INCHES / PAGE_WIDTH_INCHES));
                
                return (
                  <div 
                    key={i}
                    className="absolute z-10 pointer-events-none rounded-sm transition-all duration-500 animate-pulse"
                    style={{
                      left: `${pxX}px`,
                      top: `${pxY}px`,
                      width: `${pxW}px`,
                      height: `${pxH}px`,
                      backgroundColor: 'rgba(239, 68, 68, 0.3)',
                      border: '1.5px solid rgba(239, 68, 68, 0.8)',
                      boxShadow: '0 0 10px rgba(239, 68, 68, 0.4)'
                    }}
                  />
                );
              })}
            </Document>
          </div>
        )}
      </div>
    </div>
  );
}
