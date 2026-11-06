"use client";

import { useState } from "react";

import { api, type Review, type WorkspaceDocument } from "@/lib/api";
import { formatDay } from "@/lib/format";
import { confirmationLines, requestErrorNotice, requestState } from "@/lib/review";

import { useIdentity } from "./Identity";
import { usePlan } from "./Plan";

/** The request button, its explanation when disabled, and the confirmation dialog (decision 3). */
export function RequestReview({
  document,
  latest,
  hasResult,
  onRequested,
}: {
  document: WorkspaceDocument;
  latest: Review | null;
  hasResult: boolean;
  onRequested: () => void;
}) {
  const { lawyer, lawyerNames } = useIdentity();
  const { plan, refresh: refreshPlan } = usePlan();
  const [confirming, setConfirming] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [notice, setNotice] = useState<string>();

  if (plan === undefined) return null;
  const state = requestState({ latest, hasResult, plan, requesting, lawyerNames, now: new Date() });

  async function request() {
    setConfirming(false);
    setRequesting(true);
    setNotice(undefined);
    try {
      await api.requestReview(document.id, lawyer.id);
    } catch (error) {
      setNotice(requestErrorNotice(error, lawyerNames));
    } finally {
      setRequesting(false);
      refreshPlan();
      onRequested();
    }
  }

  return (
    <div className="request">
      <button
        type="button"
        className="button primary"
        disabled={!state.enabled}
        onClick={() => setConfirming(true)}
      >
        {state.label}
      </button>
      {notice && <p className="request-notice">{notice}</p>}
      {state.explanation.map((line) => (
        <p key={line} className="muted">
          {line}
        </p>
      ))}

      {confirming && (
        <div className="dialog-backdrop">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
            <h1 id="confirm-title">Request an AI review?</h1>
            <p className="muted">
              {document.title} ({formatDay(document.uploaded_at)})
            </p>
            <ul>
              {confirmationLines(plan).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <div className="dialog-actions">
              <button type="button" className="button" onClick={() => setConfirming(false)}>
                Cancel
              </button>
              <button type="button" className="button primary" onClick={request}>
                Use 1 review
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
