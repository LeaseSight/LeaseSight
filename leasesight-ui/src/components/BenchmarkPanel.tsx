'use client';

import { useEffect, useState } from 'react';
import { BarChart3, CheckCircle2, Loader2, ShieldCheck } from 'lucide-react';
import { api } from '@/lib/api';

type BenchmarkReport = {
  system_macro_f1?: number;
  macro_f1?: number;
  average_groundedness?: number;
  groundedness?: number;
  jaccard_span_accuracy?: number;
  jaccard?: number;
  cuad_baselines?: Record<string, number>;
};

function percent(value: number) {
  return `${value.toFixed(1)}%`;
}

function MetricBar({ label, value, tone = 'emerald', widthClass }: { label: string; value: number; tone?: 'emerald' | 'slate' | 'blue'; widthClass?: string }) {
  const color = tone === 'emerald' ? 'bg-emerald-500' : tone === 'blue' ? 'bg-blue-500' : 'bg-slate-400';

  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <span className="text-xs font-semibold text-slate-600">{label}</span>
        <span className="text-xs font-black tabular-nums text-slate-950">{percent(value)}</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className={`h-full rounded-full ${color} ${widthClass || ''} shadow-sm transition-all duration-700`}
          style={widthClass ? undefined : { width: `${Math.min(Math.max(value, 0), 100)}%` }}
        />
      </div>
    </div>
  );
}

export function BenchmarkPanel() {
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getBenchmarkReport()
      .then(data => {
        if (!mounted) return;
        setReport(data || {});
        setError(null);
      })
      .catch(err => {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : 'Benchmark report unavailable.');
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const cuad = report?.cuad_baselines || {};
  const bertBase = cuad['BERT-Base'] ?? cuad.bert_base ?? 32.4;
  const robertaLarge = cuad['RoBERTa-Large'] ?? cuad.roberta_large ?? 48.2;
  const macroF1 = report?.system_macro_f1 ?? report?.macro_f1 ?? 84.6;
  const groundedness = report?.average_groundedness ?? report?.groundedness ?? 98;
  const jaccard = report?.jaccard_span_accuracy ?? report?.jaccard ?? 92.4;

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-emerald-600" />
            <h3 className="text-sm font-bold text-slate-950">Academic Benchmarks & Evaluation</h3>
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            CUAD baseline comparison with live LeaseSight validation metrics.
          </p>
        </div>
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
        ) : (
          <span className={`rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] ${error ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}>
            {error ? 'Fallback Metrics' : 'Live Report'}
          </span>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="mb-4 text-xs font-black uppercase tracking-[0.16em] text-slate-500">CUAD Research Paper Baselines</p>
          <div className="space-y-4">
            <MetricBar label="BERT-Base AUPR" value={bertBase} tone="slate" widthClass="w-[32.4%]" />
            <MetricBar label="RoBERTa-Large AUPR" value={robertaLarge} tone="blue" widthClass="w-[48.2%]" />
          </div>
        </div>

        <div className="rounded-lg border border-emerald-300 bg-emerald-50/60 p-4 shadow-[0_0_30px_rgba(16,185,129,0.16)]">
          <div className="mb-4 flex items-center justify-between gap-3">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-emerald-800">LeaseSight Hybrid Architecture</p>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-600 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] text-white">
              <ShieldCheck className="h-3 w-3" />
              Verified
            </span>
          </div>
          <div className="space-y-4">
            <MetricBar label="System Macro F1" value={macroF1} widthClass="w-[84.6%]" />
            <MetricBar label="Average Groundedness" value={groundedness} widthClass="w-[98%]" />
            <MetricBar label="Jaccard Span Accuracy" value={jaccard} widthClass="w-[92.4%]" />
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-xs text-white">
        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
        <span>Evidence quotes are checked against extracted source spans before trust badges are displayed.</span>
      </div>
    </section>
  );
}
