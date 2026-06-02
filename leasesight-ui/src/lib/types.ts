// API response types
export interface Finding {
  label: string;
  value: string;
  evidence_quote: string;
  verification_status?: string;
  verified?: boolean;
  is_verified?: boolean;
  grounded?: boolean;
  groundedness?: number;
}

export interface Obligation {
  label: string;
  date: string;
  description: string;
}

export interface LiveTrustScores {
  faithfulness: number;
  answer_relevance?: number;
  relevance?: number;
  groundedness_index: number;
  is_trusted?: boolean;
}

export interface AuditResult {
  findings: Finding[];
  obligations?: Obligation[];
  summary_paragraph: string;
  risk_score: number;
  warnings: string[];
  annotations: Annotation[];
  live_trust_scores?: LiveTrustScores;
  coordinates_json?: string;
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
  benchmark_score?: number;
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

export interface EvaluationMetrics {
  faithfulness: number;
  answer_relevance: number;
  context_recall: number;
}

export interface AcademicBenchmark {
  paper_title: string;
  precision: number;
  recall: number;
  f1_score: number;
  paper_f1_score: number;
  leasesight_f1_score: number;
}

export interface FailedCase {
  user_query: string;
  generated_output: string;
  failure_reason: 'OCR_ERROR' | 'RETRIEVAL_ERROR' | 'GENERATION_ERROR' | string;
}

export interface EvaluationSummary {
  status: string;
  deepeval_metrics: EvaluationMetrics;
  academic_benchmark: AcademicBenchmark;
  failed_cases: FailedCase[];
}
