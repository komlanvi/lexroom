"use client";

import Link from "next/link";

import { api } from "@/lib/api";
import { planSummary } from "@/lib/display";
import { ACTIVE_MS, IDLE_MS, usePolling } from "@/lib/usePolling";

import { useIdentity } from "./Identity";

export function Header() {
  const { lawyers, lawyer, setLawyerId } = useIdentity();
  const { data: plan } = usePolling(api.plan, (current) => (current.running > 0 ? ACTIVE_MS : IDLE_MS));
  const summary = plan ? planSummary(plan) : null;

  return (
    <header className="header">
      <Link href="/" className="brand">
        Lexroom · Workspace
      </Link>
      {summary && (
        <div className={summary.exhausted ? "plan plan-exhausted" : "plan"}>
          <strong>{summary.headline}</strong>
          <span className="muted">{summary.resets}</span>
        </div>
      )}
      <label className="identity">
        <span className="visually-hidden">Acting as</span>
        <select value={lawyer.id} onChange={(event) => setLawyerId(event.target.value)}>
          {lawyers.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
    </header>
  );
}
