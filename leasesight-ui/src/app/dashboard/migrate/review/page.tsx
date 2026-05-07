'use client';

import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Header } from '@/components/Header';
import { SplitScreenReview } from '@/components/SplitScreenReview';

export default function ReviewPage() {
  const searchParams = useSearchParams();
  const batchId = searchParams.get('batchId');

  if (!batchId) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#030712] text-white">
        <div className="text-center">
          <p className="text-white/40 mb-4 font-mono text-sm tracking-widest uppercase">No batch ID provided.</p>
          <Link href="/dashboard/migrate" className="px-6 py-2 rounded-xl bg-white text-black font-bold hover:scale-105 transition-all text-sm">
            Return to Migration Pro
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-white">
      <Header 
        isAuditing={false}
        onToggleNetwork={() => {}}
        documents={[]}
        onSelectDoc={() => {}}
      />

      <div className="flex-1 overflow-hidden">
        <SplitScreenReview batchId={batchId} />
      </div>
    </div>
  );
}
