'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Check, X, Pencil, Trash2, Database,
  ChevronRight, AlertCircle, Loader2,
  Fingerprint, Sparkles, Filter, MoreHorizontal,
  Save, Eye
} from 'lucide-react';
import { api } from '@/lib/api';
import dynamic from 'next/dynamic';
import { Annotation } from '@/lib/types';

const RightPane = dynamic(() => import('@/components/RightPane').then(mod => mod.RightPane), {
  ssr: false,
  loading: () => <div className="flex-1 flex flex-col items-center justify-center bg-[#1a1a2e] text-white text-xs font-mono">Loading PDF Viewer...</div>
});

interface EntityItem {
  id: number;
  file_name: string;
  category: string;
  value: string;
  confidence: number;
  selected: boolean;
}

export function SplitScreenReview({ batchId }: { batchId: string }) {
  const [items, setItems] = useState<EntityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [finalizing, setFinalizing] = useState(false);

  // PDF Viewer State
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [targetPage, setTargetPage] = useState<number | null>(1);
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    loadResults();
  }, [batchId]);

  const loadResults = async () => {
    try {
      const res = await api.getMigrationStatus(batchId);
      setItems(res.results);
      if (res.results.length > 0) {
        setSelectedDoc(res.results[0].file_name);
      }
    } catch (e) {
      console.error('Failed to load review items:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (id: number, updates: Partial<EntityItem>) => {
    const item = items.find(i => i.id === id);
    if (!item) return;
    const newItem = { ...item, ...updates };
    setItems(prev => prev.map(i => i.id === id ? newItem : i));

    try {
      await api.updateMigrationResult(id, newItem);
    } catch (e) {
      console.error('Update failed:', e);
    }
  };

  const handleLocate = async (item: EntityItem) => {
    setSelectedDoc(item.file_name);
    try {
      const res = await api.locate(item.file_name, item.value.slice(0, 50));
      if (res.found && res.annotation) {
        setAnnotations([res.annotation]);
        setTargetPage(res.page as number);
      }
    } catch (e) {
      console.error('Locate failed:', e);
    }
  };

  const handleFinalize = async () => {
    setFinalizing(true);
    try {
      const blob = await api.finalizeMigration(batchId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Migration_Export_${batchId}.sql`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (e) {
      alert('Error finalizing: ' + e);
    } finally {
      setFinalizing(false);
    }
  };

  if (loading) return (
    <div className="h-full flex flex-col items-center justify-center gap-4">
      <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      <p className="text-xs font-bold tracking-widest text-slate-400 uppercase">Indexing Migration Data...</p>
    </div>
  );

  return (
    <div className="flex h-full overflow-hidden bg-white">
      {/* Left Pane: Findings List */}
      <div className="w-[500px] border-r flex flex-col bg-[#f8fafc]">
        <div className="p-6 border-b bg-white flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Extracted Findings</h2>
            <p className="text-xs text-slate-500">{items.length} items found in batch</p>
          </div>
          <button
            onClick={handleFinalize}
            disabled={finalizing || !items.some(i => i.selected)}
            className="px-4 py-2 rounded-xl bg-blue-600 text-white text-[11px] font-bold uppercase tracking-widest hover:bg-blue-700 transition-all disabled:opacity-40"
          >
            {finalizing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Finalize & Export"}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              onClick={() => handleLocate(item)}
              className={`group p-4 rounded-2xl border transition-all cursor-pointer ${selectedDoc === item.file_name && annotations[0]?.page === targetPage ? 'border-blue-500 bg-blue-50/30' : 'border-slate-200 bg-white hover:border-blue-300'
                } ${!item.selected ? 'opacity-50 grayscale' : ''}`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-widest ${item.confidence > 0.8 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                    }`}>
                    {item.category}
                  </div>
                  <span className="text-[9px] text-slate-400 font-mono truncate max-w-[150px]">{item.file_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditingId(editingId === item.id ? null : item.id); }}
                    className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                  <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                    <div
                      onClick={() => handleUpdate(item.id, { selected: !item.selected })}
                      className={`w-10 h-5 rounded-full relative transition-colors duration-200 ${item.selected ? 'bg-blue-600' : 'bg-slate-300'}`}
                    >
                      <div className={`absolute top-1 w-3 h-3 rounded-full bg-white transition-all duration-200 ${item.selected ? 'left-6' : 'left-1'}`} />
                    </div>
                  </div>
                </div>
              </div>

              {editingId === item.id ? (
                <textarea
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                  value={item.value}
                  onChange={(e) => handleUpdate(item.id, { value: e.target.value })}
                  className="w-full bg-slate-50 border border-blue-200 rounded-lg p-2 text-sm font-medium text-slate-800 focus:ring-2 focus:ring-blue-100 outline-none resize-none min-h-[80px]"
                />
              ) : (
                <p className="text-sm font-bold text-slate-800 line-clamp-3 leading-relaxed">
                  {item.value}
                </p>
              )}

              <div className="mt-3 flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> Click to view source</span>
                <span>{Math.round(item.confidence * 100)}% Confidence</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Right Pane: PDF Viewer */}
      <div className="flex-1 bg-slate-100 flex flex-col relative">
        <RightPane
          selectedDoc={selectedDoc}
          annotations={annotations}
          targetPage={targetPage}
        />
      </div>
    </div>
  );
}
