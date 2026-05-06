"use client";

import { useMemo, useState } from "react";
import { FlaskConical, GitFork, PlayCircle, ShieldCheck } from "lucide-react";

import {
  DiffRibbon,
  EvidenceCallout,
  LiveBadge,
  RiskHalo,
  StageStepper,
  StatePanel,
} from "@/components/target";
import {
  OBJECT_STATE_TREATMENTS,
  TRUST_STATE_TREATMENTS,
} from "@/lib/design-tokens";
import type {
  BuildFlowAction,
  BuildFlowActionId,
  BuildFlowData,
} from "@/lib/target-ux/build-flow";
import { cn } from "@/lib/utils";

export interface BuildToTestFlowProps {
  data: BuildFlowData;
}

function liveBadgeTone(
  state: BuildFlowData["objectState"],
): "live" | "draft" | "staged" | "canary" | "paused" {
  if (state === "production") return "live";
  if (state === "canary") return "canary";
  if (state === "staged") return "staged";
  if (state === "draft") return "draft";
  return "paused";
}

function actionIcon(id: BuildFlowActionId) {
  if (id === "fork") return <GitFork className="h-4 w-4" aria-hidden />;
  if (id === "save-eval") {
    return <FlaskConical className="h-4 w-4" aria-hidden />;
  }
  return <PlayCircle className="h-4 w-4" aria-hidden />;
}

function ActionButton({
  action,
  selected,
  onSelect,
}: {
  action: BuildFlowAction;
  selected: boolean;
  onSelect: (id: BuildFlowActionId) => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(
        "min-h-28 rounded-md border bg-background p-3 text-left text-sm transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
        selected ? "border-primary ring-1 ring-primary/50" : "",
      )}
      onClick={() => onSelect(action.id)}
      data-testid={`build-flow-action-${action.id}`}
    >
      <span className="flex items-center gap-2 font-semibold">
        <span className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border bg-card">
          {actionIcon(action.id)}
        </span>
        {action.label}
      </span>
      <span className="mt-2 block text-muted-foreground">
        {action.description}
      </span>
      <span className="mt-2 block text-xs text-muted-foreground">
        Evidence: {action.evidence}
      </span>
    </button>
  );
}

export function BuildToTestFlow({ data }: BuildToTestFlowProps) {
  const [selectedActionId, setSelectedActionId] =
    useState<BuildFlowActionId>("preview");
  const selectedAction = useMemo(
    () =>
      data.actions.find((action) => action.id === selectedActionId) ??
      data.actions[0]!,
    [data.actions, selectedActionId],
  );
  const productionLocked = data.objectState === "production";
  const trustTreatment = TRUST_STATE_TREATMENTS[data.trust];

  return (
    <section
      className="min-w-0 rounded-md border bg-card p-4"
      aria-labelledby={`build-flow-heading-${data.origin}`}
      data-testid={`build-to-test-flow-${data.origin}`}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Build-to-test flow
            </p>
            <h3
              className="mt-1 text-lg font-semibold"
              id={`build-flow-heading-${data.origin}`}
            >
              Preview, fork, and save as eval
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {data.agentName} · {data.sourceTraceId} · {data.sourceTurn}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <LiveBadge tone={liveBadgeTone(data.objectState)}>
              {OBJECT_STATE_TREATMENTS[data.objectState].label}
            </LiveBadge>
            <span
              className={cn(
                "inline-flex h-7 items-center rounded-md border px-2.5 text-xs font-medium",
                trustTreatment.className,
              )}
            >
              {trustTreatment.label}
            </span>
          </div>
        </div>

        <StageStepper
          currentId={data.objectState}
          steps={[
            { id: "draft", label: "Draft", state: "draft" },
            { id: "saved", label: "Saved", state: "saved" },
            { id: "staged", label: "Staged", state: "staged" },
            { id: "production", label: "Production", state: "production" },
          ]}
        />

        {data.degradedReason ? (
          <StatePanel state="permission" title="Production edit locked">
            <p>{data.degradedReason}</p>
          </StatePanel>
        ) : null}

        <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
          <div className="rounded-md border bg-background p-3">
            <p className="text-xs font-medium text-muted-foreground">
              Draft branch
            </p>
            <p className="mt-1 break-words text-sm font-semibold">
              {data.branch}
            </p>
          </div>
          <div className="rounded-md border bg-background p-3">
            <p className="text-xs font-medium text-muted-foreground">
              Fork branch
            </p>
            <p className="mt-1 break-words text-sm font-semibold">
              {data.ephemeralBranch}
            </p>
          </div>
          <div className="rounded-md border bg-background p-3">
            <p className="text-xs font-medium text-muted-foreground">
              Eval case
            </p>
            <p className="mt-1 break-words text-sm font-semibold">
              {data.evalCaseId}
            </p>
          </div>
        </div>

        <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(min(100%,12rem),1fr))]">
          {data.actions.map((action) => (
            <ActionButton
              key={action.id}
              action={action}
              selected={selectedAction.id === action.id}
              onSelect={setSelectedActionId}
            />
          ))}
        </div>

        <RiskHalo
          level={productionLocked ? "blocked" : "low"}
          label={
            productionLocked
              ? "Production mutation blocked"
              : "Production remains isolated"
          }
        >
          <div
            className="rounded-md bg-background p-3"
            data-testid="build-flow-production-guard"
          >
            <p className="flex items-center gap-2 text-sm font-semibold">
              <ShieldCheck className="h-4 w-4" aria-hidden />
              Production isolation
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              {data.productionGuard}
            </p>
            <button
              type="button"
              disabled
              title={data.blockedProductionReason}
              className="mt-3 rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground"
              data-testid="build-flow-production-action"
            >
              Apply directly to production
            </button>
            <p className="mt-2 text-xs text-muted-foreground">
              Reason: {data.blockedProductionReason}
            </p>
          </div>
        </RiskHalo>

        <DiffRibbon
          label={data.diff.label}
          before={data.diff.before}
          after={data.diff.after}
          impact={data.diff.impact}
        />

        <section
          className="rounded-md border bg-background p-3"
          data-testid="build-flow-result"
          aria-live="polite"
        >
          <p className="text-sm font-semibold">{selectedAction.label}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {selectedAction.result}
          </p>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            {data.diffs.map((diff) => (
              <li key={diff} className="rounded-md border bg-card px-3 py-2">
                {diff}
              </li>
            ))}
          </ul>
        </section>

        <EvidenceCallout
          title="Traceable test artifact"
          source={`${data.previewEvidence}; ${data.forkEvidence}; ${data.saveEvalEvidence}`}
          confidence={92}
          confidenceLevel={data.confidence}
          tone={productionLocked ? "warning" : "success"}
        >
          Preview, fork, and eval creation preserve trace, snapshot, memory,
          tool, retrieval, cost, latency, and branch evidence.
        </EvidenceCallout>
      </div>
    </section>
  );
}
