'use client';

interface BenchmarkGaugeProps {
  score: number;
}

export function BenchmarkGauge({ score }: BenchmarkGaugeProps) {
  // Score is out of 100
  const isOutlier = score < 60;
  const color = isOutlier ? '#ef4444' : '#10b981'; // Red or Mint
  const label = isOutlier ? 'Outlier' : 'Standard';

  return (
    <div className="flex flex-col items-center justify-center px-4 py-2 rounded-lg border shadow-sm w-64 shrink-0" 
         style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}>
      <div className="text-[10px] font-semibold tracking-wider uppercase mb-1" style={{ color: 'var(--text-secondary)' }}>
        Market Alignment
      </div>
      <div className="flex items-center gap-2 w-full mt-1">
        <span className="text-xs font-bold w-8 text-right" style={{ color }}>{score}%</span>
        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border-default)' }}>
          <div className="h-full transition-all duration-1000 rounded-full" style={{ width: `${score}%`, backgroundColor: color }} />
        </div>
        <span className="text-[10px] font-bold w-16" style={{ color }}>{label}</span>
      </div>
    </div>
  );
}
