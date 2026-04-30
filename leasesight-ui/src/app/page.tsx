'use client';

import { useState, useCallback } from 'react';
import { Header } from '@/components/Header';
import { LeftPane } from '@/components/LeftPane';
import { RightPane } from '@/components/RightPane';
import { ChatOverlay } from '@/components/ChatOverlay';
import { NetworkPanel } from '@/components/NetworkPanel';
import { AuditResult, Annotation } from '@/lib/types';

export default function Home() {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [targetPage, setTargetPage] = useState<number>(1);
  const [isAuditing, setIsAuditing] = useState(false);
  const [showNetwork, setShowNetwork] = useState(false);
  const [isCommitted, setIsCommitted] = useState(false);

  const handleLocate = useCallback((annotation: Annotation) => {
    setAnnotations([annotation]);
    setTargetPage(annotation.page);
  }, []);

  const handleAuditComplete = useCallback((result: AuditResult) => {
    setAuditResult(result);
    setAnnotations(result.annotations || []);
    setIsAuditing(false);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
      {/* Global Header */}
      <Header
        isAuditing={isAuditing}
        onToggleNetwork={() => setShowNetwork(!showNetwork)}
      />

      {/* Dual-Pane Workstation */}
      <div className="flex-1 flex min-h-0">
        {/* Left Pane — Auditor */}
        <div className="w-[480px] min-w-[400px] flex flex-col border-r"
             style={{ borderColor: 'var(--border-default)', background: 'var(--bg-secondary)' }}>
          <LeftPane
            selectedDoc={selectedDoc}
            onSelectDoc={setSelectedDoc}
            auditResult={auditResult}
            onAuditStart={() => setIsAuditing(true)}
            onAuditComplete={handleAuditComplete}
            onLocate={handleLocate}
            onCommitChange={setIsCommitted}
          />
        </div>

        {/* Right Pane — Viewer */}
        <div className="flex-1 flex flex-col min-w-0" style={{ background: 'var(--bg-primary)' }}>
          <RightPane
            selectedDoc={selectedDoc}
            annotations={annotations}
            targetPage={targetPage}
          />
        </div>
      </div>

      {/* Bottom Network Panel (retractable) */}
      {showNetwork && selectedDoc && (
        <NetworkPanel
          selectedDoc={selectedDoc}
          onClose={() => setShowNetwork(false)}
          isCommitted={isCommitted}
        />
      )}

      {/* Chat Overlay */}
      {selectedDoc && (
        <ChatOverlay
          selectedDoc={selectedDoc}
          onLocate={handleLocate}
        />
      )}
    </div>
  );
}
