'use client';

import { ClerkProvider } from '@clerk/react';
import { AuthGate } from '@/components/AuthGate';
import { ToastProvider } from '@/components/ToastProvider';

export function Providers({ children }: { children: React.ReactNode }) {
  const publishableKey =
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY ||
    process.env.CLERK_PUBLISHABLE_KEY ||
    'pk_test_build';

  return (
    <ClerkProvider publishableKey={publishableKey}>
      <ToastProvider>
        <AuthGate>{children}</AuthGate>
      </ToastProvider>
    </ClerkProvider>
  );
}
