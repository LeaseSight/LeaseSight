'use client';

import { Header } from '@/components/Header';
import { BackNavigation } from '@/components/BackNavigation';
import { 
  Check, Zap, ShieldCheck, Database, 
  Cpu, Globe, ArrowRight, Sparkles 
} from 'lucide-react';
import Link from 'next/link';

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#030712] text-white selection:bg-purple-500/30 font-sans">
      
      {/* Mesh Background */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-purple-600/5 blur-[140px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-blue-600/5 blur-[140px]" />
      </div>

      <nav className="relative z-50 h-20 flex items-center justify-between px-8 max-w-7xl mx-auto">
        <div className="flex w-full items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-purple-400" />
            <span className="font-bold text-lg tracking-widest font-mono">LEASESIGHT</span>
          </Link>
          <BackNavigation breadcrumbs={[{ label: 'Home', href: '/' }, { label: 'Pricing' }]} useBackButton />
        </div>
      </nav>

      <main className="relative z-10 max-w-7xl mx-auto px-8 py-20">
        <div className="text-center space-y-4 mb-20">
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight">Flexible Intelligence.</h1>
          <p className="text-white/40 text-lg max-w-xl mx-auto font-mono">
            Choose how you power your audits. Bring your own brain or use ours.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          
          {/* BYOK Tier */}
          <div className="group relative rounded-[2.5rem] border border-white/10 bg-white/5 backdrop-blur-xl p-10 transition-all hover:border-purple-500/30 hover:bg-white/10">
            <div className="flex items-center justify-between mb-8">
              <div className="p-3 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
                <Cpu className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest px-3 py-1 rounded-full border border-purple-500/20">Power User</span>
            </div>
            
            <div className="mb-8">
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-bold">$10</span>
                <span className="text-white/30 text-sm font-mono">/month</span>
              </div>
              <p className="mt-4 text-white/50 text-sm leading-relaxed">
                Bring your own OpenAI, Pinecone, and Azure keys. We provide the professional UI, RAG logic, and Visual Proof-Chain workstation.
              </p>
            </div>

            <ul className="space-y-4 mb-10">
              <PricingFeature text="Full Auditor Workstation" />
              <PricingFeature text="Bulk Migration Engine" />
              <PricingFeature text="Visual Proof-Chain Integration" />
              <PricingFeature text="Unlimited Local Documents" />
              <PricingFeature text="BYOK Configuration" />
            </ul>

            <Link 
              href="/dashboard/audit"
              className="block w-full py-4 rounded-2xl bg-white/5 border border-white/10 font-bold text-sm text-center hover:bg-white/10 transition-all"
            >
              Choose Power User
            </Link>
          </div>

          {/* Managed Tier */}
          <div className="group relative rounded-[2.5rem] border-2 border-blue-500/30 bg-blue-500/5 backdrop-blur-xl p-10 transition-all hover:bg-blue-500/10">
            <div className="absolute top-0 right-0 p-8">
              <Sparkles className="w-6 h-6 text-blue-400 animate-pulse" />
            </div>
            
            <div className="flex items-center justify-between mb-8">
              <div className="p-3 rounded-2xl bg-blue-500/20 border border-blue-500/30 text-blue-400">
                <Globe className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest px-3 py-1 rounded-full border border-blue-500/30">Pro Auditor</span>
            </div>
            
            <div className="mb-8">
              <div className="flex items-baseline gap-2">
                <span className="text-5xl font-bold">$50</span>
                <span className="text-white/30 text-sm font-mono">/month</span>
              </div>
              <p className="mt-4 text-white/50 text-sm leading-relaxed">
                Zero setup. We handle all API costs, vector indexing, and GPU processing. Just upload and audit. High-performance infrastructure included.
              </p>
            </div>

            <ul className="space-y-4 mb-10">
              <PricingFeature text="Everything in Power User" />
              <PricingFeature text="No API Keys Required" />
              <PricingFeature text="High-Priority GPU Queue" />
              <PricingFeature text="50 Managed Documents / mo" />
              <PricingFeature text="Managed Vector Storage" />
            </ul>

            <Link 
              href="/dashboard/audit"
              className="block w-full py-4 rounded-2xl bg-blue-600 text-white font-bold text-sm text-center hover:bg-blue-500 transition-all shadow-xl shadow-blue-500/20"
            >
              Subscribe to Pro
            </Link>
          </div>

        </div>

        {/* Enterprise CTA */}
        <div className="mt-20 text-center space-y-6">
          <Link href="/" className="text-xs font-mono text-white/30 uppercase hover:text-white transition-colors">
            ← Return to Home
          </Link>
          <div className="h-px w-20 bg-white/10 mx-auto" />
          <p className="text-white/30 text-xs font-mono uppercase tracking-[0.2em]">Need more capacity?</p>
          <button className="inline-flex items-center gap-2 text-sm font-bold text-white hover:text-purple-400 transition-colors group">
            Contact Enterprise Sales <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </main>
    </div>
  );
}

function PricingFeature({ text }: { text: string }) {
  return (
    <li className="flex items-center gap-3">
      <div className="w-5 h-5 rounded-full bg-white/5 flex items-center justify-center border border-white/10 shrink-0">
        <Check className="w-3 h-3 text-white/60" />
      </div>
      <span className="text-xs text-white/60 font-medium">{text}</span>
    </li>
  );
}
