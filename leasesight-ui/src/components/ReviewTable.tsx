'use client';

import { useState, useEffect } from 'react';
import { 
  Check, X, Trash2, Save, Download, 
  Database, FileJson, Table as TableIcon,
  ChevronRight, AlertCircle, Loader2
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

export function ReviewTable({ batchId }: { batchId: string }) {
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
    
    try {
      await api.updateMigrationResult(id, newItem);
      setItems(items.map(i => i.id === id ? newItem : i));
    } catch (e) {
      console.error('Update failed:', e);
    } finally {
      setSavingId(null);
    }
  };

  const handleToggleAll = (val: boolean) => {
    const newItems = items.map(i => ({ ...i, selected: val }));
    setItems(newItems);
    // In a real app, you'd batch update the backend here
  };

  const handleDeleteSelected = () => {
    setItems(items.filter(i => !i.selected));
    // In a real app, send delete requests to backend
  };

  const handleFinalize = async () => {
    setFinalizing(true);
    try {
      const blob = await api.finalizeMigration(batchId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Finalized_Migration_${batchId}.sql`;
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
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      <p className="text-sm font-medium text-slate-500">Loading records for review...</p>
    </div>
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Action Bar */}
      <div className="bg-white rounded-2xl border p-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 px-3 py-1.5 rounded-lg border hover:bg-slate-50 cursor-pointer transition-colors">
            <input 
              type="checkbox" 
              className="accent-blue-600" 
              checked={items.every(i => i.selected)}
              onChange={(e) => handleToggleAll(e.target.checked)}
            />
            <span className="text-xs font-bold text-slate-600 uppercase">Select All</span>
          </label>
          
          <button 
            onClick={handleDeleteSelected}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-red-600 hover:bg-red-50 transition-colors text-xs font-bold uppercase"
          >
            <Trash2 className="w-3.5 h-3.5" /> Discard Selected
          </button>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={handleFinalize}
            disabled={finalizing || !items.some(i => i.selected)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-900 text-white font-bold text-xs uppercase hover:bg-slate-800 transition-all disabled:opacity-40"
          >
            {finalizing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Database className="w-3.5 h-3.5" />}
            Finalize & Generate SQL
          </button>
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-white rounded-2xl border shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1000px]">
            <thead>
              <tr className="bg-slate-50 border-b">
                <th className="px-6 py-4 w-12"></th>
                <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase">Document Info</th>
                <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase">Extracted Metadata (Editable)</th>
                <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase">Summary</th>
                <th className="px-6 py-4 text-[10px] font-bold text-slate-400 uppercase w-20">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item) => (
                <tr key={item.id} className={`group hover:bg-slate-50/50 transition-colors ${!item.selected ? 'opacity-50' : ''}`}>
                  <td className="px-6 py-4 text-center">
                    <input 
                      type="checkbox" 
                      checked={item.selected}
                      onChange={(e) => handleUpdate(item.id, { selected: e.target.checked })}
                      className="accent-blue-600 w-4 h-4 cursor-pointer"
                    />
                  </td>
                  <td className="px-6 py-4 max-w-xs">
                    <div className="flex items-center gap-2 mb-1">
                      <FileJson className="w-3.5 h-3.5 text-slate-400" />
                      <span className="text-[10px] font-mono text-slate-400 truncate">{item.file_name}</span>
                    </div>
                    <input 
                      value={item.title}
                      onChange={(e) => handleUpdate(item.id, { title: e.target.value })}
                      className="w-full bg-transparent border-none focus:ring-1 focus:ring-blue-100 rounded p-1 text-sm font-bold text-slate-900 outline-none"
                    />
                  </td>
                  <td className="px-6 py-4 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-slate-400 w-16 uppercase">Authors:</span>
                      <input 
                        value={item.authors}
                        onChange={(e) => handleUpdate(item.id, { authors: e.target.value })}
                        className="flex-1 bg-transparent border-none focus:ring-1 focus:ring-blue-100 rounded p-1 text-xs text-slate-600 outline-none"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold text-slate-400 w-16 uppercase">Date:</span>
                      <input 
                        value={item.date}
                        onChange={(e) => handleUpdate(item.id, { date: e.target.value })}
                        className="flex-1 bg-transparent border-none focus:ring-1 focus:ring-blue-100 rounded p-1 text-xs font-mono text-blue-600 outline-none"
                      />
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <textarea 
                      value={item.summary}
                      onChange={(e) => handleUpdate(item.id, { summary: e.target.value })}
                      className="w-full bg-transparent border-none focus:ring-1 focus:ring-blue-100 rounded p-1 text-xs text-slate-500 leading-relaxed outline-none resize-none h-16"
                    />
                  </td>
                  <td className="px-6 py-4 text-center">
                    {savingId === item.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-400 mx-auto" />
                    ) : (
                      <Check className="w-4 h-4 text-emerald-400 mx-auto" />
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
