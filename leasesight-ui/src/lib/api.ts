/**
 * api.ts — LeaseSight Frontend API Service v4.0
 *
 * - Free/BYOK users send only their OpenAI key.
 * - Pro/Managed users use server-side OpenAI, Azure, and Pinecone keys.
 * - Catches HTTP 401 responses → redirects to /settings with an "Invalid Key" toast.
 * - All other errors bubble up to the caller.
 */
import { AuditResult, ChatResponse, LocateResponse, GraphData, HealthStatus, CommitResult } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.leasesights.tech';

// ---------------------------------------------------------------------------
// Global Auth Context (Set by AuthGate or on login)
// ---------------------------------------------------------------------------

let globalUserId: string | null = null;
let globalTier: 'BYOK' | 'Managed' | null = null;

export function setApiAuthContext(userId: string | null, tier: 'BYOK' | 'Managed' | null) {
  globalUserId = userId;
  globalTier = tier;
}

// ---------------------------------------------------------------------------
// Key Storage Helpers
// ---------------------------------------------------------------------------

export interface StoredKeys {
  openai: string;
  pinecone: string;
  azureKey: string;
  azureEndpoint: string;
}

export function getStoredKeys(): StoredKeys {
  if (typeof window === 'undefined') return { openai: '', pinecone: '', azureKey: '', azureEndpoint: '' };
  return {
    openai:        localStorage.getItem('ls_openai_key') || '',
    pinecone:      localStorage.getItem('ls_pinecone_key') || '',
    azureKey:      localStorage.getItem('ls_azure_key') || '',
    azureEndpoint: localStorage.getItem('ls_azure_endpoint') || '',
  };
}

export function saveStoredKeys(keys: Partial<StoredKeys>) {
  if (typeof window === 'undefined') return;
  if (keys.openai        !== undefined) localStorage.setItem('ls_openai_key',      keys.openai);
  if (keys.pinecone      !== undefined) localStorage.setItem('ls_pinecone_key',    keys.pinecone);
  if (keys.azureKey      !== undefined) localStorage.setItem('ls_azure_key',       keys.azureKey);
  if (keys.azureEndpoint !== undefined) localStorage.setItem('ls_azure_endpoint',  keys.azureEndpoint);
}

export function hasStoredKeys(): boolean {
  const k = getStoredKeys();
  return !!k.openai;
}

export type SubscriptionTier = 'free' | 'pro';

export function getSelectedTier(): SubscriptionTier | null {
  if (typeof window === 'undefined') return null;
  const tier = localStorage.getItem('ls_subscription_tier');
  return tier === 'free' || tier === 'pro' ? tier : null;
}

export function saveSelectedTier(tier: SubscriptionTier) {
  if (typeof window === 'undefined') return;
  localStorage.setItem('ls_subscription_tier', tier);
  document.cookie = `ls_has_selected_package=true; path=/; max-age=31536000; SameSite=Lax`;
  document.cookie = `ls_subscription_tier=${tier}; path=/; max-age=31536000; SameSite=Lax`;
}

// ---------------------------------------------------------------------------
// Invalid Key Error — carries the backend's detail message
// ---------------------------------------------------------------------------

export class ApiAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiAuthError';
  }
}

// ---------------------------------------------------------------------------
// Core fetch wrapper — ALWAYS injects keys from localStorage, handles 401
// ---------------------------------------------------------------------------

function buildKeyHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  if (globalUserId) {
    headers['X-User-Id'] = globalUserId;
  }

  const selectedTier = getSelectedTier();
  const isByok = globalTier === 'BYOK' || selectedTier === 'free';
  const keys = getStoredKeys();
  if (isByok && keys.openai) {
    headers['X-OpenAI-Key'] = keys.openai;
  }

  return headers;
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const keyHeaders = buildKeyHeaders();

  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...keyHeaders,
      ...(options?.headers || {}),
    },
  });

  // 401 — invalid or missing API key → redirect to settings
  if (res.status === 401) {
    let detail = 'One or more API keys are invalid or missing.';
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore parse error */ }

    if (typeof window !== 'undefined') {
      sessionStorage.setItem('ls_auth_error', detail);
      window.location.href = '/settings';
    }
    throw new ApiAuthError(detail);
  }

  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// API surface
// ---------------------------------------------------------------------------

export const api = {
  testConnection: () => fetchJSON<{ success?: boolean; status?: string; openai?: string; pinecone?: string; message: string }>('/api/test-connection'),

  health: () => fetchJSON<HealthStatus>('/api/health'),

  documents: () => fetchJSON<{ documents: string[]; count: number }>('/api/documents'),

  audit: (file_name: string) =>
    fetchJSON<AuditResult>('/api/audit', {
      method: 'POST',
      body: JSON.stringify({ file_name }),
    }),

  chat: (query: string, file_name: string) =>
    fetchJSON<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ query, file_name }),
    }),

  auditResearch: (file_name: string) =>
    fetchJSON<any>('/api/audit/research', {
      method: 'POST',
      body: JSON.stringify({ file_name }),
    }),

  locate: (file_name: string, snippet: string) =>
    fetchJSON<LocateResponse>('/api/locate', {
      method: 'POST',
      body: JSON.stringify({ file_name, snippet }),
    }),

  commit: (file_name: string, vector_ids?: string[]) =>
    fetchJSON<CommitResult>('/api/commit', {
      method: 'POST',
      body: JSON.stringify({ file_name, vector_ids }),
    }),

  graphData: (file_name: string) =>
    fetchJSON<GraphData>('/api/analytics', {
      method: 'POST',
      body: JSON.stringify({ file_name }),
    }),

  pdfUrl: (filename: string) => `${API_BASE}/pdfs/${encodeURIComponent(filename)}`,

  upload: async (file: File) => {
    const keyHeaders = buildKeyHeaders();
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/upload`, {
      method: 'POST',
      headers: keyHeaders,
      body: formData,
    });
    if (res.status === 401) {
      let detail = 'API key invalid or missing.';
      try { const b = await res.json(); if (b?.detail) detail = b.detail; } catch { /* ignore */ }
      if (typeof window !== 'undefined') { sessionStorage.setItem('ls_auth_error', detail); window.location.href = '/settings'; }
      throw new ApiAuthError(detail);
    }
    if (!res.ok) throw new Error(`Upload error: ${res.status}`);
    return res.json();
  },

  checkIndex: (filename: string) =>
    fetchJSON<{ status: string; was_missing: boolean }>(`/api/index-status/${encodeURIComponent(filename)}`),

  exportAuditPdf: async (filename: string, auditData: AuditResult) => {
    const keyHeaders = buildKeyHeaders();
    const res = await fetch(`${API_BASE}/api/export/${encodeURIComponent(filename)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...keyHeaders },
      body: JSON.stringify(auditData),
    });
    if (!res.ok) throw new Error(`Export error: ${res.status}`);
    return res.blob();
  },

  queryAnalytics: (query: string, file_name: string) =>
    fetchJSON<GraphData>('/api/query-analytics', {
      method: 'POST',
      body: JSON.stringify({ query, file_name }),
    }),

  auditLogUrl: () => `${API_BASE}/api/audit-log`,

  // Migration Pro methods
  startMigration: async (files: File[]) => {
    const keyHeaders = buildKeyHeaders();
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    const res = await fetch(`${API_BASE}/api/migrate/upload`, {
      method: 'POST',
      headers: keyHeaders,
      body: formData,
    });
    if (!res.ok) throw new Error(`Migration upload error: ${res.status}`);
    return res.json();
  },

  getMigrationStatus: (batchId: string) =>
    fetchJSON<{ batch_id: string; total: number; processed: number; status: string; results: any[] }>(`/api/migrate/status/${batchId}`),

  migrationExportUrl: (batchId: string) => `${API_BASE}/api/migrate/export/${batchId}`,

  updateMigrationResult: (resultId: number, data: any) =>
    fetchJSON(`/api/migrate/update/${resultId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  finalizeMigration: async (batchId: string) => {
    const res = await fetch(`${API_BASE}/api/migrate/finalize/${batchId}`, { method: 'POST' });
    if (!res.ok) throw new Error('Finalize failed');
    return res.blob();
  },
};
