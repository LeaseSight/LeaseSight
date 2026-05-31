'use client';

import { useRouter } from 'next/navigation';
import { Check, Database } from 'lucide-react';
import { BrandLogo } from '@/components/BrandLogo';
import { BackNavigation } from '@/components/BackNavigation';
import { saveSelectedTier } from '@/lib/api';

export default function ChoosePackagePage() {
  const router = useRouter();

  const choose = () => {
    saveSelectedTier('pro');
    router.push('/dashboard/audit');
  };

  return (
    <main className="min-h-screen bg-[#F9FAFB] px-4 py-10 text-[#1A1A1A]">
      <div className="enterprise-container">
        <header className="mb-12 flex items-center justify-between">
          <BrandLogo />
          <BackNavigation breadcrumbs={[{ label: 'Home', href: '/' }]} useBackButton={true} />
        </header>

        <section className="mx-auto max-w-3xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Subscription Gate</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Choose how LeaseSight powers your audits.</h1>
          <p className="mt-5 text-sm leading-6 text-slate-500">
            LeaseSight runs on managed Gemini, Azure Document Intelligence, Pinecone, and local transformer embeddings.
          </p>
        </section>

        <section className="mx-auto mt-12 grid max-w-3xl gap-6">
          <article className="border border-slate-200 bg-white p-7 shadow-sm transition hover:-translate-y-1 hover:shadow-xl">
            <Database className="h-8 w-8 text-[#1A1A1A]" />
            <p className="mt-8 text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Tier 1</p>
            <h2 className="mt-2 text-3xl font-semibold">Managed Auditor</h2>
            <p className="mt-1 text-lg text-slate-500">No user API keys required.</p>
            <div className="mt-8 text-4xl font-semibold">$0<span className="text-base text-slate-500"> during local testing</span></div>
            <ul className="mt-8 space-y-3 text-sm text-slate-600">
              {['Server-managed Gemini reasoning', 'Azure OCR and coordinate extraction', 'Local all-mpnet-base-v2 embeddings', 'Pinecone vector indexing'].map(item => (
                <li key={item} className="flex gap-3"><Check className="mt-0.5 h-4 w-4 text-[#1A1A1A]" />{item}</li>
              ))}
            </ul>
            <button onClick={choose} className="mt-8 w-full border border-[#1A1A1A] px-5 py-3 text-sm font-semibold uppercase tracking-[0.16em] transition hover:-translate-y-0.5 hover:bg-[#1A1A1A] hover:text-white">
              Continue
            </button>
          </article>
        </section>
      </div>
    </main>
  );
}
