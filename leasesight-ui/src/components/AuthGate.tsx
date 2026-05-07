'use client';

import { useAuth, useUser, SignInButton } from '@clerk/nextjs';
import { useRouter, usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { Loader2, ShieldAlert } from 'lucide-react';
import { setApiAuthContext } from '@/lib/api';

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { isLoaded, userId } = useAuth();
  const { user } = useUser();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoaded) {
      // Set the API context based on the user's metadata (provided by Clerk)
      const tier = (user && user.publicMetadata) ? (user.publicMetadata.tier as 'BYOK' | 'Managed') : undefined;
      setApiAuthContext(userId, tier || 'Managed'); // Fallback to Managed for current testing

      // IF logged in but no tier explicitly set, and trying to go to dashboard
      // FORCE them to visit pricing first
      if (userId && !tier && pathname.startsWith('/dashboard')) {
        router.push('/pricing');
      }
    }
    
    if (isLoaded && !userId && pathname !== '/' && pathname !== '/pricing') {
      // Allow landing and pricing, but protect dashboard
      if (pathname.startsWith('/dashboard')) {
        router.push('/');
      }
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

  // If on a protected route and not logged in
  if (!userId && pathname.startsWith('/dashboard')) {
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
