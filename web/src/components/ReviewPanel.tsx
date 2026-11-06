"use client";

import type { Finding, Review } from "@/lib/api";
import { formatDateTime, formatElapsed, formatTime } from "@/lib/format";
import {
  SEVERITY_LABELS,
  clauseLabel,
  elapsedSeconds,
  failureMessage,
  panelSections,
  requesterName,
  sortFindings,
  type PanelSection,
} from "@/lib/review";

import { useIdentity } from "./Identity";

const DISCLAIMER = "AI findings support, not replace, a lawyer's review.";

export function ReviewPanel({ latest, result }: { latest: Review | null; result: Review | null }) {
  return (
    <>
      {panelSections(latest, result).map((section) => (
        <Section key={section.kind} section={section} />
      ))}
    </>
  );
}

function Section({ section }: { section: PanelSection }) {
  switch (section.kind) {
    case "not-reviewed":
      return <p className="panel-empty">This document has not been reviewed yet.</p>;
    case "no-result":
      return <p className="panel-empty">No completed review for this document yet.</p>;
    case "live":
      return <LiveReview review={section.review} />;
    case "previous":
      return <PreviousResult review={section.review} />;
    case "final":
      return <FinalReview review={section.review} />;
    case "failed":
      return <FailedReview review={section.review} hasResult={section.hasResult} />;
  }
}

/** Decision 2: findings shown as they arrive, marked Partial, no totals. */
function LiveReview({ review }: { review: Review }) {
  const { lawyerNames } = useIdentity();
  const count = review.findings.length;

  return (
    <section className="panel panel-live">
      <h2>Review in progress</h2>
      <p>
        Requested by {requesterName(review, lawyerNames)} at {formatTime(review.requested_at)} ·{" "}
        {formatElapsed(elapsedSeconds(review))} elapsed · stopped automatically at 1:00
      </p>
      <p className="panel-banner">
        {count === 1 ? "1 finding" : `${count} findings`} received so far. This list is incomplete: more may arrive, and
        the review may still fail.
      </p>
      {review.findings.map((finding) => (
        <FindingCard key={finding.seq} finding={finding} tag="Partial" />
      ))}
    </section>
  );
}

/** Decision 1: the last completed review stays visible while a new one runs, never merged with it. */
function PreviousResult({ review }: { review: Review }) {
  const { lawyerNames } = useIdentity();

  return (
    <section className="panel panel-previous">
      <h2>Previous result · no longer current</h2>
      <p className="muted">
        {formatDateTime(review.finished_at!)} · by {requesterName(review, lawyerNames)} · a new review is in progress
        (above)
      </p>
      {sortFindings(review.findings).map((finding) => (
        <FindingCard key={finding.seq} finding={finding} tag="Previous" />
      ))}
    </section>
  );
}

function FinalReview({ review }: { review: Review }) {
  const { lawyerNames } = useIdentity();
  const count = review.findings.length;

  return (
    <section className="panel">
      <h2>
        <span className="final-badge">Final</span> Review completed {formatDateTime(review.finished_at!)} · requested by{" "}
        {requesterName(review, lawyerNames)}
      </h2>
      {count === 0 ? (
        <p>
          <strong>Completed · no clauses flagged.</strong> The AI flagged no clauses. This is not a legal opinion that
          the contract is risk-free.
        </p>
      ) : (
        <p className="muted">{count === 1 ? "1 finding" : `${count} findings`}, sorted by severity</p>
      )}
      {sortFindings(review.findings).map((finding) => (
        <FindingCard key={finding.seq} finding={finding} />
      ))}
      <p className="muted">{DISCLAIMER}</p>
    </section>
  );
}

/** BR-16: status only, never the findings of a failed review. */
function FailedReview({ review, hasResult }: { review: Review; hasResult: boolean }) {
  const { lawyerNames } = useIdentity();

  return (
    <section className="panel panel-failed">
      <h2>{hasResult ? "Latest attempt failed" : "Review failed"}</h2>
      <p>✕ {failureMessage(review, lawyerNames)}</p>
      <p>
        It did not count against the plan.
        {hasResult && " The result below is from the last completed review."}
      </p>
    </section>
  );
}

function FindingCard({ finding, tag }: { finding: Finding; tag?: "Partial" | "Previous" }) {
  const severity = SEVERITY_LABELS[finding.severity];

  return (
    <article className={`finding finding-${finding.severity}${tag ? ` finding-${tag.toLowerCase()}` : ""}`}>
      <p className="finding-heading">
        {tag && <span className="finding-tag">{tag}</span>}
        <span className="severity">
          {severity.icon} {severity.label}
        </span>{" "}
        · {clauseLabel(finding.clause)} · <strong>{finding.title}</strong>
      </p>
      {finding.excerpt === null ? (
        <p className="muted">No excerpt: this finding is about something missing from the contract.</p>
      ) : (
        <blockquote>“{finding.excerpt}”</blockquote>
      )}
      <p>{finding.explanation}</p>
    </article>
  );
}
