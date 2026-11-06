export type ReviewStatus = "running" | "completed" | "failed";
export type FailureReason = "ai_error" | "timed_out";
export type Severity = "high" | "medium" | "low";

export interface Lawyer {
  id: string;
  name: string;
  title: string;
}

export interface Plan {
  limit: number;
  completed: number;
  running: number;
  available: number;
  period: string;
  resets_at: string;
}

export interface ReviewSummary {
  id: string;
  status: ReviewStatus;
  failure_reason: FailureReason | null;
  requested_by: string;
  requested_at: string;
  deadline_at: string;
  finished_at: string | null;
}

export interface ReviewResult {
  review_id: string;
  finished_at: string;
  findings_count: number;
}

export interface WorkspaceDocument {
  id: string;
  title: string;
  type: string;
  pages: number;
  uploaded_at: string;
  uploaded_by: string;
  supersedes: string | null;
  superseded_by: string | null;
  latest_review: ReviewSummary | null;
  current_result: ReviewResult | null;
}

export interface Finding {
  seq: number;
  clause: string | null;
  title: string;
  severity: Severity;
  excerpt: string | null;
  explanation: string;
}

export interface Review extends ReviewSummary {
  document_id: string;
  server_now: string;
  is_final: boolean;
  findings: Finding[];
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: Record<string, unknown>,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { cache: "no-store", ...init });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(
      response.status,
      body?.code ?? "UNKNOWN_ERROR",
      body?.message ?? response.statusText,
      body?.details ?? {},
    );
  }
  return body as T;
}

export const api = {
  lawyers: () => call<Lawyer[]>("/lawyers"),
  plan: () => call<Plan>("/plan"),
  documents: () => call<WorkspaceDocument[]>("/documents"),
  document: (id: string) => call<WorkspaceDocument>(`/documents/${id}`),
  review: (id: string) => call<Review>(`/reviews/${id}`),
  requestReview: (documentId: string, lawyerId: string) =>
    call<Review>(`/documents/${documentId}/reviews`, {
      method: "POST",
      headers: { "X-Lawyer-Id": lawyerId },
    }),
};
