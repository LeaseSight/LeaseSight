'use client';

import { useState } from 'react';
import Link from 'next/link';
import { 
  Zap, ChevronDown, Activity, Database, GraduationCap, Sparkles 
} from 'lucide-react';
import { 
  SignInButton, UserButton, useAuth 
} from '@clerk/nextjs';
import { BentoLandingPage } from '@/components/BentoLandingPage';

export default function LandingPage() {
  const { userId } = useAuth();
  const [isLaunchOpen, setIsLaunchOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#030712] text-white selection:bg-purple-500/30 selection:text-purple-200 overflow-x-hidden font-sans">
      
      {/* Background Mesh Gradient */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] rounded-full bg-purple-600/10 blur-[140px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-blue-600/10 blur-[140px] animate-pulse" style={{ animationDelay: '2s' }} />
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] rounded-full bg-emerald-600/5 blur-[120px]" />
      </div>

      {/* Navigation */}
      <nav className="relative z-50 h-20 flex items-center justify-between px-8 max-w-7xl mx-auto border-b border-white/5 backdrop-blur-md bg-black/20">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-lg tracking-widest font-mono">LEASESIGHT</span>
        </div>

        <div className="flex items-center gap-8">
          <div className="hidden md:flex items-center gap-6 text-sm font-medium text-white/50">
            <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
            <a href="#" className="hover:text-white transition-colors">Enterprise</a>
          </div>

          <div className="flex items-center gap-4">
            {!userId ? (
              <>
                <SignInButton mode="modal">
                  <button className="text-sm font-bold text-white/70 hover:text-white transition-colors">
                    Login
                  </button>
                </SignInButton>
                <Link 
                  href="/pricing"
                  className="px-5 py-2 rounded-xl bg-white text-black font-bold text-xs uppercase tracking-widest hover:scale-105 transition-all"
                >
                  Get Started
                </Link>
              </>
            ) : (
              <>
                <div className="relative">
                  <button 
                    onClick={() => setIsLaunchOpen(!isLaunchOpen)}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white text-black font-bold text-sm transition-all hover:scale-105 active:scale-95 shadow-xl shadow-white/10"
                  >
                    Launch App <ChevronDown className={`w-4 h-4 transition-transform ${isLaunchOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {isLaunchOpen && (
                    <div className="absolute top-full right-0 mt-3 w-72 rounded-2xl border border-white/10 bg-[#0a0a16] shadow-2xl z-50 p-2 animate-in fade-in zoom-in-95 duration-200">
                      <Link href="/dashboard/audit" className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/5 transition-colors group">
                        <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 group-hover:bg-purple-500 group-hover:text-white transition-colors">
                          <Activity className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-white">Interactive Auditor</p>
                          <p className="text-[10px] text-white/40">Surgical RAG-based analysis</p>
                        </div>
                      </Link>
                      <Link href="/dashboard/migrate" className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/5 transition-colors group mt-1">
                        <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:bg-blue-500 group-hover:text-white transition-colors">
                          <Database className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-white">Bulk Migration Engine</p>
                          <p className="text-[10px] text-white/40">Academic & Legal batching</p>
                        </div>
                      </Link>
                      <Link href="/dashboard/research" className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/5 transition-colors group mt-1">
                        <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:bg-emerald-500 group-hover:text-white transition-colors">
                          <GraduationCap className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="text-xs font-bold text-white">Peer-Review Assistant</p>
                          <p className="text-[10px] text-white/40">Academic pre-submission audit</p>
                        </div>
                      </Link>
                    </div>
                  )}
                </div>
                <UserButton afterSignOutUrl="/" />
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 max-w-7xl mx-auto px-8 py-20 md:py-32">
        <div className="text-center space-y-8 mb-24">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-md animate-fade-in">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-[10px] uppercase tracking-widest text-white/70 font-mono">The 2026 Multi-Service AI Platform</span>
          </div>
          
          <h1 className="text-6xl md:text-8xl font-bold tracking-tight text-white leading-tight">
            Universal Intelligence <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-blue-400 to-emerald-400">for Modern Enterprise.</span>
          </h1>

          <p className="text-lg md:text-xl text-white/40 max-w-2xl mx-auto font-medium leading-relaxed">
            LeaseSight transforms complex legal archives, enterprise data, and research papers into actionable intelligence. 
            Auditing, migration, and academic excellence—all in one high-performance interface.
          </p>
        </div>

        {/* Bento Grid Component */}
        <BentoLandingPage />
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 mt-20 py-12 px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="text-[10px] text-white/20 tracking-[0.3em] font-mono uppercase">
            © 2026 LEASESIGHT PLATFORM • END-TO-END LEGAL-AI ORCHESTRATION
          </div>
          <div className="flex gap-8 text-[10px] text-white/40 tracking-widest font-bold uppercase">
            <a href="#" className="hover:text-white transition-colors">Twitter</a>
            <a href="#" className="hover:text-white transition-colors">LinkedIn</a>
            <a href="#" className="hover:text-white transition-colors">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
