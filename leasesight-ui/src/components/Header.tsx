'use client';

import { useState, useEffect } from 'react';
import { Activity, Search, Zap, Wifi, WifiOff, Network } from 'lucide-react';
import { api } from '@/lib/api';

interface HeaderProps {
  isAuditing: boolean;
  onToggleNetwork: () => void;
}

export function Header({ isAuditing, onToggleNetwork }: HeaderProps) {
  const [health, setHealth] = useState<{ pinecone: string; openai: string } | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
    const interval = setInterval(() => {
      api.health().then(setHealth).catch(() => setHealth(null));
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const isConnected = health?.pinecone === 'connected' && health?.openai === 'connected';

  return (
    <header className="h-12 flex items-center justify-between px-4 border-b glass"
            style={{ borderColor: 'var(--border-default)' }}>
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        <Zap className="w-5 h-5" style={{ color: 'var(--accent-emerald)' }} />
        <span className="font-semibold text-sm tracking-wide" style={{ color: 'var(--text-primary)' }}>
          LEASESIGHT
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: 'rgba(16, 185, 129, 0.15)', color: 'var(--accent-emerald)' }}>
          v2.0
        </span>
      </div>

      {/* Center: Search */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg w-72"
           style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
        <Search className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Search documents...
        </span>
        <span className="ml-auto text-xs px-1.5 py-0.5 rounded"
              style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
          ⌘K
        </span>
      </div>

      {/* Right: Status */}
      <div className="flex items-center gap-4">
        {/* Network Graph Toggle */}
        <button onClick={onToggleNetwork}
                className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-md transition-colors hover:opacity-80"
                style={{ color: 'var(--text-secondary)' }}>
          <Network className="w-3.5 h-3.5" />
          3D Map
        </button>

        {/* Agent Activity */}
        <div className="flex items-center gap-1.5">
          {isAuditing ? (
            <>
              <Activity className="w-3.5 h-3.5 animate-pulse" style={{ color: 'var(--accent-emerald)' }} />
              <span className="text-xs" style={{ color: 'var(--accent-emerald)' }}>Agents Active</span>
            </>
          ) : (
            <>
              <Activity className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Idle</span>
            </>
          )}
        </div>

        {/* System Health */}
        <div className="flex items-center gap-1.5">
          {isConnected ? (
            <>
              <div className="w-2 h-2 rounded-full animate-pulse-dot" style={{ background: 'var(--accent-emerald)' }} />
              <Wifi className="w-3.5 h-3.5" style={{ color: 'var(--accent-emerald)' }} />
            </>
          ) : (
            <>
              <div className="w-2 h-2 rounded-full" style={{ background: 'var(--accent-red)' }} />
              <WifiOff className="w-3.5 h-3.5" style={{ color: 'var(--accent-red)' }} />
            </>
          )}
        </div>
      </div>
    </header>
  );
}
