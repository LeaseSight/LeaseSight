'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, Play, AlertTriangle, CheckCircle, Database } from 'lucide-react';
import { api } from '@/lib/api';
import { AuditResult, Annotation } from '@/lib/types';
import { RiskGauge } from './RiskGauge';
import { FindingCard } from './FindingCard';
import { CommitModal } from './CommitModal';

interface LeftPaneProps {
  selectedDoc: string | null;
  onSelectDoc: (doc: string) => void;
  auditResult: AuditResult | null;
  onAuditStart: () => void;
  onAuditComplete: (result: AuditResult) => void;
  onLocate: (annotation: Annotation) => void;
  onCommitChange?: (committed: boolean) => void;
}

export function LeftPane({
  selectedDoc, onSelectDoc, auditResult,
  onAuditStart, onAuditComplete, onLocate, onCommitChange
}: LeftPaneProps) {
  const [documents, setDocuments] = useState<string[]>([]);
  const [isAuditing, setIsAuditing] = useState(false);
  const [showCommitModal, setShowCommitModal] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [committed, setCommitted] = useState(false);

  useEffect(() => {
    api.documents().then(d => setDocuments(d.documents)).catch(() => {});
  }, []);

  const handleRunAudit = async () => {
    if (!selectedDoc) return;
    setIsAuditing(true);
    setCommitted(false);
    onCommitChange?.(false);
    onAuditStart();
    try {
      const result = await api.audit(selectedDoc);
      onAuditComplete(result);
    } catch (e) {
      console.error('Audit failed:', e);
    } finally {
      setIsAuditing(false);
    }
  };

  const handleLocateSnippet = async (snippet: string) => {
    if (!selectedDoc) return;
    try {
      const res = await api.locate(selectedDoc, snippet);
      if (res.found && res.annotation) {
        onLocate(res.annotation);
      }
    } catch (e) {
      console.error('Locate failed:', e);
    }
  };

  const handleCommit = async () => {
    if (!selectedDoc) return;
    setIsCommitting(true);
    try {
      const result = await api.commit(selectedDoc);
      if (result.success) {
        setCommitted(true);
        onCommitChange?.(true);
        setShowCommitModal(false);
      }
    } catch (e) {
      console.error('Commit failed:', e);
    } finally {
      setIsCommitting(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Document Selector */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--border-default)' }}>
        <label className="text-xs font-medium mb-1.5 block" style={{ color: 'var(--text-secondary)' }}>
          Document
        </label>
        <div className="relative">
          <select
            value={selectedDoc || ''}
            onChange={e => onSelectDoc(e.target.value)}
            className="w-full appearance-none rounded-lg px-3 py-2 pr-8 text-sm outline-none cursor-pointer"
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-default)',
            }}
          >
            <option value="">Select a document...</option>
            {documents.map(d => (
              <option key={d} value={d}>{d.length > 50 ? d.slice(0, 50) + '...' : d}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none"
                       style={{ color: 'var(--text-secondary)' }} />
        </div>

        {/* Run Audit Button */}
        <button
          onClick={handleRunAudit}
          disabled={!selectedDoc || isAuditing}
          className="w-full mt-3 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: isAuditing ? 'var(--bg-card)' : 'var(--accent-primary)',
            color: isAuditing ? 'var(--accent-primary)' : '#ffffff',
            border: isAuditing ? '1px solid var(--accent-primary)' : 'none',
          }}
        >
          {isAuditing ? (
            <>
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              Running Pipeline...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Intelligent Audit
            </>
          )}
        </button>
      </div>

      {/* Scrollable Results Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {auditResult ? (
          <>
            {/* Success Box */}
            <div className="rounded-lg p-3 flex flex-col gap-1"
                 style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534' }}>
              <span className="text-sm font-semibold">✨ Look what we found</span>
              <span className="text-xs">We processed the lease document and extracted key information. Please review for accuracy.</span>
            </div>

            {/* Risk Gauge + Warnings */}
            <div className="flex items-start gap-4">
              <RiskGauge score={auditResult.risk_score || 1} />
              <div className="flex-1 space-y-1.5">
                {auditResult.warnings?.length > 0 ? (
                  auditResult.warnings.map((w, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs rounded-md p-2"
                         style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--accent-red)' }}>
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                      <span>{w}</span>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center gap-2 text-xs rounded-md p-2"
                       style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-emerald)' }}>
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>No issues detected</span>
                  </div>
                )}
              </div>
            </div>

            {/* Findings */}
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider mb-2"
                  style={{ color: 'var(--text-secondary)' }}>
                Key Findings
              </h3>
              <div className="space-y-2">
                {auditResult.findings.map((f, i) => (
                  <FindingCard key={i} finding={f} index={i} onLocate={handleLocateSnippet} />
                ))}
              </div>
            </div>

            {/* Executive Brief */}
            {auditResult.summary_paragraph && (
              <div className="rounded-lg p-3"
                   style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
                <h4 className="text-xs font-semibold uppercase tracking-wider mb-2"
                    style={{ color: 'var(--text-secondary)' }}>
                  Executive Brief
                </h4>
                <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                  {auditResult.summary_paragraph}
                </p>
              </div>
            )}

            {/* Commit Button */}
            <div className="pt-2">
              {committed ? (
                <div className="flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm"
                     style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-emerald)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                  <CheckCircle className="w-4 h-4" />
                  Committed as Legal Precedent
                </div>
              ) : (
                <button onClick={() => setShowCommitModal(true)}
                        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold glow-primary transition-all"
                        style={{ background: 'var(--accent-primary)', color: '#ffffff' }}>
                  <Database className="w-4 h-4" />
                  Commit to Knowledge Base
                </button>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-center py-20">
            <div>
              <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center"
                   style={{ background: 'var(--bg-card)' }}>
                <Play className="w-6 h-6" style={{ color: 'var(--text-secondary)' }} />
              </div>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Select a document and run an audit to see results
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Commit Modal */}
      {showCommitModal && (
        <CommitModal
          onConfirm={handleCommit}
          onCancel={() => setShowCommitModal(false)}
          isCommitting={isCommitting}
        />
      )}
    </div>
  );
}
