'use client';

import { CalendarPlus, Clock } from 'lucide-react';
import { api } from '@/lib/api';

interface Obligation {
  label: string;
  date: string;
  description: string;
}

interface ObligationTimelineProps {
  obligations: Obligation[];
}

export function ObligationTimeline({ obligations }: ObligationTimelineProps) {
  if (!obligations || obligations.length === 0) return null;

  const handlePushToCalendar = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/calendar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ obligations }),
      });
      if (!res.ok) throw new Error('Failed to generate calendar');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'obligations.ics';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="mt-4 pt-4 border-t" style={{ borderColor: 'var(--border-default)' }}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-secondary)' }}>
          Smart Obligation Timeline
        </h3>
        <button
          onClick={handlePushToCalendar}
          className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium transition-colors hover:opacity-80 cursor-pointer"
          style={{ background: 'rgba(147, 51, 234, 0.1)', color: 'var(--accent-primary)', border: '1px solid rgba(147, 51, 234, 0.2)' }}
        >
          <CalendarPlus className="w-3 h-3" />
          Push to Calendar
        </button>
      </div>

      <div className="relative pl-3 space-y-4 before:absolute before:inset-0 before:ml-3.5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-[var(--border-default)] before:to-transparent">
        {obligations.map((obs, i) => (
          <div key={i} className="relative flex items-start gap-3">
            <div className="absolute left-[-17px] mt-1 w-2.5 h-2.5 rounded-full z-10" style={{ background: 'var(--bg-card)', border: '2px solid var(--accent-primary)' }} />
            <div className="flex-1 bg-[var(--bg-card)] border border-[var(--border-default)] rounded-md p-2.5 shadow-sm">
              <div className="flex items-center gap-2 mb-1">
                <Clock className="w-3 h-3" style={{ color: 'var(--accent-primary)' }} />
                <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{obs.label}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded ml-auto" style={{ background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}>
                  {obs.date}
                </span>
              </div>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-secondary)' }}>{obs.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
