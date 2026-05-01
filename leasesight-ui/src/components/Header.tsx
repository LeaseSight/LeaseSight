'use client';

import { useState, useEffect } from 'react';
import { Activity, Search, Zap, Wifi, WifiOff, Network } from 'lucide-react';
import { api } from '@/lib/api';

interface HeaderProps {
  isAuditing: boolean;
  onToggleNetwork: () => void;
  documents: string[];
  onSelectDoc: (doc: string) => void;
}

export function Header({ isAuditing, onToggleNetwork, documents, onSelectDoc }: HeaderProps) {
  const [health, setHealth] = useState<{ pinecone: string; openai: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);

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
      <div className="relative">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg w-72"
             style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
          <Search className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
          <input 
            type="text"
            placeholder="Search documents..."
            className="text-xs bg-transparent outline-none flex-1"
            style={{ color: 'var(--text-primary)' }}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setIsSearchFocused(true)}
            onBlur={() => setTimeout(() => setIsSearchFocused(false), 200)}
          />
          <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded"
                style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
            ⌘K
          </span>
        </div>
        {isSearchFocused && searchQuery && (
          <div className="absolute top-full mt-1 w-full rounded-lg shadow-lg overflow-hidden z-50 border"
               style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}>
            {documents.filter(d => d.toLowerCase().includes(searchQuery.toLowerCase())).slice(0, 5).map(doc => (
              <button
                key={doc}
                onMouseDown={() => {
                  onSelectDoc(doc);
                  setSearchQuery('');
                  setIsSearchFocused(false);
                }}
                className="w-full text-left px-3 py-2 text-xs transition-colors truncate"
                style={{ color: 'var(--text-primary)', background: 'var(--bg-card)' }}
              >
                {doc}
              </button>
            ))}
          </div>
        )}
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
