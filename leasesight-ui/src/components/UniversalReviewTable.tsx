'use client';

import { useState, useEffect } from 'react';
import { 
  Check, X, Trash2, Save, Download, 
  Database, FileJson, Table as TableIcon,
  ChevronRight, AlertCircle, Loader2,
  Fingerprint, Sparkles, Filter, MoreHorizontal
} from 'lucide-react';
import { api } from '@/lib/api';

interface EntityItem {
  id: number;
  file_name: string;
  category: string;
  value: string;
  confidence: number;
  selected: boolean;
}

export function UniversalReviewTable({ batchId }: { batchId: string }) {
  const [items, setItems] = useState<EntityItem[]>([]);
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

  const handleUpdate = async (id: number, updates: Partial<EntityItem>) => {
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
      a.download = `Universal_Migration_${batchId}.sql`;
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
    <div className="flex flex-col items-center justify-center py-40 gap-4">
      <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
      </div>
      <p className="text-xs font-bold tracking-[0.2em] text-slate-400 uppercase">Analyzing Entities...</p>
    </div>
  );

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Control Strip */}
      <div className="bg-white rounded-[2rem] border border-slate-200 p-6 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-3">
            <input 
              type="checkbox" 
              className="accent-blue-600 w-5 h-5 rounded-lg" 
              checked={items.length > 0 && items.every(i => i.selected)}
              onChange={(e) => setItems(items.map(i => ({ ...i, selected: e.target.checked })))}
            />
            <span className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Select All Entities</span>
          </div>
          
          <div className="h-6 w-px bg-slate-100" />
          
          <button 
            onClick={() => setItems(items.filter(i => !i.selected))}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-red-500 hover:bg-red-50 transition-colors text-[11px] font-black uppercase tracking-tight"
          >
            <Trash2 className="w-4 h-4" /> Discard Selected
          </button>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden lg:flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-50 text-[11px] font-bold text-slate-400 uppercase">
            <Sparkles className="w-3.5 h-3.5" /> Proof-Chain Verified
          </div>
          <button 
            onClick={handleFinalize}
            disabled={finalizing || !items.some(i => i.selected)}
            className="flex items-center gap-3 px-10 py-4 rounded-2xl bg-[#0f172a] text-white font-bold text-sm hover:scale-[1.02] active:scale-[0.98] transition-all shadow-2xl shadow-slate-300 disabled:opacity-40"
          >
            {finalizing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Database className="w-4 h-4" />}
            Confirm & Export SQL
          </button>
        </div>
      </div>

      {/* Entity Grid Table */}
      <div className="bg-white rounded-[2.5rem] border border-slate-200 shadow-2xl shadow-slate-200/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1000px]">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-100">
                <th className="px-10 py-6 w-20"></th>
                <th className="px-10 py-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Entity Category</th>
                <th className="px-10 py-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Extracted Value (Editable)</th>
                <th className="px-10 py-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] w-48">Confidence</th>
                <th className="px-10 py-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] w-20 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {items.map((item) => (
                <tr key={item.id} className={`group transition-all ${!item.selected ? 'opacity-30' : 'hover:bg-slate-50/20'}`}>
                  <td className="px-10 py-6 text-center">
                    <input 
                      type="checkbox" 
                      checked={item.selected}
                      onChange={(e) => handleUpdate(item.id, { selected: e.target.checked })}
                      className="accent-blue-600 w-5 h-5 rounded-lg cursor-pointer"
                    />
                  </td>
                  
                  {/* Category */}
                  <td className="px-10 py-6">
                    <div className="flex flex-col gap-1">
                      <span className="text-[10px] font-mono text-slate-300 uppercase truncate mb-1">Source: {item.file_name}</span>
                      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-lg bg-blue-50 border border-blue-100/50 w-fit">
                        <Fingerprint className="w-3 h-3 text-blue-400" />
                        <span className="text-[11px] font-bold text-blue-700 uppercase tracking-tighter">{item.category}</span>
                      </div>
                    </div>
                  </td>

                  {/* Editable Value */}
                  <td className="px-10 py-6">
                    <textarea 
                      value={item.value}
                      onChange={(e) => handleUpdate(item.id, { value: e.target.value })}
                      className="w-full bg-transparent border-none focus:ring-2 focus:ring-blue-100 rounded-xl p-3 text-sm font-bold text-slate-800 outline-none resize-none min-h-[60px] transition-all hover:bg-slate-50/50"
                    />
                  </td>

                  {/* Confidence Score */}
                  <td className="px-10 py-6">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-[10px] font-bold">
                        <span className="text-slate-400 uppercase">AI Reliability</span>
                        <span className={item.confidence > 0.8 ? 'text-emerald-500' : 'text-amber-500'}>
                          {Math.round(item.confidence * 100)}%
                        </span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div 
                          className={`h-full transition-all duration-1000 ${item.confidence > 0.8 ? 'bg-emerald-400' : 'bg-amber-400'}`}
                          style={{ width: `${item.confidence * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>

                  {/* Status Indicator */}
                  <td className="px-10 py-6 text-center">
                    {savingId === item.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-400 mx-auto" />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-slate-50 flex items-center justify-center mx-auto text-slate-300 group-hover:text-emerald-400 transition-colors">
                        <Check className="w-4 h-4" />
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
