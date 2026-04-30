import { AuditResult, ChatResponse, LocateResponse, GraphData, HealthStatus, CommitResult } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

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
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: formData });
    if (!res.ok) throw new Error(`Upload error: ${res.status}`);
    return res.json();
  },
};
