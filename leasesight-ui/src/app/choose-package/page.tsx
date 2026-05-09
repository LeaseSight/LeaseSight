'use client';

import { useRouter } from 'next/navigation';
import { Check, KeyRound, ShieldCheck } from 'lucide-react';
import { BrandLogo } from '@/components/BrandLogo';
import { saveSelectedTier } from '@/lib/api';

export default function ChoosePackagePage() {
  const router = useRouter();

  const choose = (tier: 'free' | 'pro') => {
    saveSelectedTier(tier);
    router.push(tier === 'free' ? '/settings' : '/dashboard/audit');
  };

  return (
    <main className="min-h-screen bg-[#F9FAFB] px-4 py-10 text-[#1A1A1A]">
      <div className="enterprise-container">
        <header className="mb-12 flex items-center justify-between">
          <BrandLogo />
          <p className="hidden text-xs font-semibold uppercase tracking-[0.22em] text-slate-500 sm:block">Select Package</p>
        </header>

        <section className="mx-auto max-w-3xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Subscription Gate</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Choose how LeaseSight powers your audits.</h1>
          <p className="mt-5 text-sm leading-6 text-slate-500">
            Free users bring their own OpenAI key. Enterprise users run on fully managed LeaseSight infrastructure.
          </p>
        </section>

        <section className="mx-auto mt-12 grid max-w-5xl gap-6 md:grid-cols-2">
          <article className="border border-slate-200 bg-white p-7 shadow-sm transition hover:-translate-y-1 hover:shadow-xl">
            <KeyRound className="h-8 w-8 text-[#1A1A1A]" />
            <p className="mt-8 text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">Tier 1</p>
            <h2 className="mt-2 text-3xl font-semibold">Free Forever</h2>
            <p className="mt-1 text-lg text-slate-500">Bring Your Own Brain.</p>
            <div className="mt-8 text-4xl font-semibold">$0</div>
            <ul className="mt-8 space-y-3 text-sm text-slate-600">
              {['Use your own OpenAI API key', 'Shared Azure OCR and Pinecone rails', 'Unified LeaseSight knowledge base indexing', 'Secure browser-local key storage'].map(item => (
                <li key={item} className="flex gap-3"><Check className="mt-0.5 h-4 w-4 text-[#1A1A1A]" />{item}</li>
              ))}
            </ul>
            <button onClick={() => choose('free')} className="mt-8 w-full border border-[#1A1A1A] px-5 py-3 text-sm font-semibold uppercase tracking-[0.16em] transition hover:-translate-y-0.5 hover:bg-[#1A1A1A] hover:text-white">
              Choose Free
            </button>
          </article>

          <article className="border border-[#1A1A1A] bg-[#1A1A1A] p-7 text-white shadow-xl transition hover:-translate-y-1">
            <ShieldCheck className="h-8 w-8 text-white" />
            <p className="mt-8 text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Tier 2</p>
            <h2 className="mt-2 text-3xl font-semibold">Enterprise</h2>
            <p className="mt-1 text-lg text-slate-300">Fully Managed.</p>
            <div className="mt-8 text-4xl font-semibold">$100<span className="text-base text-slate-400">/mo</span></div>
            <ul className="mt-8 space-y-3 text-sm text-slate-300">
              {['No user API keys required', 'Server-managed OpenAI execution', 'Shared Azure Document Intelligence', 'Central Pinecone RAG knowledge base'].map(item => (
                <li key={item} className="flex gap-3"><Check className="mt-0.5 h-4 w-4 text-white" />{item}</li>
              ))}
            </ul>
            <button onClick={() => choose('pro')} className="mt-8 w-full border border-white bg-white px-5 py-3 text-sm font-semibold uppercase tracking-[0.16em] text-[#1A1A1A] transition hover:-translate-y-0.5 hover:bg-slate-200">
              Choose Enterprise
            </button>
          </article>
        </section>
      </div>
    </main>
  );
}
