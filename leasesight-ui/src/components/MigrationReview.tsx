'use client';

import { useState, useEffect } from 'react';
import { 
  Check, X, Trash2, Save, Download, 
  Database, FileJson, Table as TableIcon,
  ChevronRight, AlertCircle, Loader2,
  FileText, User, Calendar, Quote, Hash, Tag
} from 'lucide-react';
import { api } from '@/lib/api';

interface ReviewItem {
  id: number;
  file_name: string;
  title: string;
  authors: string;
  date: string;
  summary: string;
  citations: string;
  tags: string;
  selected: boolean;
}

export function MigrationReview({ batchId }: { batchId: string }) {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [finalizing, setFinalizing] = useState(false);

  useEffect(() => {
    loadResults();
  }, [batchId]);

  const loadResults = async () => {
    try {
      const res = await api.getMigrationStatus(batchId);
      setItems(res.results);
    } catch (e) {
      console.error('Failed to load review items:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (id: number, updates: Partial<ReviewItem>) => {
    setSavingId(id);
    const item = items.find(i => i.id === id);
    if (!item) return;
    const newItem = { ...item, ...updates };
    
    // Optimistic local update
    setItems(prev => prev.map(i => i.id === id ? newItem : i));

    try {
      await api.updateMigrationResult(id, newItem);
    } catch (e) {
      console.error('Update failed:', e);
    } finally {
      setSavingId(null);
    }
  };

  const handleFinalize = async () => {
    setFinalizing(true);
    try {
      const blob = await api.finalizeMigration(batchId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LeaseSight_Final_Export_${batchId}.sql`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (e) {
      alert('Error finalizing migration: ' + e);
    } finally {
      setFinalizing(false);
    }
  };

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-40 gap-4">
      <Loader2 className="w-10 h-10 animate-spin text-blue-500" />
      <p className="text-sm font-mono tracking-widest text-slate-400 uppercase">Indexing Records...</p>
    </div>
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Control Panel */}
      <div className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3 px-4 py-2 bg-slate-50 rounded-2xl border border-slate-100">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Selected</span>
            <span className="text-sm font-bold text-slate-900">{items.filter(i => i.selected).length} / {items.length}</span>
          </div>
          
          <button 
            onClick={() => setItems(items.filter(i => !i.selected))}
            className="flex items-center gap-2 px-4 py-2 rounded-2xl text-red-500 hover:bg-red-50 transition-colors text-xs font-bold uppercase tracking-tight"
          >
            <Trash2 className="w-3.5 h-3.5" /> Discard Unticked
          </button>
        </div>

        <button 
          onClick={handleFinalize}
          disabled={finalizing || !items.some(i => i.selected)}
          className="flex items-center gap-3 px-8 py-3 rounded-2xl bg-slate-900 text-white font-bold text-sm hover:bg-slate-800 transition-all shadow-xl shadow-slate-200 disabled:opacity-40"
        >
          {finalizing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
          Verify & Export to SQL
        </button>
      </div>

      {/* Main Review Table */}
      <div className="bg-white rounded-[2rem] border border-slate-200 shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1200px]">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                <th className="px-8 py-5 w-12">
                  <input 
                    type="checkbox" 
                    className="accent-blue-600 rounded" 
                    checked={items.length > 0 && items.every(i => i.selected)}
                    onChange={(e) => setItems(items.map(i => ({ ...i, selected: e.target.checked })))}
                  />
                </th>
                <th className="px-8 py-5 text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Title & Source</th>
                <th className="px-8 py-5 text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Metadata</th>
                <th className="px-8 py-5 text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em]">Summary / Abstract</th>
                <th className="px-8 py-5 text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] w-32">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {items.map((item) => (
                <tr key={item.id} className={`group transition-all ${!item.selected ? 'opacity-40 grayscale' : 'hover:bg-slate-50/30'}`}>
                  <td className="px-8 py-6 text-center align-top">
                    <input 
                      type="checkbox" 
                      checked={item.selected}
                      onChange={(e) => handleUpdate(item.id, { selected: e.target.checked })}
                      className="accent-blue-600 w-4 h-4 cursor-pointer"
                    />
                  </td>
                  
                  {/* Title & Source */}
                  <td className="px-8 py-6 max-w-sm align-top">
                    <div className="flex items-center gap-2 mb-2 text-[10px] font-mono text-slate-400">
                      <FileText className="w-3 h-3" />
                      <span className="truncate">{item.file_name}</span>
                    </div>
                    <textarea 
                      value={item.title}
                      onChange={(e) => handleUpdate(item.id, { title: e.target.value })}
                      className="w-full bg-transparent border-none focus:ring-2 focus:ring-blue-100 rounded-lg p-2 text-sm font-bold text-slate-900 outline-none resize-none transition-all h-20"
                    />
                  </td>

                  {/* Metadata fields */}
                  <td className="px-8 py-6 space-y-3 align-top min-w-[280px]">
                    <div className="flex items-center gap-3">
                      <User className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                      <input 
                        value={item.authors}
                        onChange={(e) => handleUpdate(item.id, { authors: e.target.value })}
                        className="w-full bg-transparent border-none focus:ring-1 focus:ring-blue-100 rounded p-1 text-xs text-slate-600 outline-none font-medium"
                        placeholder="Authors / Parties"
                      />
                    </div>
                    <div className="flex items-center gap-3">
                      <Calendar className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                      <input 
                        value={item.date}
                        onChange={(e) => handleUpdate(item.id, { date: e.target.value })}
                        className="w-full bg-transparent border-none focus:ring-1 focus:ring-blue-100 rounded p-1 text-xs font-mono text-blue-500 outline-none"
                        placeholder="Pub Date (ISO)"
                      />
                    </div>
                    <div className="flex items-center gap-3">
                      <Quote className="w-3.5 h-3.5 text-slate-300 shrink-0" />
                      <input 
                        value={item.citations}
                        onChange={(e) => handleUpdate(item.id, { citations: e.target.value })}
                        className="w-full bg-transparent border-none focus:ring-1 focus:ring-blue-100 rounded p-1 text-xs font-mono text-slate-500 outline-none"
                        placeholder="Citation Count"
                      />
                    </div>
                  </td>

                  {/* Summary / Tags */}
                  <td className="px-8 py-6 align-top">
                    <textarea 
                      value={item.summary}
                      onChange={(e) => handleUpdate(item.id, { summary: e.target.value })}
                      className="w-full bg-transparent border-none focus:ring-2 focus:ring-blue-100 rounded-lg p-2 text-xs text-slate-500 leading-relaxed outline-none resize-none h-24 mb-2"
                      placeholder="Summary / Abstract..."
                    />
                    <div className="flex flex-wrap gap-1.5">
                      {JSON.parse(item.tags || '[]').map((tag: string, idx: number) => (
                        <span key={idx} className="px-2 py-0.5 rounded bg-slate-100 text-[9px] font-bold text-slate-400 uppercase tracking-tighter">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </td>

                  {/* Status Indicator */}
                  <td className="px-8 py-6 text-center align-top">
                    {savingId === item.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-400 mx-auto" />
                    ) : (
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center">
                          <Check className="w-4 h-4 text-emerald-500" />
                        </div>
                        <span className="text-[9px] font-bold text-emerald-500 uppercase">Verified</span>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
