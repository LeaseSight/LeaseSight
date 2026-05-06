'use client';

import Link from 'next/link';
import { ArrowRight, Zap, ShieldCheck, BarChart3, Globe } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-hidden flex flex-col items-center justify-center p-6 bg-[#030712]">
      
      {/* Background Mesh Gradient */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-purple-900/20 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-blue-900/20 blur-[120px]" />
      </div>

      {/* Hero Section */}
      <div className="relative z-10 max-w-5xl w-full text-center space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-1000">
        
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/10 bg-white/5 backdrop-blur-md">
          <Globe className="w-3 h-3 text-purple-400" />
          <span className="text-[10px] uppercase tracking-widest text-white/70 font-mono">Global Contract Intelligence v3.0</span>
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-8xl font-bold tracking-tight text-white font-sans">
          LeaseSight: The <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-blue-400 to-emerald-400">Visual Proof-Chain</span> for Global Contracts.
        </h1>

        {/* Sub-headline */}
        <p className="text-lg md:text-xl text-white/50 max-w-2xl mx-auto font-mono">
          Intelligent contract analysis powered by multi-agent AI orchestration. 
          Audit, visualize, and secure your legal obligations with surgical precision.
        </p>

        {/* CTA Section */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <Link 
            href="/dashboard"
            className="group relative px-8 py-4 rounded-2xl bg-white text-black font-semibold overflow-hidden transition-all hover:scale-105 active:scale-95"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 opacity-0 group-hover:opacity-100 transition-opacity" />
            <span className="relative z-10 group-hover:text-white flex items-center gap-2">
              Launch Auditor <ArrowRight className="w-4 h-4" />
            </span>
          </Link>
          <Link 
            href="/settings"
            className="px-8 py-4 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-md text-white/80 font-semibold transition-all hover:bg-white/10"
          >
            Configure Keys
          </Link>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-16 max-w-4xl mx-auto">
          <FeatureCard 
            icon={<Zap className="w-5 h-5 text-yellow-400" />}
            title="Surgical Extraction"
            desc="AI-driven data mining with visual coordinate grounding."
          />
          <FeatureCard 
            icon={<ShieldCheck className="w-5 h-5 text-emerald-400" />}
            title="Proof-Chain Audit"
            desc="Cross-validated finding logic for enterprise compliance."
          />
          <FeatureCard 
            icon={<BarChart3 className="w-5 h-5 text-blue-400" />}
            title="3D Analytics"
            desc="Vector-based similarity mapping for entire portfolios."
          />
        </div>
      </div>

      {/* Footer */}
      <footer className="absolute bottom-8 text-white/20 text-[10px] tracking-widest font-mono">
        SECURED BY CLIENT-SIDE ENCRYPTION • BYOK ARCHITECTURE
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="p-6 rounded-2xl border border-white/5 bg-white/5 backdrop-blur-xl text-left space-y-3 transition-all hover:border-white/20">
      <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/10">
        {icon}
      </div>
      <h3 className="text-white font-semibold text-sm">{title}</h3>
      <p className="text-white/40 text-xs leading-relaxed">{desc}</p>
    </div>
  );
}
