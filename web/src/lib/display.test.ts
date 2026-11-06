import { describe, expect, it } from "vitest";

import type { Plan, ReviewResult, ReviewSummary, WorkspaceDocument } from "./api";
import { anyRunning, documentBadge, planSummary, supersededLabel } from "./display";
import { formatDay, formatDayTime, formatElapsed } from "./format";

const CHIARA = "chiara-id";
const NAMES = { [CHIARA]: "Chiara Belotti" };
const NOW = new Date("2026-11-06T10:00:30Z");

function review(overrides: Partial<ReviewSummary> = {}): ReviewSummary {
  return {
    id: "review-1",
    status: "completed",
    failure_reason: null,
    requested_by: CHIARA,
    requested_at: "2026-11-05T09:00:00Z",
    deadline_at: "2026-11-05T09:01:00Z",
    finished_at: "2026-11-05T09:00:20Z",
    ...overrides,
  };
}

function result(overrides: Partial<ReviewResult> = {}): ReviewResult {
  return { review_id: "review-1", finished_at: "2026-11-05T09:00:20Z", findings_count: 2, ...overrides };
}

function doc(overrides: Partial<WorkspaceDocument> = {}): WorkspaceDocument {
  return {
    id: "doc-1",
    title: "Commercial lease",
    type: "lease",
    pages: 18,
    uploaded_at: "2026-09-03T14:05:00Z",
    uploaded_by: CHIARA,
    supersedes: null,
    superseded_by: null,
    latest_review: null,
    current_result: null,
    ...overrides,
  };
}

describe("documentBadge", () => {
  it("not reviewed", () => {
    expect(documentBadge(doc(), NAMES, NOW)).toEqual({ tone: "neutral", label: "Not reviewed" });
  });

  it("in progress, with elapsed time and requester", () => {
    const running = review({ status: "running", requested_at: "2026-11-06T10:00:18Z", finished_at: null });

    expect(documentBadge(doc({ latest_review: running }), NAMES, NOW)).toEqual({
      tone: "active",
      label: "In progress · 0:12 · by Chiara Belotti",
      note: undefined,
    });
  });

  it("in progress, mentions the previous result", () => {
    const running = review({ id: "review-2", status: "running", requested_at: "2026-11-06T10:00:18Z" });

    const badge = documentBadge(doc({ latest_review: running, current_result: result() }), NAMES, NOW);

    expect(badge.note).toBe("Previous result from 5 Nov");
  });

  it("in progress never shows more than the 60-second limit", () => {
    const running = review({ status: "running", requested_at: "2026-11-06T09:58:00Z" });

    expect(documentBadge(doc({ latest_review: running }), NAMES, NOW).label).toContain("1:00");
  });

  it.each([
    [2, "Completed 5 Nov · 2 findings"],
    [1, "Completed 5 Nov · 1 finding"],
    [0, "Completed 5 Nov · no clauses flagged"],
  ])("completed with %i findings", (count, label) => {
    const badge = documentBadge(doc({ latest_review: review(), current_result: result({ findings_count: count }) }), NAMES, NOW);

    expect(badge).toEqual({ tone: "success", label });
  });

  it.each([
    ["ai_error", "Failed (AI error) 6 Nov · no result yet"],
    ["timed_out", "Failed (time limit) 6 Nov · no result yet"],
  ] as const)("failed (%s) without an earlier result", (reason, label) => {
    const failed = review({ status: "failed", failure_reason: reason, finished_at: "2026-11-06T10:00:00Z" });

    expect(documentBadge(doc({ latest_review: failed }), NAMES, NOW)).toEqual({ tone: "danger", label });
  });

  it("failed, with an earlier result still available", () => {
    const failed = review({
      id: "review-2",
      status: "failed",
      failure_reason: "timed_out",
      finished_at: "2026-11-06T10:00:00Z",
    });

    expect(documentBadge(doc({ latest_review: failed, current_result: result() }), NAMES, NOW)).toEqual({
      tone: "danger",
      label: "Last attempt failed (time limit) 6 Nov",
      note: "Result from 5 Nov available",
    });
  });
});

describe("supersededLabel", () => {
  const v1 = doc({ id: "v1", superseded_by: "v2" });
  const v2 = doc({ id: "v2", supersedes: "v1", uploaded_at: "2026-09-24T10:15:00Z" });

  it("labels the older version with the date of the newer one", () => {
    expect(supersededLabel(v1, [v1, v2])).toBe("Previous version · superseded by the version of 24 Sep");
  });

  it("leaves current versions unlabelled", () => {
    expect(supersededLabel(v2, [v1, v2])).toBeNull();
  });
});

describe("planSummary", () => {
  const plan: Plan = {
    limit: 10,
    completed: 3,
    running: 1,
    available: 6,
    period: "2026-11",
    resets_at: "2026-12-01T00:00:00+01:00",
  };

  it("shows availability, running reviews and the reset in Rome time", () => {
    expect(planSummary(plan)).toEqual({
      headline: "Plan · November: 6 of 10 available · 1 running",
      resets: "Resets 1 Dec, 00:00 Rome time",
      exhausted: false,
    });
  });

  it("is flagged as exhausted at 0 available", () => {
    expect(planSummary({ ...plan, completed: 10, running: 0, available: 0 }).exhausted).toBe(true);
  });
});

describe("anyRunning", () => {
  it("is true only while a document has a running latest review", () => {
    expect(anyRunning([doc(), doc({ latest_review: review() })])).toBe(false);
    expect(anyRunning([doc(), doc({ latest_review: review({ status: "running" }) })])).toBe(true);
  });
});

describe("format", () => {
  it("shows days in Rome time, not UTC", () => {
    expect(formatDay("2026-11-30T23:30:00Z")).toBe("1 Dec");
  });

  it("uses the same short month names everywhere", () => {
    expect(formatDay("2026-09-24T10:15:00Z")).toBe("24 Sep");
  });

  it("shows times in Rome time, 24-hour", () => {
    expect(formatDayTime("2026-11-30T23:00:00Z")).toBe("1 Dec, 00:00");
    expect(formatDayTime("2026-07-01T12:05:00Z")).toBe("1 Jul, 14:05");
  });

  it("formats elapsed seconds as m:ss", () => {
    expect([formatElapsed(0), formatElapsed(9.9), formatElapsed(72), formatElapsed(-3)]).toEqual([
      "0:00",
      "0:09",
      "1:12",
      "0:00",
    ]);
  });
});
