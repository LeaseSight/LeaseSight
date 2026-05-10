'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ChevronLeft } from 'lucide-react';

interface Breadcrumb {
  label: string;
  href?: string;
}

interface BackNavigationProps {
  breadcrumbs: Breadcrumb[];
  onBack?: () => void;
  useBackButton?: boolean;
}

export function BackNavigation({ breadcrumbs, onBack, useBackButton = false }: BackNavigationProps) {
  const router = useRouter();

  const handleBack = () => {
    if (onBack) return onBack();
    if (useBackButton) return router.back();
    const last = breadcrumbs[breadcrumbs.length - 1];
    if (last?.href) router.push(last.href);
  };

  return (
    <nav className="flex min-h-11 items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500" aria-label="Breadcrumb">
      <button
        onClick={handleBack}
        className="inline-flex min-h-11 min-w-11 items-center gap-1.5 rounded-md px-4 py-3 text-slate-600 transition hover:bg-slate-100 hover:text-[#1A1A1A] sm:px-5 sm:py-2"
        aria-label="Go back"
      >
        <ChevronLeft className="h-4 w-4" />
        <span className="hidden sm:inline">Back</span>
      </button>

      {breadcrumbs.length > 0 && (
        <div className="hidden sm:flex items-center gap-1">
          {breadcrumbs.map((crumb, idx) => (
            <div key={idx} className="flex items-center gap-1">
              {idx > 0 && <span className="text-slate-300">/</span>}
              {crumb.href ? (
                <Link href={crumb.href} className="text-slate-600 transition hover:text-[#1A1A1A]">
                  {crumb.label}
                </Link>
              ) : (
                <span className="text-slate-600">{crumb.label}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </nav>
  );
}
