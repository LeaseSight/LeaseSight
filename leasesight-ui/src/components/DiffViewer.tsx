'use client';

import { useState, useEffect } from 'react';
import { FileDiff, ChevronDown } from 'lucide-react';
import { api } from '@/lib/api';

interface DiffViewerProps {
  selectedDoc: string;
  onSelectDiff: (page: number) => void;
  onClose: () => void;
}

interface DiffItem {
  page: number;
  text: string;
  color: string;
}

export function DiffViewer({ selectedDoc, onSelectDiff, onClose }: DiffViewerProps) {
  const [documents, setDocuments] = useState<string[]>([]);
  const [baseline, setBaseline] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [diffs, setDiffs] = useState<{ additions: DiffItem[], deletions: DiffItem[] } | null>(null);

  useEffect(() => {
    api.documents().then(d => setDocuments(d.documents)).catch(console.error);
  }, []);

  const handleCompare = async () => {
    if (!baseline || baseline === selectedDoc) return;
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/diff', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseline_file: baseline, target_file: selectedDoc })
      });
      const data = await res.json();
      setDiffs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-80 border-r flex flex-col" style={{ borderColor: 'var(--border-default)', background: 'var(--bg-secondary)' }}>
      <div className="p-4 border-b" style={{ borderColor: 'var(--border-default)' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
            <FileDiff className="w-3.5 h-3.5" />
            Compare Mode
          </h3>
          <button onClick={onClose} className="text-xs hover:underline" style={{ color: 'var(--text-secondary)' }}>Close</button>
        </div>
        
        <label className="text-xs mb-1 block" style={{ color: 'var(--text-secondary)' }}>Baseline Document</label>
        <div className="relative mb-2">
          <select 
            value={baseline} 
            onChange={e => setBaseline(e.target.value)}
            className="w-full appearance-none rounded px-2 py-1.5 pr-6 text-xs outline-none"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
          >
            <option value="">Select baseline...</option>
            {documents.filter(d => d !== selectedDoc).map(d => (
              <option key={d} value={d}>{d.length > 30 ? d.slice(0, 30) + '...' : d}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none" style={{ color: 'var(--text-secondary)' }} />
        </div>
        
        <button 
          onClick={handleCompare}
          disabled={!baseline || loading}
          className="w-full py-1.5 rounded text-xs font-semibold disabled:opacity-50"
          style={{ background: 'var(--accent-primary)', color: '#fff' }}
        >
          {loading ? 'Comparing...' : 'Run Diff'}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!diffs ? (
          <p className="text-xs text-center mt-4" style={{ color: 'var(--text-secondary)' }}>Select a baseline document to see changes.</p>
        ) : (
          <>
            <div>
              <h4 className="text-[10px] font-bold uppercase mb-2" style={{ color: '#ef4444' }}>Deletions ({diffs.deletions.length})</h4>
              <div className="space-y-1.5">
                {diffs.deletions.map((d, i) => (
                  <div key={`del-${i}`} onClick={() => onSelectDiff(d.page)}
                       className="text-[10px] p-2 rounded cursor-pointer hover:opacity-80 transition-opacity"
                       style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#991b1b', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
                    <span className="font-bold mr-1">Pg {d.page}:</span>
                    {d.text.length > 80 ? d.text.slice(0, 80) + '...' : d.text}
                  </div>
                ))}
                {diffs.deletions.length === 0 && <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>No deletions.</p>}
              </div>
            </div>

            <div>
              <h4 className="text-[10px] font-bold uppercase mb-2" style={{ color: '#10b981' }}>Additions ({diffs.additions.length})</h4>
              <div className="space-y-1.5">
                {diffs.additions.map((a, i) => (
                  <div key={`add-${i}`} onClick={() => onSelectDiff(a.page)}
                       className="text-[10px] p-2 rounded cursor-pointer hover:opacity-80 transition-opacity"
                       style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#065f46', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
                    <span className="font-bold mr-1">Pg {a.page}:</span>
                    {a.text.length > 80 ? a.text.slice(0, 80) + '...' : a.text}
                  </div>
                ))}
                {diffs.additions.length === 0 && <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>No additions.</p>}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
