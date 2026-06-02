'use client';

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { LEGAL_PANELS, type LegalPanel } from '@/content/legal';

export function LegalDrawer({ panel, onClose }: { panel: LegalPanel | null; onClose: () => void }) {
  const open = panel !== null;
  const content = panel ? LEGAL_PANELS[panel] : null;

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  if (!open || !content) return null;

  return (
    <div className="fixed inset-0 z-[90] flex justify-end" role="dialog" aria-modal="true" aria-labelledby="legal-drawer-title">
      <button
        type="button"
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px] transition-opacity"
        aria-label="Close panel"
        onClick={onClose}
      />
      <aside
        className="legal-drawer-panel relative flex h-full w-full max-w-xl flex-col border-l border-slate-200 bg-[#F9FAFB] shadow-2xl"
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">LeaseSight</p>
            <h2 id="legal-drawer-title" className="mt-2 text-2xl font-semibold tracking-tight text-[#1A1A1A]">
              {content.title}
            </h2>
            <p className="mt-1 text-xs text-slate-500">{content.subtitle}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 border border-slate-300 p-2 text-[#1A1A1A] transition hover:-translate-y-0.5 hover:bg-[#1A1A1A] hover:text-white"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-6">
          <div className="space-y-8">
            {content.sections.map(section => (
              <section key={section.heading}>
                <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-[#1A1A1A]">{section.heading}</h3>
                <div className="mt-3 space-y-3">
                  {section.body.map((paragraph, i) => (
                    <p key={i} className="text-sm leading-7 text-slate-600">
                      {paragraph}
                    </p>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}
