"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfidenceMeter } from "@/components/target/confidence-meter";
import { EvidenceCallout } from "@/components/target/evidence-callout";
import { PermissionBoundary } from "@/components/target/permission-boundary";
import { StatePanel } from "@/components/target/state-panel";
import { cn } from "@/lib/utils";
import {
  APPROVALS,
  type ApprovalRequirement,
  EVAL_GATES,
  type EvalGate,
  type GateStatus,
  PREFLIGHT_DIFFS,
  type PreflightDiff,
  canPromote,
} from "@/lib/deploy-flight";

const GATE_TONE: Record<GateStatus, string> = {
  passed: "border-success/40 bg-success/10 text-success",
  running: "border-info/40 bg-info/10 text-info",
  failed: "border-destructive bg-destructive/10 text-destructive",
  waived: "border-warning/40 bg-warning/10 text-warning",
};

export interface PromotionPanelProps {
  diffs?: ReadonlyArray<PreflightDiff>;
  gates?: ReadonlyArray<EvalGate>;
  approvals?: ReadonlyArray<ApprovalRequirement>;
  /** Caller permission. When false the panel renders a permission boundary. */
  canApprove?: boolean;
  onPromote?: () => void;
  onRequestAccess?: () => void;
}

export function PromotionPanel({
  diffs = PREFLIGHT_DIFFS,
  gates = EVAL_GATES,
  approvals = APPROVALS,
  canApprove = true,
  onPromote,
  onRequestAccess,
}: PromotionPanelProps) {
  const [promoted, setPromoted] = useState(false);
  const promoteEnabled = canPromote(gates, approvals) && canApprove;
  const handlePromote = () => {
    if (!promoteEnabled) return;
    setPromoted(true);
    onPromote?.();
  };
  return (
    <PermissionBoundary
      allowed={canApprove}
      reason="Promotion requires the deploy:promote permission. Ask an engineering lead to grant access for this agent."
      onRequestAccess={onRequestAccess}
    >
      <section className="space-y-3" data-testid="promotion-panel">
        <header className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">Promotion</h2>
          <Button
            type="button"
            size="sm"
            disabled={!promoteEnabled || promoted}
            onClick={handlePromote}
            data-testid="promotion-promote"
          >
            {promoted ? "Promoted" : "Promote to production"}
          </Button>
        </header>
        <div className="grid gap-3 lg:grid-cols-3">
          <article
            className="rounded-md border bg-card p-3"
            data-pane="changes"
            data-testid="promotion-pane-changes"
          >
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Changes
            </h3>
            <ul className="mt-2 space-y-2 text-xs">
              {diffs.map((d) => (
                <li key={d.dimension} className="flex items-start gap-2">
                  <span className="font-mono text-[11px] uppercase text-muted-foreground">
                    {d.dimension}
                  </span>
                  <span className="flex-1">{d.impact}</span>
                </li>
              ))}
            </ul>
          </article>
          <article
            className="rounded-md border bg-card p-3"
            data-pane="gates"
            data-testid="promotion-pane-gates"
          >
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Gates
            </h3>
            <ul className="mt-2 space-y-2 text-xs">
              {gates.map((g) => (
                <li
                  key={g.id}
                  className="flex items-center justify-between"
                  data-testid={`promotion-gate-${g.id}`}
                >
                  <div>
                    <p className="font-medium">{g.label}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">
                      {g.cases.passed}/{g.cases.total} · {g.evidenceRef}
                    </p>
                  </div>
                  <span
                    className={cn(
                      "rounded-md border px-2 py-0.5 text-[11px]",
                      GATE_TONE[g.status],
                    )}
                  >
                    {g.status}
                  </span>
                </li>
              ))}
            </ul>
          </article>
          <article
            className="rounded-md border bg-card p-3"
            data-pane="approvals"
            data-testid="promotion-pane-approvals"
          >
            <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Approvals
            </h3>
            <ul className="mt-2 space-y-2 text-xs">
              {approvals.map((a) => (
                <li
                  key={a.id}
                  data-testid={`promotion-approval-${a.id}`}
                  className="rounded-md border bg-background p-2"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-medium">{a.role}</p>
                    <span
                      className={cn(
                        "rounded-md border px-2 py-0.5 text-[11px]",
                        a.satisfied
                          ? "border-success/40 bg-success/10 text-success"
                          : a.required
                            ? "border-warning/40 bg-warning/10 text-warning"
                            : "border-border bg-muted text-muted-foreground",
                      )}
                    >
                      {a.satisfied ? "approved" : a.required ? "required" : "optional"}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                    {a.approver ?? "—"} · {a.evidenceRef}
                  </p>
                </li>
              ))}
            </ul>
          </article>
        </div>
        {!promoteEnabled ? (
          <StatePanel state="degraded" title="Promotion locked">
            One or more blocking gates or required approvals are still open.
            <ConfidenceMeter
              value={55}
              label="Promotion confidence"
              evidence="Gate the production button until canary smoke and SRE sign-off complete."
            />
          </StatePanel>
        ) : (
          <EvidenceCallout
            title="Audited promotion"
            tone="info"
            source="canonical §19.3"
          >
            Production button enabled because every blocking gate is passed and
            every required approval is satisfied. The promotion event will be
            audited with the snapshot id and approver list.
          </EvidenceCallout>
        )}
      </section>
    </PermissionBoundary>
  );
}
