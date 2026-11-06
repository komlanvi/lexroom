import type { FailureReason, Plan, WorkspaceDocument } from "./api";
import { formatDay, formatDayTime, formatElapsed, formatPeriod } from "./format";

export type Tone = "neutral" | "active" | "success" | "danger";

export interface Badge {
  tone: Tone;
  label: string;
  /** A second line, e.g. that an earlier result is still available. */
  note?: string;
}

export const FAILURE_REASON_LABELS: Record<FailureReason, string> = {
  ai_error: "AI error",
  timed_out: "time limit",
};

/**
 * The latest-review badge of a document in the list (UI state matrix, "Document badge").
 * `now` is used for the elapsed time of a running review.
 */
export function documentBadge(document: WorkspaceDocument, lawyerNames: Record<string, string>, now: Date): Badge {
  const latest = document.latest_review;
  const result = document.current_result;

  if (latest === null) {
    return { tone: "neutral", label: "Not reviewed" };
  }

  if (latest.status === "running") {
    const elapsed = (now.getTime() - new Date(latest.requested_at).getTime()) / 1000;
    return {
      tone: "active",
      label: `In progress · ${formatElapsed(Math.min(elapsed, 60))} · by ${lawyerNames[latest.requested_by] ?? "unknown"}`,
      note: result ? `Previous result from ${formatDay(result.finished_at)}` : undefined,
    };
  }

  if (latest.status === "completed") {
    const count = result?.review_id === latest.id ? result.findings_count : 0;
    const findings = count === 0 ? "no clauses flagged" : count === 1 ? "1 finding" : `${count} findings`;
    return { tone: "success", label: `Completed ${formatDay(latest.finished_at ?? latest.requested_at)} · ${findings}` };
  }

  const reason = latest.failure_reason ? FAILURE_REASON_LABELS[latest.failure_reason] : "unknown";
  const failedOn = formatDay(latest.finished_at ?? latest.requested_at);
  if (result) {
    return {
      tone: "danger",
      label: `Last attempt failed (${reason}) ${failedOn}`,
      note: `Result from ${formatDay(result.finished_at)} available`,
    };
  }
  return { tone: "danger", label: `Failed (${reason}) ${failedOn} · no result yet` };
}

/** "Previous version · superseded by the version of 24 Sep", or null for a current document. */
export function supersededLabel(document: WorkspaceDocument, documents: WorkspaceDocument[]): string | null {
  if (document.superseded_by === null) return null;
  const newer = documents.find((candidate) => candidate.id === document.superseded_by);
  return newer
    ? `Previous version · superseded by the version of ${formatDay(newer.uploaded_at)}`
    : "Previous version";
}

export interface PlanSummary {
  headline: string;
  resets: string;
  exhausted: boolean;
}

/** Header plan counter: "Plan · November: 6 of 10 available · 1 running", "Resets 1 Dec, 00:00 Rome time". */
export function planSummary(plan: Plan): PlanSummary {
  return {
    headline: `Plan · ${formatPeriod(plan.period)}: ${plan.available} of ${plan.limit} available · ${plan.running} running`,
    resets: `Resets ${formatDayTime(plan.resets_at)} Rome time`,
    exhausted: plan.available === 0,
  };
}

export function anyRunning(documents: WorkspaceDocument[]): boolean {
  return documents.some((document) => document.latest_review?.status === "running");
}
