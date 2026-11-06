import { describe, expect, it } from "vitest";

import { ApiError, type Finding, type Plan, type Review } from "./api";
import { formatDateTime, formatTime } from "./format";
import {
  clauseLabel,
  confirmationLines,
  failureMessage,
  panelSections,
  requestErrorNotice,
  requestState,
  sortFindings,
} from "./review";

const CHIARA = "chiara-id";
const NAMES = { [CHIARA]: "Chiara Belotti" };
const NOW = new Date("2026-11-07T10:00:00Z");

function finding(overrides: Partial<Finding> = {}): Finding {
  return {
    seq: 1,
    clause: "4.2",
    title: "A finding",
    severity: "medium",
    excerpt: "Some text.",
    explanation: "Why it matters.",
    ...overrides,
  };
}

function review(overrides: Partial<Review> = {}): Review {
  return {
    id: "review-1",
    document_id: "doc-1",
    status: "completed",
    failure_reason: null,
    requested_by: CHIARA,
    requested_at: "2026-11-06T13:10:05Z",
    deadline_at: "2026-11-06T13:11:05Z",
    finished_at: "2026-11-06T13:10:19Z",
    server_now: "2026-11-06T13:10:19Z",
    is_final: true,
    findings: [],
    ...overrides,
  };
}

const running = review({ id: "review-2", status: "running", finished_at: null, is_final: false });
const failed = review({ id: "review-2", status: "failed", failure_reason: "ai_error", is_final: false });

function plan(overrides: Partial<Plan> = {}): Plan {
  return {
    limit: 10,
    completed: 3,
    running: 1,
    available: 6,
    period: "2026-11",
    resets_at: "2026-11-30T23:00:00Z",
    ...overrides,
  };
}

function state(overrides: Partial<Parameters<typeof requestState>[0]> = {}) {
  return requestState({
    latest: null,
    hasResult: false,
    plan: plan(),
    requesting: false,
    lawyerNames: NAMES,
    now: NOW,
    ...overrides,
  });
}

describe("requestState", () => {
  it("is disabled while a review runs on the document, showing who started it and when", () => {
    const latest = review({ ...running, server_now: "2026-11-06T13:10:19Z" });

    expect(state({ latest })).toEqual({ label: "Review in progress (by Chiara, 0:14)", enabled: false, explanation: [] });
  });

  it("a running review on the document wins over an exhausted plan", () => {
    expect(state({ latest: running, plan: plan({ available: 0, completed: 9, running: 1 }) }).label).toMatch(
      /^Review in progress/,
    );
  });

  it("explains that reviews in progress hold the last slots, and that nothing was saved", () => {
    const result = state({ plan: plan({ completed: 8, running: 2, available: 0 }) });

    expect(result.enabled).toBe(false);
    expect(result.explanation).toEqual([
      "No review can be started right now.",
      "This month: 8 completed + 2 in progress = all 10 reviews in use.",
      expect.stringContaining("if it fails or takes longer than 60 seconds, it is not counted and becomes available again"),
      expect.stringContaining("This request has not been saved and will not start on its own."),
    ]);
  });

  it("shows the reset date when the plan is used up", () => {
    const result = state({ plan: plan({ completed: 10, running: 0, available: 0 }) });

    expect(result.enabled).toBe(false);
    expect(result.explanation).toEqual([
      "The workspace has used its 10 reviews for November.",
      "Reviews are available again on 1 Dec 2026, 00:00 Rome time (in 24 days).",
      "No new review can be started until then.",
    ]);
  });

  it("says 'in 1 day' on the last day of the month", () => {
    const lastDay = new Date("2026-11-30T09:00:00Z");

    expect(state({ plan: plan({ completed: 10, running: 0, available: 0 }), now: lastDay }).explanation[1]).toContain(
      "(in 1 day)",
    );
  });

  it("is disabled while the request is in flight", () => {
    expect(state({ latest: failed, requesting: true })).toEqual({ label: "Requesting…", enabled: false, explanation: [] });
  });

  it.each([
    ["the latest review failed, even with an earlier result", { latest: failed, hasResult: true }, "Retry review"],
    ["a completed review exists", { latest: review(), hasResult: true }, "Request a new review"],
    ["the document was never reviewed", {}, "Request review"],
  ])("is enabled when %s", (_, overrides, label) => {
    expect(state(overrides)).toEqual({ label, enabled: true, explanation: [] });
  });
});

describe("confirmationLines", () => {
  it("states the cost, the plan before and after, and that a failure is free", () => {
    expect(confirmationLines(plan())).toEqual([
      "If it completes, it uses 1 of the workspace's 10 November reviews: 6 available now → 5 after this one.",
      "If it fails or takes longer than 60 seconds, it is free.",
    ]);
  });

  it("warns when it is the last review of the month", () => {
    expect(confirmationLines(plan({ available: 1 }))[0]).toContain(
      "This is the last review available this month for the whole workspace.",
    );
  });
});

describe("panelSections", () => {
  const result = review({ id: "review-1" });

  it("shows an empty state when the document was never reviewed", () => {
    expect(panelSections(null, null)).toEqual([{ kind: "not-reviewed" }]);
  });

  it("shows a running review alone when there is no earlier result", () => {
    expect(panelSections(running, null)).toEqual([{ kind: "live", review: running }]);
  });

  it("keeps the previous completed result below the running review, separately", () => {
    expect(panelSections(running, result)).toEqual([
      { kind: "live", review: running },
      { kind: "previous", review: result },
    ]);
  });

  it("shows only the final review once completed", () => {
    expect(panelSections(result, result)).toEqual([{ kind: "final", review: result }]);
  });

  it("shows a failure as a status, then the last completed review as the current result", () => {
    expect(panelSections(failed, result)).toEqual([
      { kind: "failed", review: failed, hasResult: true },
      { kind: "final", review: result },
    ]);
  });

  it("shows a failure as a status, then says there is no result yet", () => {
    expect(panelSections(failed, null)).toEqual([{ kind: "failed", review: failed, hasResult: false }, { kind: "no-result" }]);
  });
});

describe("sortFindings", () => {
  it("orders by severity, then natural clause order, with General last", () => {
    const findings = [
      finding({ seq: 1, severity: "low", clause: "2" }),
      finding({ seq: 2, severity: "medium", clause: null }),
      finding({ seq: 3, severity: "medium", clause: "12.1" }),
      finding({ seq: 4, severity: "high", clause: "8.3" }),
      finding({ seq: 5, severity: "medium", clause: "4.2" }),
      finding({ seq: 6, severity: "medium", clause: "12" }),
    ];

    expect(sortFindings(findings).map((item) => item.seq)).toEqual([4, 5, 6, 3, 2, 1]);
  });

  it("does not reorder the list it is given (arrival order is kept for partial findings)", () => {
    const findings = [finding({ seq: 1, severity: "low" }), finding({ seq: 2, severity: "high" })];

    sortFindings(findings);

    expect(findings.map((item) => item.seq)).toEqual([1, 2]);
  });
});

describe("clauseLabel", () => {
  it("names the clause, or says the finding is general", () => {
    expect([clauseLabel("4.2"), clauseLabel(null)]).toEqual(["Clause 4.2", "General (no specific clause)"]);
  });
});

describe("failureMessage", () => {
  it("gives the time to the AI error and the requester", () => {
    expect(failureMessage(failed, NAMES)).toBe("The AI returned an error after 14 s (requested by Chiara at 14:10:05).");
  });

  it("explains a timeout", () => {
    const timedOut = review({ status: "failed", failure_reason: "timed_out", finished_at: "2026-11-06T13:11:05Z" });

    expect(failureMessage(timedOut, NAMES)).toBe("No result within 60 seconds (requested by Chiara at 14:10:05).");
  });
});

describe("requestErrorNotice", () => {
  it("tells the lawyer who already started the review they now follow", () => {
    const error = new ApiError(409, "REVIEW_IN_PROGRESS", "", { review: running });

    expect(requestErrorNotice(error, NAMES)).toBe(
      "Chiara already started a review of this document at 14:10:05. You are now following it.",
    );
  });

  it("says the request was not saved when the last slot was taken", () => {
    const error = new ApiError(409, "PLAN_EXHAUSTED", "", {});

    expect(requestErrorNotice(error, NAMES)).toBe(
      "Another review just took the last available slot. Your request has not been saved.",
    );
  });

  it("says the request was not saved when the service cannot be reached", () => {
    expect(requestErrorNotice(new TypeError("fetch failed"), NAMES)).toBe(
      "The review service cannot be reached. Your request has not been saved.",
    );
  });
});

describe("format", () => {
  it("formats full dates and times with seconds in Rome time", () => {
    expect(formatDateTime("2026-11-30T23:00:00Z")).toBe("1 Dec 2026, 00:00");
    expect(formatTime("2026-11-06T13:10:05Z")).toBe("14:10:05");
  });
});
