'use client';

import { useAuth, SignInButton } from '@clerk/react';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { Loader2, ShieldAlert } from 'lucide-react';
import { setApiAuthContext } from '@/lib/api';

function hasSelectedPackage(): boolean {
  if (typeof document === 'undefined') return false;
  return document.cookie.split(';').some(c => c.trim() === 'ls_has_selected_package=true');
}

function isPublicPath(pathname: string): boolean {
  if (pathname === '/' || pathname === '/pricing') return true;
  if (pathname === '/login' || pathname.startsWith('/login/')) return true;
  return false;
}

function isProtectedPath(pathname: string): boolean {
  return pathname.startsWith('/dashboard') || pathname.startsWith('/settings');
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { isLoaded, userId } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = isPublicPath(pathname);
  const isProtected = isProtectedPath(pathname);
  const isPackageRoute = pathname.startsWith('/choose-package');

  useEffect(() => {
    if (!isLoaded) return;

    setApiAuthContext(userId);

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
  }, [isLoaded, userId, pathname, router, isProtected, isPackageRoute]);

  if (!isLoaded && (isProtected || isPackageRoute)) {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center bg-[#F9FAFB]">
        <Loader2 className="mb-4 h-8 w-8 animate-spin text-[#1A1A1A]" />
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Loading session…</p>
      </div>
    );
  }

  if (
    isLoaded &&
    !userId &&
    (isProtected || isPackageRoute)
  ) {
    return (
      <div className="flex h-screen w-screen flex-col items-center justify-center bg-[#F9FAFB] p-8 text-center">
        <ShieldAlert className="mb-6 h-12 w-12 text-[#1A1A1A]" />
        <h2 className="mb-2 text-2xl font-semibold text-[#1A1A1A]">Sign in required</h2>
        <p className="mb-8 max-w-sm text-sm text-slate-500">
          Sign in to access the audit dashboard, migration tools, and settings.
        </p>
        <SignInButton mode="modal">
          <button className="bg-[#1A1A1A] px-8 py-3 text-sm font-semibold text-white transition hover:bg-slate-700">
            Sign In
          </button>
        </SignInButton>
      </div>
    );
  }

  return <>{children}</>;
}
