"use client";

import Link from "next/link";

import { api } from "@/lib/api";
import { anyRunning, documentBadge, supersededLabel } from "@/lib/display";
import { firstName, formatDay } from "@/lib/format";
import { ACTIVE_MS, IDLE_MS, usePolling } from "@/lib/usePolling";

import { useIdentity } from "./Identity";

export function DocumentList() {
  const { lawyerNames } = useIdentity();
  const { data: documents, error } = usePolling(api.documents, (current) =>
    anyRunning(current) ? ACTIVE_MS : IDLE_MS,
  );

  if (documents === undefined) {
    return <p className="page-message">{error ? "The review service cannot be reached. Retrying…" : "Loading…"}</p>;
  }

  const now = new Date();
  return (
    <>
      {error && <p className="connection-lost">Connection lost, status may be out of date.</p>}
      <table className="documents">
        <thead>
          <tr>
            <th>Document</th>
            <th>Uploaded</th>
            <th>Latest review</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => {
            const badge = documentBadge(document, lawyerNames, now);
            const superseded = supersededLabel(document, documents);
            return (
              <tr key={document.id}>
                <td>
                  <Link href={`/documents/${document.id}`}>{document.title}</Link>
                  {superseded && <div className="tag">{superseded}</div>}
                </td>
                <td className="nowrap">
                  {formatDay(document.uploaded_at)} · {firstName(lawyerNames[document.uploaded_by] ?? "unknown")}
                </td>
                <td>
                  <span className={`badge badge-${badge.tone}`}>{badge.label}</span>
                  {badge.note && <div className="muted">{badge.note}</div>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}
