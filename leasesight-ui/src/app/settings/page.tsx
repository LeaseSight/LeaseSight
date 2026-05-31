'use client';

import { useState } from 'react';
import { CheckCircle2, Loader2, ServerCog, XCircle } from 'lucide-react';
import { BrandLogo } from '@/components/BrandLogo';
import { BackNavigation } from '@/components/BackNavigation';
import { api } from '@/lib/api';

type TestStatus = 'idle' | 'testing' | 'ok' | 'error';

export default function SettingsPage() {
  const [testStatus, setTestStatus] = useState<TestStatus>('idle');
  const [testMessage, setTestMessage] = useState('');

  const handleTest = async () => {
    setTestStatus('testing');
    setTestMessage('');
    try {
      const res = await api.testConnection();
      const success = res.success || res.status === 'success';
      setTestStatus(success ? 'ok' : 'error');
      setTestMessage(success ? 'Server Gemini, Azure, Pinecone, and local embedding configuration is reachable.' : res.message || 'Connection failed.');
    } catch (e) {
      setTestStatus('error');
      setTestMessage(e instanceof Error ? e.message : 'Connection failed.');
    }
  };

  return (
    <main className="min-h-screen bg-[#F9FAFB] text-[#1A1A1A]">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-xl">
        <div className="enterprise-container flex h-16 items-center justify-between">
          <BrandLogo />
          <BackNavigation breadcrumbs={[{ label: 'Dashboard', href: '/dashboard/audit' }]} />
        </div>
      </header>

      <section className="enterprise-container py-12">
        <div className="mx-auto max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">System Settings</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">Managed Backend</h1>
          <p className="mt-4 text-sm leading-6 text-slate-500">
            LeaseSight now runs with server-managed Gemini, Azure Document Intelligence, Pinecone, and local transformer embeddings. Users do not provide browser-side API keys.
          </p>

          <div className="mt-8 border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="border border-slate-200 p-3">
                  <ServerCog className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-semibold">Backend Connection</h2>
                  <p className="text-xs text-slate-500">Runs a live Gemini generation check and local embedding warmup.</p>
                </div>
              </div>
            </div>

            {testStatus !== 'idle' && (
              <div className={`mt-4 flex items-center gap-2 border p-3 text-sm ${
                testStatus === 'ok' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' :
                testStatus === 'error' ? 'border-red-200 bg-red-50 text-red-700' :
                'border-slate-200 bg-slate-50 text-slate-600'
              }`}>
                {testStatus === 'testing' && <Loader2 className="h-4 w-4 animate-spin" />}
                {testStatus === 'ok' && <CheckCircle2 className="h-4 w-4" />}
                {testStatus === 'error' && <XCircle className="h-4 w-4" />}
                {testStatus === 'testing' ? 'Testing managed backend...' : testMessage}
              </div>
            )}

            <button onClick={handleTest} disabled={testStatus === 'testing'} className="mt-6 border border-slate-300 px-5 py-3 text-sm font-semibold uppercase tracking-[0.14em] transition hover:-translate-y-0.5 hover:border-[#1A1A1A] disabled:opacity-40">
              Test Managed Backend
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
