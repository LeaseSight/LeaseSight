'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function DashboardRoot() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/audit');
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center bg-[#F9FAFB]">
      <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
    </div>
  );
}
