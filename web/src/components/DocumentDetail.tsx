"use client";

import Link from "next/link";

import { ApiError, api, type Review, type WorkspaceDocument } from "@/lib/api";
import { supersededLabel } from "@/lib/display";
import { firstName, formatDay } from "@/lib/format";
import { ACTIVE_MS, FOLLOW_MS, IDLE_MS, usePolling } from "@/lib/usePolling";

import { useIdentity } from "./Identity";
import { usePlan } from "./Plan";
import { RequestReview } from "./RequestReview";
import { ReviewPanel } from "./ReviewPanel";

interface Detail {
  document: WorkspaceDocument;
  /** The latest review, whatever its status (BR-19). */
  latest: Review | null;
  /** The current result: the latest completed review (BR-19). */
  result: Review | null;
}

async function loadDetail(documentId: string): Promise<Detail> {
  const document = await api.document(documentId);
  const latest = document.latest_review ? await api.review(document.latest_review.id) : null;
  const resultId = document.current_result?.review_id;
  const result = !resultId ? null : resultId === latest?.id ? latest : await api.review(resultId);
  return { document, latest, result };
}

export function DocumentDetail({ documentId }: { documentId: string }) {
  const { lawyerNames } = useIdentity();
  const { plan } = usePlan();
  const { data, error, refresh } = usePolling(
    () => loadDetail(documentId),
    (current) => {
      if (current.latest?.status === "running") return FOLLOW_MS;
      return plan && plan.running > 0 ? ACTIVE_MS : IDLE_MS;
    },
    documentId,
  );

  if (data === undefined) {
    if (error instanceof ApiError && error.status === 404) {
      return (
        <p className="page-message">
          Document not found. <Link href="/">Back to the documents</Link>
        </p>
      );
    }
    return <p className="page-message">{error ? "The review service cannot be reached. Retrying…" : "Loading…"}</p>;
  }

  const { document, latest, result } = data;
  const superseded = supersededLabel(document, []);
  return (
    <>
      <Link href="/">← Back</Link>
      <h1 className="document-title">{document.title}</h1>
      <p className="muted">
        Uploaded {formatDay(document.uploaded_at)} by {firstName(lawyerNames[document.uploaded_by] ?? "unknown")} ·{" "}
        {document.pages} pages · {document.type}
      </p>
      {superseded && <div className="tag">{superseded}</div>}
      {error && <p className="connection-lost">Connection lost, status may be out of date.</p>}
      <RequestReview document={document} latest={latest} hasResult={result !== null} onRequested={refresh} />
      <ReviewPanel latest={latest} result={result} />
    </>
  );
}
