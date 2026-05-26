'use client';

import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, BarChart3, Loader2, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import { EvaluationSummary, FailedCase } from '@/lib/types';

function percent(value: number | undefined) {
  return Math.max(0, Math.min(100, Math.round((value ?? 0) * 100)));
}

function MetricBar({
  label,
  leasesight,
  baseline,
}: {
  label: string;
  leasesight: number;
  baseline: number;
}) {
  const leasesightPct = percent(leasesight);
  const baselinePct = percent(baseline);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-4">
        <span className="text-sm font-bold text-slate-800">{label}</span>
        <span className="text-xs font-semibold text-slate-500">
          {leasesightPct}% vs {baselinePct}%
        </span>
      </div>
      <div className="space-y-2">
        <div className="grid grid-cols-[96px_1fr_48px] items-center gap-3">
          <span className="text-xs font-semibold text-emerald-700">LeaseSight</span>
          <div className="h-3 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-emerald-500" style={{ width: `${leasesightPct}%` }} />
          </div>
          <span className="text-xs font-bold text-slate-700">{leasesightPct}%</span>
        </div>
        <div className="grid grid-cols-[96px_1fr_48px] items-center gap-3">
          <span className="text-xs font-semibold text-slate-500">Baseline</span>
          <div className="h-3 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-slate-400" style={{ width: `${baselinePct}%` }} />
          </div>
          <span className="text-xs font-bold text-slate-500">{baselinePct}%</span>
        </div>
      </div>
    </div>
  );
}

function FailureRow({ failure }: { failure: FailedCase }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-sm font-bold text-slate-900">{failure.user_query}</p>
        <span className="shrink-0 rounded-md bg-amber-50 px-2 py-1 text-[10px] font-black uppercase tracking-widest text-amber-700">
          {failure.failure_reason}
        </span>
      </div>
      <p className="line-clamp-3 text-sm leading-6 text-slate-600">{failure.generated_output}</p>
    </div>
  );
}

export function BenchmarkingDashboard() {
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEvaluation = async () => {
    setLoading(true);
    setError(null);
    try {
      setSummary(await api.evaluation());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation request failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvaluation();
  }, []);

  const comparison = useMemo(() => {
    if (!summary) return [];
    const leaseSightF1 = summary.academic_benchmark.leasesight_f1_score;
    return [
      {
        label: 'F1 Score',
        leasesight: leaseSightF1,
        baseline: summary.academic_benchmark.f1_score,
      },
      {
        label: 'Precision vs Faithfulness',
        leasesight: summary.deepeval_metrics.faithfulness,
        baseline: summary.academic_benchmark.precision,
      },
      {
        label: 'Recall vs Context Recall',
        leasesight: summary.deepeval_metrics.context_recall,
        baseline: summary.academic_benchmark.recall,
      },
    ];
  }, [summary]);

  return (
    <section className="w-full space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-md border border-emerald-100 bg-emerald-50 px-3 py-1">
            <BarChart3 className="h-4 w-4 text-emerald-700" />
            <span className="text-xs font-black uppercase tracking-widest text-emerald-700">Benchmarking</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-950">LeaseSight vs Research Baseline</h2>
          <p className="mt-1 text-sm text-slate-500">
            DeepEval RAG scores compared against the CUAD legal dataset benchmark.
          </p>
        </div>
        <button
          type="button"
          onClick={loadEvaluation}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-800 shadow-sm transition hover:bg-slate-50 disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Refresh
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-3 rounded-lg border border-red-100 bg-red-50 p-4 text-sm font-semibold text-red-700">
          <AlertTriangle className="h-5 w-5" />
          {error}
        </div>
      )}

      {loading && !summary && (
        <div className="flex min-h-64 items-center justify-center rounded-lg border border-slate-200 bg-white">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
        </div>
      )}

      {summary && (
        <>
          <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-6 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-950">Comparative Scores</h3>
                  <p className="text-sm text-slate-500">{summary.academic_benchmark.paper_title}</p>
                </div>
                <div className="rounded-md bg-emerald-50 px-3 py-2 text-right">
                  <p className="text-[10px] font-black uppercase tracking-widest text-emerald-700">LeaseSight F1</p>
                  <p className="text-xl font-black text-emerald-700">
                    {percent(summary.academic_benchmark.leasesight_f1_score)}%
                  </p>
                </div>
              </div>
              <div className="space-y-6">
                {comparison.map((metric) => (
                  <MetricBar key={metric.label} {...metric} />
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-bold text-slate-950">DeepEval Metrics</h3>
              <div className="mt-5 space-y-4">
                {Object.entries(summary.deepeval_metrics).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between border-b border-slate-100 pb-3 last:border-0">
                    <span className="text-sm font-semibold capitalize text-slate-600">{key.replaceAll('_', ' ')}</span>
                    <span className="text-lg font-black text-slate-950">{percent(value)}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-6">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-bold text-slate-950">Failure Analysis</h3>
                <p className="text-sm text-slate-500">Logged cases where faithfulness or relevance dropped below 70%.</p>
              </div>
              <span className="rounded-md bg-white px-3 py-1 text-xs font-bold text-slate-600">
                {summary.failed_cases.length} case{summary.failed_cases.length === 1 ? '' : 's'}
              </span>
            </div>

            {summary.failed_cases.length > 0 ? (
              <div className="space-y-3">
                {summary.failed_cases.map((failure, index) => (
                  <FailureRow key={`${failure.user_query}-${index}`} failure={failure} />
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-sm font-semibold text-slate-500">
                No failed benchmark cases have been logged yet.
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
