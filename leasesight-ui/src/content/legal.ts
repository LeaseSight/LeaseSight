export type LegalPanel = 'terms' | 'privacy' | 'documentation';

export const LEGAL_PANELS: Record<
  LegalPanel,
  { title: string; subtitle: string; sections: { heading: string; body: string[] }[] }
> = {
  terms: {
    title: 'Terms of Service',
    subtitle: 'LeaseSight Technologies — Effective June 2026',
    sections: [
      {
        heading: '1. Service Scope',
        body: [
          'LeaseSight provides automated legal document parsing, clause extraction, compliance heuristics, and structured audit outputs for commercial lease and logistics contracts. The platform is designed to assist qualified reviewers; it does not provide legal advice, establish attorney-client relationships, or replace licensed counsel.',
          'By accessing LeaseSight, you agree that all outputs are computational interpretations of source documents and must be validated by your organization before reliance in transactions, filings, or disputes.',
        ],
      },
      {
        heading: '2. Automated Compliance & Liability Limits',
        body: [
          'Automated compliance checking applies rule-based and model-inferred signals against configurable matrices (including multi-point validation schemas). LeaseSight does not warrant completeness, accuracy, or fitness for a particular regulatory regime.',
          'To the maximum extent permitted by law, LeaseSight Technologies and its affiliates disclaim liability for indirect, incidental, consequential, or punitive damages arising from missed clauses, OCR errors, embedding drift, model hallucinations, or delayed pipeline execution. Aggregate direct liability is limited to fees paid in the twelve (12) months preceding the claim.',
        ],
      },
      {
        heading: '3. Groq / LPU API Transport',
        body: [
          'Structured verification and JSON ingestion may invoke Groq-hosted inference on Language Processing Unit (LPU) hardware. You authorize transient transmission of redacted or full text segments strictly necessary for inference, subject to provider terms and our data-processing addendum.',
          'You must not submit unlawfully obtained materials, privileged communications without waiver, or content violating export-control or sanctions rules. LeaseSight may throttle, queue, or suspend requests that exceed fair-use thresholds or threaten platform stability.',
        ],
      },
      {
        heading: '4. Data Processing Thresholds',
        body: [
          'Per-tenant ingestion limits, concurrent audit jobs, and API rate caps apply by subscription tier. Background workers may dequeue large PDF batches asynchronously; browser sessions must not assume synchronous completion for documents exceeding published size or page thresholds.',
          'LeaseSight may log operational metadata (timestamps, job IDs, token counts, error codes) for reliability and billing. Contract body text retention follows the Privacy Policy unless you enable optional encrypted local indexes.',
        ],
      },
      {
        heading: '5. Jurisdiction & Dispute Resolution',
        body: [
          'These Terms are governed by the laws of the State of Delaware, United States, without regard to conflict-of-law principles. Exclusive venue for disputes shall be state or federal courts located in Wilmington, Delaware, except where mandatory consumer protections require otherwise.',
          'If any provision is held unenforceable, remaining provisions continue in full force. Continued use after policy updates constitutes acceptance of revised Terms posted in-product with a revised effective date.',
        ],
      },
    ],
  },
  privacy: {
    title: 'Privacy Policy',
    subtitle: 'LeaseSight Technologies — Data Handling & Retention',
    sections: [
      {
        heading: '1. Principles',
        body: [
          'LeaseSight processes contract data to deliver audit, migration, and research features. We minimize collection, default to ephemeral handling for uploaded PDFs, and segregate customer workspaces by authenticated identity.',
        ],
      },
      {
        heading: '2. In-Memory PDF Pipeline',
        body: [
          'Uploaded contract PDFs are read into process memory only. The pipeline: (a) receive bytes over TLS; (b) hold the file in a bounded memory buffer; (c) stream pages to Azure Form Recognizer for OCR layout extraction; (d) discard raw bytes after chunking unless you explicitly persist to an encrypted local vector index.',
          'No contract PDF is written to shared object storage by default. Crash recovery buffers are cleared on process exit. Temporary OCR JSON exists only for the duration of the active job worker.',
        ],
      },
      {
        heading: '3. Third-Party Inference & Zero Retention',
        body: [
          'Groq LPU endpoints and Google Vertex AI (when configured) receive only the minimum text spans required for structured JSON verification. Under our vendor configuration, inference payloads are not used for model training and are not retained beyond the provider\'s transient execution window (typically seconds).',
          'API keys for third-party services are server-held; they are never exposed to browser clients. You may disable cloud inference and rely solely on local embedding and rules-only modes where supported.',
        ],
      },
      {
        heading: '4. Local Vector Index Encryption',
        body: [
          'Sentence embeddings produced by the local all-mpnet-base-v2 model (768 dimensions) may be stored in an on-device or tenant-scoped vector index. Index files are encrypted at rest using AES-256 with keys derived from your session or machine-bound secret material.',
          'Similarity search executes locally on laptop or server threads; vectors are not uploaded to Pinecone or other cloud vector stores unless you opt into managed archive features on eligible plans.',
        ],
      },
      {
        heading: '5. Your Rights',
        body: [
          'You may request export or deletion of account metadata and optional persisted indexes. Contact privacy@leasesight.com for data subject requests. We will verify identity before fulfilling deletion within applicable statutory timelines.',
        ],
      },
    ],
  },
  documentation: {
    title: 'Documentation',
    subtitle: 'LeaseSight ingestion & verification pipeline',
    sections: [
      {
        heading: 'Step 1 — Azure Form Recognizer OCR',
        body: [
          'Documents enter through the audit or migration upload surface. The backend submits each PDF to Azure Document Intelligence (Form Recognizer) with layout-aware OCR. Output includes page-level text, tables, selection marks, and bounding polygons used later for verbatim visual grounding in the review UI.',
          'Configure endpoint and key in server environment variables. Failures surface as retryable job states; partial pages are flagged for manual re-upload.',
        ],
      },
      {
        heading: 'Step 2 — Local all-mpnet-base-v2 Embeddings',
        body: [
          'Extracted clauses are chunked (typically 400–800 tokens with overlap). Each chunk is encoded with sentence-transformers/all-mpnet-base-v2 producing 768-dimensional dense vectors. Encoding runs on local CPU/GPU threads—no per-token cloud embedding fees.',
          'Vectors populate an encrypted local index for cosine similarity retrieval, enabling RAG-style Q&A and precedent matching without shipping full contracts to external vector databases.',
        ],
      },
      {
        heading: 'Step 3 — Multi-Agent Llama-3.3-70B Verification',
        body: [
          'Retrieved spans feed a multi-agent loop on Groq (Llama-3.3-70B) with LPU acceleration. Agents emit structured JSON aligned to a 20-point validation matrix (parties, term, rent, CAM, insurance, indemnity, default, governing law, etc.).',
          'A critic agent reconciles conflicts; the orchestrator merges final fields with confidence scores and source quotes. Results render in the audit dashboard with PDF highlight coordinates. Large jobs run asynchronously via background workers to avoid browser proxy timeouts.',
        ],
      },
      {
        heading: 'Operations Checklist',
        body: [
          'Ensure Azure OCR credentials, Groq API key, and Clerk authentication are configured. Start an audit from Dashboard → Audit, upload a PDF, monitor job status, then review JSON findings with evidence links. For bulk migration, use Dashboard → Migrate with batch queueing enabled.',
        ],
      },
    ],
  },
};
