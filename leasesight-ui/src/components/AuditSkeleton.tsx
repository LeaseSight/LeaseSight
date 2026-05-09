export function AuditSkeleton() {
  return (
    <div className="space-y-4 p-4" aria-label="Loading audit results">
      <div className="h-16 animate-pulse bg-slate-200" />
      <div className="grid grid-cols-[88px_1fr] gap-4">
        <div className="h-24 animate-pulse bg-slate-200" />
        <div className="space-y-2">
          <div className="h-6 animate-pulse bg-slate-200" />
          <div className="h-6 w-5/6 animate-pulse bg-slate-200" />
          <div className="h-6 w-2/3 animate-pulse bg-slate-200" />
        </div>
      </div>
      {[0, 1, 2, 3].map(item => (
        <div key={item} className="border border-[var(--border-default)] bg-white p-4">
          <div className="mb-3 h-4 w-1/3 animate-pulse bg-slate-200" />
          <div className="h-3 animate-pulse bg-slate-200" />
          <div className="mt-2 h-3 w-4/5 animate-pulse bg-slate-200" />
        </div>
      ))}
    </div>
  );
}
