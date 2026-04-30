'use client';

interface RiskGaugeProps {
  score: number; // 1-10
}

export function RiskGauge({ score }: RiskGaugeProps) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 10) * circumference;

  const getColor = () => {
    if (score <= 3) return '#10b981'; // emerald
    if (score <= 6) return '#f59e0b'; // amber
    return '#ef4444'; // red
  };

  const getLabel = () => {
    if (score <= 3) return 'Low Risk';
    if (score <= 6) return 'Medium Risk';
    return 'High Risk';
  };

  const color = getColor();

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-28 h-28">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle cx="50" cy="50" r={radius} fill="none"
                  stroke="var(--bg-card)" strokeWidth="8" />
          {/* Progress arc */}
          <circle cx="50" cy="50" r={radius} fill="none"
                  stroke={color} strokeWidth="8" strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={circumference - progress}
                  style={{ transition: 'stroke-dashoffset 1s ease-out, stroke 0.5s ease' }} />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold" style={{ color }}>{score}</span>
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>/10</span>
        </div>
      </div>
      <span className="text-xs font-medium px-2 py-0.5 rounded-full"
            style={{ background: `${color}20`, color }}>
        {getLabel()}
      </span>
    </div>
  );
}
