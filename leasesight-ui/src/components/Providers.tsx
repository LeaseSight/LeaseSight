'use client';

import { useEffect, useState } from 'react';
import { ClerkProvider } from '@clerk/react';
import { AuthGate } from '@/components/AuthGate';
import { ToastProvider } from '@/components/ToastProvider';

/** Azure static build only when .env.production is sourced before `npm run build`. */
const BUILD_PLACEHOLDER_KEY = 'pk_test_build';

function resolvePublishableKey(): string {
  const fromEnv =
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || process.env.CLERK_PUBLISHABLE_KEY || '';
  if (fromEnv) return fromEnv;
  if (process.env.NEXT_PHASE === 'phase-production-build' && process.env.VERCEL !== '1') {
    return BUILD_PLACEHOLDER_KEY;
  }
  return '';
}

function isLocalDevHost(): boolean {
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname;
  return host === 'localhost' || host === '127.0.0.1';
}

export function Providers({ children }: { children: React.ReactNode }) {
  const publishableKey = resolvePublishableKey();
  const [liveKeyOnLocalhost, setLiveKeyOnLocalhost] = useState(false);

  useEffect(() => {
    if (publishableKey.startsWith('pk_live_') && isLocalDevHost()) {
      setLiveKeyOnLocalhost(true);
    }
  }, [publishableKey]);

  if (liveKeyOnLocalhost) {
    return (
      <ToastProvider>
        <div className="flex min-h-screen items-center justify-center bg-[#F9FAFB] px-6 text-center">
          <div className="max-w-lg space-y-4">
            <h1 className="text-xl font-semibold text-[#1A1A1A]">Use test keys on localhost</h1>
            <p className="text-sm leading-7 text-slate-600">
              Put <code className="text-[#1A1A1A]">pk_test_</code> in{' '}
              <code className="text-[#1A1A1A]">leasesight-ui/.env.local</code>. Reserve{' '}
              <code className="text-[#1A1A1A]">pk_live_</code> for Vercel / production only.
            </p>
          </div>
        </div>
      </ToastProvider>
    );
  }

  if (!publishableKey) {
    return (
      <ToastProvider>
        <div className="flex min-h-screen items-center justify-center bg-[#F9FAFB] px-6 text-center">
          <div className="max-w-lg space-y-4 text-sm text-slate-600">
            <h1 className="text-xl font-semibold text-[#1A1A1A]">Clerk not configured</h1>
            <p>
              <strong>On Vercel:</strong> Project → Settings → Environment Variables → add{' '}
              <code className="text-[#1A1A1A]">NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code> (your{' '}
              <code className="text-[#1A1A1A]">pk_live_</code> key), enable Production + Preview,
              then <strong>Redeploy</strong>.
            </p>
            <p>
              <strong>Local:</strong> add the same variable to{' '}
              <code className="text-[#1A1A1A]">leasesight-ui/.env.local</code> using{' '}
              <code className="text-[#1A1A1A]">pk_test_</code> keys.
            </p>
            <p className="text-xs text-slate-500">
              Vercel never reads <code className="text-[#1A1A1A]">.env.local</code> from git — you
              must set variables in the dashboard.
            </p>
          </div>
        </div>
      </ToastProvider>
    );
  }

  return (
    <ClerkProvider publishableKey={publishableKey}>
      <ToastProvider>
        <AuthGate>{children}</AuthGate>
      </ToastProvider>
    </ClerkProvider>
  );
}
