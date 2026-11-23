export interface User {
  id: string;
  email: string;
}

export interface AuthResponse {
  user_id: string;
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at?: string;
  question_count?: number;
  reference_count?: number;
}

export interface DocumentItem {
  id: string;
  project_id: string;
  title: string;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  sha256: string;
  status: "EXTRACTING" | "REVIEW_REQUIRED" | "READY" | "FAILED";
  extraction_warnings: string[];
}

export interface UnitItem {
  id: string;
  document_id: string;
  name: string;
  position: number;
}

export type QuestionStatus =
  | "PENDING"
  | "QUEUED"
  | "GENERATING"
  | "VERIFYING"
  | "REVISING"
  | "RETRY_WAIT"
  | "VERIFIER_APPROVED"
  | "MANUAL_REVIEW"
  | "FAILED"
  | "CANCELLED";

export interface QuestionItem {
  id: string;
  project_id?: string;
  document_id?: string;
  unit_id?: string | null;
  position: number;
  question_number?: string | null;
  section?: string | null;
  question_text: string;
  original_text?: string | null;
  marks?: number | null;
  bl?: string | null;
  co?: string | null;
  source_page_start?: number | null;
  source_page_end?: number | null;
  source_excerpt?: string | null;
  extraction_confidence?: number | null;
  status: QuestionStatus;
}

export interface ReferenceExcerptItem {
  id: string;
  title: string;
  text: string;
  source_label: string;
  page?: number | null;
}

export interface AnswerSection {
  heading: string;
  content: string;
  bullets: string[];
  formula?: string | null;
  example?: string | null;
}

export interface AnswerContent {
  introduction: string;
  sections: AnswerSection[];
  conclusion: string;
  diagram_source?: string | null;
}

export type CriterionStatus = "pass" | "fail" | "uncertain";
export type IssueSeverity = "critical" | "major" | "minor" | "suggestion";

export interface Criterion {
  name: string;
  status: CriterionStatus;
  notes: string;
}

export interface VerificationIssue {
  severity: IssueSeverity;
  category: string;
  description: string;
  required_action: string;
}

export interface VerificationReport {
  verdict: "approved" | "needs_revision";
  criteria: Criterion[];
  issues: VerificationIssue[];
  evidence_notes: string[];
  confidence: number | null;
}

export interface HumanDecisionRecord {
  id?: string;
  answer_version_id: string;
  decision: "APPROVED" | "REJECTED";
  reviewer_id?: string;
  created_at: string;
}

export interface AnswerVersionItem {
  id: string;
  version_number: number;
  answer: AnswerContent;
  provider?: string | null;
  model?: string | null;
  created_at: string;
  verifier_report?: VerificationReport | null;
  human_approvals?: Array<{
    decision: "APPROVED" | "REJECTED";
    reviewer_id: string;
    created_at: string;
  }>;
}

export interface LatestAnswerResponse {
  question_id: string;
  answer_version_id: string;
  version_number: number;
  answer: AnswerContent;
  provider?: string | null;
  model?: string | null;
  created_at: string;
  verifier_report?: VerificationReport | null;
  latest_human_decision?: "APPROVED" | "REJECTED" | null;
}

export interface ProcessingJobItem {
  id: string;
  question_id: string;
  status: QuestionStatus;
  revision_count: number;
  retry_count: number;
  started_at?: string | null;
  finished_at?: string | null;
  cancel_requested_at?: string | null;
  last_error_code?: string | null;
  last_error_message?: string | null;
}

export interface ProcessingRunResponse {
  id: string;
  project_id: string;
  idempotency_key: string;
  jobs: ProcessingJobItem[];
}

export interface ProgressCounts {
  PENDING: number;
  QUEUED: number;
  GENERATING: number;
  VERIFYING: number;
  REVISING: number;
  VERIFIER_APPROVED: number;
  MANUAL_REVIEW: number;
  FAILED: number;
  CANCELLED: number;
}

export interface DocumentProgressResponse {
  document_id: string;
  total: number;
  completed: number;
  percent: number;
  counts: ProgressCounts;
}

export interface DuplicateItem {
  question_id_1: string;
  question_id_2: string;
  text_1: string;
  text_2: string;
  similarity: number;
  reason: string;
}

export interface ExportResponse {
  id: string;
  document_id: string;
  format: "pdf" | "docx" | "md" | "json";
  status: "COMPLETED" | "FAILED" | "PENDING";
  file_size_bytes?: number;
  sha256?: string;
  created_at?: string;
  error_message?: string | null;
}
