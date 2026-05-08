import { Suspense } from 'react';
import ReviewPageContent from './ReviewPageContent';

export default function ReviewPage() {
  return (
    <Suspense fallback={
      <div className="h-screen flex items-center justify-center bg-[#030712] text-white">
        <p className="text-white/40 font-mono text-sm tracking-widest uppercase">Loading...</p>
      </div>
    }>
      <ReviewPageContent />
    </Suspense>
  );
}
