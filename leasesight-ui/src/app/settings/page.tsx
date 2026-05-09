'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  KeyRound, Eye, EyeOff, CheckCircle2, XCircle, Loader2,
  ArrowLeft, Zap, ShieldCheck, AlertTriangle, Sparkles
} from 'lucide-react';
import { getStoredKeys, saveStoredKeys, hasStoredKeys, api } from '@/lib/api';

type TestStatus = 'idle' | 'testing' | 'ok' | 'error';

interface FieldState {
  value: string;
  show: boolean;
}

export default function SettingsPage() {
  const router = useRouter();

  // ---- Form State ----
  const [openai,        setOpenai]        = useState<FieldState>({ value: '', show: false });
  const [pinecone,      setPinecone]      = useState<FieldState>({ value: '', show: false });
  const [azureKey,      setAzureKey]      = useState<FieldState>({ value: '', show: false });
  const [azureEndpoint, setAzureEndpoint] = useState<FieldState>({ value: '', show: false });

  const [testStatus, setTestStatus] = useState<TestStatus>('idle');
  const [testMessage, setTestMessage] = useState('');
  const [saved, setSaved] = useState(false);
  const [authError, setAuthError] = useState('');

  // ---- Load from localStorage + sessionStorage error on mount ----
  useEffect(() => {
    const keys = getStoredKeys();
    setOpenai(s => ({ ...s, value: keys.openai }));
    setPinecone(s => ({ ...s, value: keys.pinecone }));
    setAzureKey(s => ({ ...s, value: keys.azureKey }));
    setAzureEndpoint(s => ({ ...s, value: keys.azureEndpoint }));

    // Read redirect error from api.ts
    const err = sessionStorage.getItem('ls_auth_error');
    if (err) {
      setAuthError(err);
      sessionStorage.removeItem('ls_auth_error');
    }
  }, []);

  // ---- Save handler ----
  const handleSave = () => {
    saveStoredKeys({
      openai:        openai.value.trim(),
      pinecone:      pinecone.value.trim(),
      azureKey:      azureKey.value.trim(),
      azureEndpoint: azureEndpoint.value.trim(),
    });
    setSaved(true);
    setAuthError('');
    setTimeout(() => setSaved(false), 3000);
  };

  // ---- Test Connection ----
  const handleTest = async () => {
    // Temporarily write values so the api service picks them up
    saveStoredKeys({
      openai:        openai.value.trim(),
      pinecone:      pinecone.value.trim(),
      azureKey:      azureKey.value.trim(),
      azureEndpoint: azureEndpoint.value.trim(),
    });
    setTestStatus('testing');
    setTestMessage('');
    try {
      const res = await api.testConnection();
      setTestStatus(res.success ? 'ok' : 'error');
      setTestMessage(res.success
        ? 'All services connected successfully!'
        : `OpenAI: ${res.openai} | Pinecone: ${res.pinecone}`);
    } catch (e: unknown) {
      setTestStatus('error');
      setTestMessage(e instanceof Error ? e.message : 'Connection failed. Check your keys.');
    }
  };

  const toggle = (setter: React.Dispatch<React.SetStateAction<FieldState>>) =>
    setter(s => ({ ...s, show: !s.show }));

  return (
    <div className="min-h-screen settings-bg flex flex-col overflow-visible">
      {/* ---- Top Nav ---- */}
      <header className="h-14 flex items-center justify-between px-6 border-b settings-header sticky top-0 z-50">
        <Link href="/dashboard" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <ArrowLeft className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
          <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>Back to Dashboard</span>
        </Link>
        <div className="flex items-center gap-2">
          <Zap className="w-5 h-5" style={{ color: 'var(--accent-emerald)' }} />
          <span className="font-bold text-sm tracking-widest" style={{ color: 'var(--text-primary)' }}>LEASESIGHT</span>
          <span className="text-xs px-2 py-0.5 rounded-full"
                style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--accent-emerald)' }}>SETTINGS</span>
        </div>
        <div className="w-24" />
      </header>

      {/* ---- Hero ---- */}
      <div className="py-10 px-6 text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-4 settings-icon-bg">
          <ShieldCheck className="w-7 h-7" style={{ color: 'var(--accent-primary)' }} />
        </div>
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
          API Configuration
        </h1>
        <p className="text-sm max-w-sm mx-auto" style={{ color: 'var(--text-secondary)' }}>
          Your keys are stored locally in your browser — they are never sent to any LeaseSight server.
        </p>
      </div>

      {/* ---- Auth Error Banner ---- */}
      {authError && (
        <div className="mx-6 mb-4 flex items-start gap-3 rounded-xl p-4 animate-fade-in"
             style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" style={{ color: 'var(--accent-red)' }} />
          <div>
            <p className="text-sm font-semibold mb-0.5" style={{ color: 'var(--accent-red)' }}>
              Authentication Failed
            </p>
            <p className="text-xs" style={{ color: 'var(--accent-red)', opacity: 0.85 }}>{authError}</p>
          </div>
        </div>
      )}

      {/* ---- Cards ---- */}
      <div className="flex-1 px-6 pb-10 max-w-2xl mx-auto w-full space-y-4">

        {/* OpenAI Card */}
        <ProviderCard
          title="OpenAI"
          badge="Required"
          badgeColor="var(--accent-primary)"
          description="Powers the Miner, Judge & Clerk agents and all embeddings."
          iconColor="#10a37f"
          iconLetter="O"
        >
          <KeyField
            label="API Key"
            placeholder="sk-proj-..."
            value={openai.value}
            show={openai.show}
            onChange={v => setOpenai(s => ({ ...s, value: v }))}
            onToggle={() => toggle(setOpenai)}
          />
        </ProviderCard>

        {/* Pinecone Card */}
        <ProviderCard
          title="Pinecone"
          badge="Required"
          badgeColor="var(--accent-primary)"
          description="Vector database for semantic search and market benchmarking."
          iconColor="#1b6ac9"
          iconLetter="P"
        >
          <KeyField
            label="API Key"
            placeholder="pcsk_..."
            value={pinecone.value}
            show={pinecone.show}
            onChange={v => setPinecone(s => ({ ...s, value: v }))}
            onToggle={() => toggle(setPinecone)}
          />
        </ProviderCard>

        {/* Azure Card */}
        <ProviderCard
          title="Azure Form Recognizer"
          badge="Optional"
          badgeColor="var(--accent-orange)"
          description="Enables PDF upload & spatial indexing. Required for new document processing."
          iconColor="#0078d4"
          iconLetter="A"
        >
          <KeyField
            label="API Key"
            placeholder="Azure Form Recognizer key..."
            value={azureKey.value}
            show={azureKey.show}
            onChange={v => setAzureKey(s => ({ ...s, value: v }))}
            onToggle={() => toggle(setAzureKey)}
          />
          <div className="mt-3">
            <KeyField
              label="Endpoint URL"
              placeholder="https://your-resource.cognitiveservices.azure.com/"
              value={azureEndpoint.value}
              show={azureEndpoint.show}
              onChange={v => setAzureEndpoint(s => ({ ...s, value: v }))}
              onToggle={() => toggle(setAzureEndpoint)}
              isUrl
            />
          </div>
        </ProviderCard>

        {/* Test Status */}
        {testStatus !== 'idle' && (
          <div className={`flex items-center gap-3 rounded-xl p-3 animate-fade-in text-sm ${testStatus === 'ok' ? 'test-ok' : testStatus === 'error' ? 'test-error' : 'test-testing'}`}>
            {testStatus === 'testing' && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
            {testStatus === 'ok'      && <CheckCircle2 className="w-4 h-4 shrink-0" />}
            {testStatus === 'error'   && <XCircle className="w-4 h-4 shrink-0" />}
            <span>{testStatus === 'testing' ? 'Testing connection…' : testMessage}</span>
          </div>
        )}

        {/* Save Status */}
        {saved && (
          <div className="flex items-center gap-2 rounded-xl p-3 animate-fade-in text-sm"
               style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--accent-emerald)', border: '1px solid rgba(16,185,129,0.25)' }}>
            <Sparkles className="w-4 h-4 shrink-0" />
            Keys saved to your browser — you&apos;re all set!
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <button
            id="test-connection-btn"
            onClick={handleTest}
            disabled={testStatus === 'testing'}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all hover:opacity-80 disabled:opacity-50 settings-btn-secondary"
          >
            {testStatus === 'testing' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Test Connection
          </button>
          <button
            id="save-keys-btn"
            onClick={handleSave}
            className="flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all glow-primary settings-btn-primary"
          >
            <KeyRound className="w-4 h-4" />
            Save Keys
          </button>
        </div>

        {/* Go to Dashboard */}
        {hasStoredKeys() && (
          <button
            onClick={() => router.push('/dashboard')}
            className="w-full py-3 rounded-xl text-sm font-medium transition-all hover:opacity-80"
            style={{ color: 'var(--text-secondary)' }}
          >
            ← Return to Dashboard
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProviderCard({ title, badge, badgeColor, description, iconColor, iconLetter, children }: {
  title: string; badge: string; badgeColor: string; description: string;
  iconColor: string; iconLetter: string; children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl p-5 settings-card">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0"
             style={{ background: iconColor }}>
          {iconLetter}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{title}</span>
            <span className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                  style={{ background: `${badgeColor}22`, color: badgeColor }}>
              {badge}
            </span>
          </div>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

function KeyField({ label, placeholder, value, show, onChange, onToggle, isUrl }: {
  label: string; placeholder: string; value: string; show: boolean;
  onChange: (v: string) => void; onToggle: () => void; isUrl?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
        {label}
      </label>
      <div className="relative">
        <input
          type={isUrl ? 'url' : (show ? 'text' : 'password')}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          className="w-full px-3 py-2.5 pr-10 rounded-lg text-sm outline-none transition-all settings-input"
          style={{ fontFamily: value && !isUrl ? 'JetBrains Mono, monospace' : 'inherit' }}
        />
        {!isUrl && (
          <button
            type="button"
            onClick={onToggle}
            className="absolute right-3 top-1/2 -translate-y-1/2 transition-opacity hover:opacity-70"
            style={{ color: 'var(--text-secondary)' }}
          >
            {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        )}
      </div>
    </div>
  );
}
