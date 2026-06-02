'use client';

import { ClerkProvider } from '@clerk/react';
import { AuthGate } from '@/components/AuthGate';
import { ToastProvider } from '@/components/ToastProvider';

/** Placeholder only for `next build` static export when env is injected on the server. */
const BUILD_PLACEHOLDER_KEY = 'pk_test_build';

function resolvePublishableKey(): string {
  const fromEnv =
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || process.env.CLERK_PUBLISHABLE_KEY || '';
  if (fromEnv) return fromEnv;
  if (process.env.NEXT_PHASE === 'phase-production-build') return BUILD_PLACEHOLDER_KEY;
  return '';
}

export function Providers({ children }: { children: React.ReactNode }) {
  const publishableKey = resolvePublishableKey();

  if (!publishableKey) {
    return (
      <ToastProvider>
        <div className="flex min-h-screen items-center justify-center bg-[#F9FAFB] px-6 text-center">
          <p className="max-w-md text-sm text-slate-600">
            Missing <code className="text-[#1A1A1A]">NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code> in{' '}
            <code className="text-[#1A1A1A]">leasesight-ui/.env.local</code>.
          </p>
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
