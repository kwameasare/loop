"use client";

import { useState } from "react";

import { LiveBadge } from "@/components/target/live-badge";
import { cn } from "@/lib/utils";
import {
  type ApprovalPolicy,
  type FlightEnvironment,
  FLIGHT_ENVIRONMENTS,
} from "@/lib/deploy-flight";

const POLICY_LABEL: Record<ApprovalPolicy, string> = {
  none: "Auto-promote",
  "single-reviewer": "Single reviewer",
  "two-person": "Two-person rule",
  "compliance-board": "Compliance board",
};

export interface EnvironmentStripProps {
  defaultEnvironmentId?: string;
  onSelect?: (env: FlightEnvironment) => void;
}

export function EnvironmentStrip({
  defaultEnvironmentId = "production",
  onSelect,
}: EnvironmentStripProps) {
  const [selected, setSelected] = useState(defaultEnvironmentId);
  const handle = (env: FlightEnvironment) => {
    setSelected(env.id);
    onSelect?.(env);
  };
  return (
    <div className="space-y-3" data-testid="environment-strip">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-foreground">Environments</h2>
        <span className="text-xs text-muted-foreground">
          Each tier carries its own secrets, KB, budget and approval policy.
        </span>
      </div>
      <ul
        className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
        data-testid="environment-strip-list"
      >
        {FLIGHT_ENVIRONMENTS.map((env) => {
          const active = env.id === selected;
          return (
            <li key={env.id}>
              <button
                type="button"
                onClick={() => handle(env)}
                aria-pressed={active}
                data-testid={`environment-card-${env.id}`}
                className={cn(
                  "w-full rounded-md border bg-card p-4 text-left transition",
                  active
                    ? "border-primary ring-1 ring-primary"
                    : "hover:border-foreground/40",
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold">{env.label}</span>
                  {env.tier === "production" ? (
                    <LiveBadge tone="live" pulse>live</LiveBadge>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      {env.region}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{env.blurb}</p>
                <dl className="mt-3 grid grid-cols-2 gap-y-1 text-xs">
                  <dt className="text-muted-foreground">Budget</dt>
                  <dd className="text-right">${env.budgetUsdPerDay}/day</dd>
                  <dt className="text-muted-foreground">KB</dt>
                  <dd className="text-right font-mono text-[11px]">
                    {env.kbVersion}
                  </dd>
                  <dt className="text-muted-foreground">Approval</dt>
                  <dd
                    className="text-right"
                    data-testid={`environment-policy-${env.id}`}
                  >
                    {POLICY_LABEL[env.approvalPolicy]}
                  </dd>
                </dl>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
