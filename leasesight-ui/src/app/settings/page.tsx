'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, Eye, EyeOff, KeyRound, Loader2, XCircle } from 'lucide-react';
import { BrandLogo } from '@/components/BrandLogo';
import { BackNavigation } from '@/components/BackNavigation';
import { api, getSelectedTier, getStoredKeys, hasStoredKeys, saveStoredKeys } from '@/lib/api';

type TestStatus = 'idle' | 'testing' | 'ok' | 'error';

export default function SettingsPage() {
  const [openaiKey, setOpenaiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [saved, setSaved] = useState(false);
  const [testStatus, setTestStatus] = useState<TestStatus>('idle');
  const [testMessage, setTestMessage] = useState('');
  const tier = getSelectedTier();
  const isFree = tier !== 'pro';

  useEffect(() => {
    setOpenaiKey(getStoredKeys().openai);
    const err = sessionStorage.getItem('ls_auth_error');
    if (err) {
      setTestStatus('error');
      setTestMessage(err);
      sessionStorage.removeItem('ls_auth_error');
    }
  }, []);

  const handleSave = () => {
    saveStoredKeys({ openai: openaiKey.trim() });
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const handleTest = async () => {
    saveStoredKeys({ openai: openaiKey.trim() });
    setTestStatus('testing');
    setTestMessage('');
    try {
      const res = await api.testConnection();
      const success = res.success || res.status === 'success';
      setTestStatus(success ? 'ok' : 'error');
      setTestMessage(success ? 'Connection verified.' : res.message || 'Connection failed.');
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
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">API Settings</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">Key Manager</h1>
          <p className="mt-4 text-sm leading-6 text-slate-500">
            {isFree
              ? 'Free users must provide an OpenAI key. Azure Document Intelligence and Pinecone always run on LeaseSight server infrastructure.'
              : 'Enterprise users do not need to provide keys. This panel is available only for optional BYOK testing.'}
          </p>

          <div className="mt-8 border border-slate-200 bg-white p-6 shadow-sm">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="border border-slate-200 p-3">
                  <KeyRound className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-semibold">OpenAI API Key</h2>
                  <p className="text-xs text-slate-500">Sent as `X-OpenAI-Key` only for Free/BYOK audits.</p>
                </div>
              </div>
              <div className={`flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] ${hasStoredKeys() ? 'text-emerald-700' : 'text-red-600'}`}>
                {hasStoredKeys() ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
                {hasStoredKeys() ? 'Configured' : 'Missing'}
              </div>
            </div>

            <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">API Key</label>
            <div className="relative">
              <input
                value={openaiKey}
                onChange={e => setOpenaiKey(e.target.value)}
                type={showKey ? 'text' : 'password'}
                placeholder="sk-proj-..."
                className="w-full border border-slate-300 bg-[#F9FAFB] px-3 py-3 pr-11 font-mono text-sm outline-none transition focus:border-[#1A1A1A]"
                autoComplete="off"
              />
              <button type="button" onClick={() => setShowKey(!showKey)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-[#1A1A1A]">
                {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
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
                {testStatus === 'testing' ? 'Testing connection...' : testMessage}
              </div>
            )}

            {saved && (
              <div className="mt-4 border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                OpenAI key saved locally for Free/BYOK audits.
              </div>
            )}

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <button onClick={handleTest} disabled={!openaiKey || testStatus === 'testing'} className="border border-slate-300 px-5 py-3 text-sm font-semibold uppercase tracking-[0.14em] transition hover:-translate-y-0.5 hover:border-[#1A1A1A] disabled:opacity-40">
                Test Connection
              </button>
              <button onClick={handleSave} disabled={!openaiKey} className="bg-[#1A1A1A] px-5 py-3 text-sm font-semibold uppercase tracking-[0.14em] text-white transition hover:-translate-y-0.5 hover:bg-slate-700 disabled:opacity-40">
                Save Key
              </button>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
