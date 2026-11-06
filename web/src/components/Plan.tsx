"use client";

import { createContext, useContext, type ReactNode } from "react";

import { api, type Plan } from "@/lib/api";
import { ACTIVE_MS, IDLE_MS, usePolling } from "@/lib/usePolling";

interface PlanValue {
  plan: Plan | undefined;
  /** Reload now, e.g. right after a review is requested. */
  refresh: () => void;
}

const PlanContext = createContext<PlanValue | null>(null);

export function usePlan(): PlanValue {
  const value = useContext(PlanContext);
  if (value === null) throw new Error("usePlan must be used inside <PlanProvider>.");
  return value;
}

/** One shared, polled copy of the workspace plan, for the header counter and the request button. */
export function PlanProvider({ children }: { children: ReactNode }) {
  const { data: plan, refresh } = usePolling(api.plan, (current) => (current.running > 0 ? ACTIVE_MS : IDLE_MS));
  return <PlanContext.Provider value={{ plan, refresh }}>{children}</PlanContext.Provider>;
}
