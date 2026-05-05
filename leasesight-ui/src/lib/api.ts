/**
 * api.ts — LeaseSight Frontend API Service v3.0
 *
 * - Reads API keys from localStorage and injects them as headers on every request.
 * - Catches HTTP 401 responses → redirects to /settings with an "Invalid Key" toast.
 * - All other errors bubble up to the caller.
 */
import { AuditResult, ChatResponse, LocateResponse, GraphData, HealthStatus, CommitResult } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  return !!(k.openai && k.pinecone);
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
// Core fetch wrapper — injects headers, handles 401
// ---------------------------------------------------------------------------

function buildKeyHeaders(): Record<string, string> {
  const keys = getStoredKeys();
  const headers: Record<string, string> = {};
  if (keys.openai)        headers['X-OpenAI-Key']      = keys.openai;
  if (keys.pinecone)      headers['X-Pinecone-Key']    = keys.pinecone;
  if (keys.azureKey)      headers['X-Azure-Key']       = keys.azureKey;
  if (keys.azureEndpoint) headers['X-Azure-Endpoint']  = keys.azureEndpoint;
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

  // 401 — invalid or missing API key
  if (res.status === 401) {
    let detail = 'One or more API keys are invalid or missing.';
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch { /* ignore parse error */ }

    // Store the message for the Settings page to display
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

  pdfUrl: (filename: string) => `${API_BASE}/api/pdf/${encodeURIComponent(filename)}`,

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
};
