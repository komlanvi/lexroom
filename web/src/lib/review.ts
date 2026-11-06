import { ApiError, type Finding, type Plan, type Review, type ReviewSummary, type Severity } from "./api";
import { firstName, formatDateTime, formatElapsed, formatPeriod, formatTime } from "./format";

const LIMIT_S = 60;
const DAY_MS = 24 * 60 * 60 * 1000;

/** Severity is always shown with text and an icon, never colour alone. */
export const SEVERITY_LABELS: Record<Severity, { icon: string; label: string }> = {
  high: { icon: "▲", label: "High" },
  medium: { icon: "■", label: "Medium" },
  low: { icon: "●", label: "Low" },
};

const SEVERITY_ORDER: Severity[] = ["high", "medium", "low"];
const clauseCollator = new Intl.Collator("en", { numeric: true });

export function clauseLabel(clause: string | null): string {
  return clause === null ? "General (no specific clause)" : `Clause ${clause}`;
}

/** BR-17: high → medium → low, then natural clause order ("4.2" before "12.1"), "General" last. */
export function sortFindings(findings: Finding[]): Finding[] {
  return [...findings].sort(
    (a, b) =>
      SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity) ||
      compareClauses(a.clause, b.clause),
  );
}

function compareClauses(a: string | null, b: string | null): number {
  if (a === null || b === null) return Number(a === null) - Number(b === null);
  return clauseCollator.compare(a, b);
}

/** Seconds since the request, on the server clock (edge case 21), never more than the limit. */
export function elapsedSeconds(review: Review): number {
  const elapsed = (new Date(review.server_now).getTime() - new Date(review.requested_at).getTime()) / 1000;
  return Math.min(elapsed, LIMIT_S);
}

/**
 * What the review panel shows, top to bottom (BR-15 to BR-18, decisions 1 and 2).
 * `result` is the document's current result: its latest completed review.
 */
export type PanelSection =
  | { kind: "not-reviewed" }
  | { kind: "live"; review: Review }
  | { kind: "previous"; review: Review }
  | { kind: "final"; review: Review }
  | { kind: "failed"; review: Review; hasResult: boolean }
  | { kind: "no-result" };

export function panelSections(latest: Review | null, result: Review | null): PanelSection[] {
  if (latest === null) return [{ kind: "not-reviewed" }];
  if (latest.status === "running") {
    return result ? [{ kind: "live", review: latest }, { kind: "previous", review: result }] : [{ kind: "live", review: latest }];
  }
  if (latest.status === "completed") return [{ kind: "final", review: latest }];
  return [
    { kind: "failed", review: latest, hasResult: result !== null },
    result ? { kind: "final", review: result } : { kind: "no-result" },
  ];
}

/** BR-16: a failed review is shown as a status only. */
export function failureMessage(review: Review, lawyerNames: Record<string, string>): string {
  const requested = `requested by ${requesterName(review, lawyerNames)} at ${formatTime(review.requested_at)}`;
  if (review.failure_reason === "ai_error") {
    const seconds = Math.round((new Date(review.finished_at!).getTime() - new Date(review.requested_at).getTime()) / 1000);
    return `The AI returned an error after ${seconds} s (${requested}).`;
  }
  return `No result within ${LIMIT_S} seconds (${requested}).`;
}

export function requesterName(review: ReviewSummary, lawyerNames: Record<string, string>): string {
  return firstName(lawyerNames[review.requested_by] ?? "unknown");
}

export interface RequestState {
  label: string;
  enabled: boolean;
  /** Why the button is disabled, one paragraph per line. */
  explanation: string[];
}

/** The request button, in the priority order of the UI state matrix. */
export function requestState({
  latest,
  hasResult,
  plan,
  requesting,
  lawyerNames,
  now,
}: {
  latest: Review | null;
  hasResult: boolean;
  plan: Plan;
  requesting: boolean;
  lawyerNames: Record<string, string>;
  now: Date;
}): RequestState {
  if (latest?.status === "running") {
    const by = requesterName(latest, lawyerNames);
    return { label: `Review in progress (by ${by}, ${formatElapsed(elapsedSeconds(latest))})`, enabled: false, explanation: [] };
  }
  if (plan.available === 0 && plan.running > 0) {
    return {
      label: "Request review",
      enabled: false,
      explanation: [
        "No review can be started right now.",
        `This month: ${plan.completed} completed + ${plan.running} in progress = all ${plan.limit} reviews in use.`,
        `Each review in progress holds one of the ${plan.limit} reviews until it finishes: if it completes, that review is used; ` +
          `if it fails or takes longer than ${LIMIT_S} seconds, it is not counted and becomes available again (within ${LIMIT_S} seconds at most).`,
        "This request has not been saved and will not start on its own. " +
          "This button becomes active again automatically if a review becomes available.",
      ],
    };
  }
  if (plan.available === 0) {
    const days = Math.ceil((new Date(plan.resets_at).getTime() - now.getTime()) / DAY_MS);
    return {
      label: "Request review",
      enabled: false,
      explanation: [
        `The workspace has used its ${plan.limit} reviews for ${formatPeriod(plan.period)}.`,
        `Reviews are available again on ${formatDateTime(plan.resets_at)} Rome time (in ${days} ${days === 1 ? "day" : "days"}).`,
        "No new review can be started until then.",
      ],
    };
  }
  if (requesting) return { label: "Requesting…", enabled: false, explanation: [] };
  if (latest?.status === "failed") return { label: "Retry review", enabled: true, explanation: [] };
  if (hasResult) return { label: "Request a new review", enabled: true, explanation: [] };
  return { label: "Request review", enabled: true, explanation: [] };
}

/** BR-13: the cost and the remaining plan, shown before every request. */
export function confirmationLines(plan: Plan): string[] {
  const month = formatPeriod(plan.period);
  const cost =
    plan.available === 1
      ? `If it completes, it uses 1 of the workspace's ${plan.limit} ${month} reviews. ` +
        "This is the last review available this month for the whole workspace."
      : `If it completes, it uses 1 of the workspace's ${plan.limit} ${month} reviews: ` +
        `${plan.available} available now → ${plan.available - 1} after this one.`;
  return [cost, `If it fails or takes longer than ${LIMIT_S} seconds, it is free.`];
}

/** What to tell the lawyer when a request is refused (edge cases 5 and 7). */
export function requestErrorNotice(error: unknown, lawyerNames: Record<string, string>): string {
  if (error instanceof ApiError && error.code === "REVIEW_IN_PROGRESS") {
    const review = error.details.review as ReviewSummary;
    return (
      `${requesterName(review, lawyerNames)} already started a review of this document at ${formatTime(review.requested_at)}. ` +
      "You are now following it."
    );
  }
  if (error instanceof ApiError && error.code === "PLAN_EXHAUSTED") {
    return "Another review just took the last available slot. Your request has not been saved.";
  }
  const reason = error instanceof ApiError ? error.message : "The review service cannot be reached.";
  return `${reason} Your request has not been saved.`;
}
