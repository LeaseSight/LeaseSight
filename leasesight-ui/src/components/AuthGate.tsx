'use client';

import { useAuth, SignInButton } from '@clerk/nextjs';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { Loader2, ShieldAlert } from 'lucide-react';
import { setApiAuthContext } from '@/lib/api';

function hasSelectedPackage(): boolean {
  if (typeof document === 'undefined') return false;
  return document.cookie.split(';').some(c => c.trim() === 'ls_has_selected_package=true');
}

const PUBLIC_PATHS = ['/', '/pricing', '/login'];

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { isLoaded, userId } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoaded) return;

    setApiAuthContext(userId);

    const isProtected =
      pathname.startsWith('/dashboard') || pathname.startsWith('/settings');
    const isPackageRoute = pathname.startsWith('/choose-package');

    if (!userId) {
      if (isProtected || isPackageRoute) {
        router.replace('/login');
      }
      return;
    }

    if (isPackageRoute && hasSelectedPackage()) {
      router.replace('/dashboard/audit');
      return;
    }

    if (isProtected && !hasSelectedPackage()) {
      router.replace(`/choose-package?returnTo=${encodeURIComponent(pathname)}`);
    }
  }, [isLoaded, userId, pathname, router]);

  if (!isLoaded) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-[#030712]">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500 mb-4" />
        <p className="text-xs font-mono text-white/30 uppercase tracking-[0.3em]">Authenticating Node...</p>
      </div>
    );
  }

  if (
    !userId &&
    (pathname.startsWith('/dashboard') || pathname.startsWith('/settings') || pathname.startsWith('/choose-package'))
  ) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-[#030712] p-8 text-center">
        <ShieldAlert className="w-12 h-12 text-red-500 mb-6" />
        <h2 className="text-2xl font-bold text-white mb-2">Access Restricted</h2>
        <p className="text-white/50 max-w-sm mb-8">
          The LeaseSight workstation requires a secure session. Please sign in to access the Auditor and Migration engines.
        </p>
        <SignInButton mode="modal">
          <button className="px-8 py-4 rounded-2xl bg-white text-black font-bold hover:scale-105 transition-transform">
            Sign In with GitHub
          </button>
        </SignInButton>
      </div>
    );
  }

  return <>{children}</>;
}
