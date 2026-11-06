"use client";

import Link from "next/link";

import { planSummary } from "@/lib/display";

import { useIdentity } from "./Identity";
import { usePlan } from "./Plan";

export function Header() {
  const { lawyers, lawyer, setLawyerId } = useIdentity();
  const { plan } = usePlan();
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
