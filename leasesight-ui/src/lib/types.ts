// API response types
export interface Finding {
  label: string;
  value: string;
  evidence_quote: string;
}

export interface AuditResult {
  findings: Finding[];
  summary_paragraph: string;
  risk_score: number;
  warnings: string[];
  annotations: Annotation[];
}

export interface Annotation {
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  source_text?: string | null;
  page?: number | null;
  annotation?: Annotation | null;
}

export interface ChatResponse {
  answer: string;
  source_text: string | null;
  page: number | null;
  annotation: Annotation | null;
}

export interface LocateResponse {
  found: boolean;
  page: number | null;
  annotation: Annotation | null;
}

export interface GraphData {
  archive_coords: number[][];
  new_coords: number[];
  names: string[];
  sufficient: boolean;
  internal_similarities?: number[];
}

export interface HealthStatus {
  status: string;
  pinecone: string;
  openai: string;
}

export interface CommitResult {
  success: boolean;
  message: string;
  moved: boolean;
  vectors_updated: number;
}
