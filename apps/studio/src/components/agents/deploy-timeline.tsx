"use client";

import { useState } from "react";

import {
  evaluateDeploymentThreshold as defaultEvaluateThreshold,
  pauseDeployment as defaultPause,
  promoteDeployment as defaultPromote,
  rampDeployment as defaultRamp,
  rollbackDeployment as defaultRollback,
  exportEvidencePack as defaultExportEvidencePack,
  startCanaryDeployment as defaultStartCanary,
  type Deployment,
  type EvidencePackExport,
  type EvidencePackExportFormat,
  type EvidencePackExportInput,
  type DeploymentThresholdEvaluationInput,
  type DeploymentThresholdEvaluationResult,
  type DeploymentStartInput,
  type EvidencePack,
} from "@/lib/deploys";
import type { ChangePackage } from "@/lib/change-package";

type ActionFn = (agentId: string, depId: string) => Promise<Deployment>;
type RampFn = (
  agentId: string,
  depId: string,
  trafficPercent: number,
) => Promise<Deployment>;
type StartFn = (
  agentId: string,
  input: DeploymentStartInput,
) => Promise<{ deployment: Deployment; evidence_pack?: EvidencePack }>;
type ExportEvidencePackFn = (
  agentId: string,
  evidencePackId: string,
  input: EvidencePackExportInput,
) => Promise<EvidencePackExport>;
type EvaluateThresholdFn = (
  agentId: string,
  deploymentId: string,
  input: DeploymentThresholdEvaluationInput,
) => Promise<DeploymentThresholdEvaluationResult>;

type ThresholdPolicy = "pause" | "rollback";
type ThresholdInputState = {
  metric: string;
  observed: number;
  policy: ThresholdPolicy;
};

const DEFAULT_CHANNEL_SCOPE = "web_chat";
const DEFAULT_REGION_SCOPE = "global";
const DEFAULT_SEGMENT_SCOPE = "all-customers";
const DEFAULT_THRESHOLD_METRICS = [
  "error_rate_percent",
  "p95_latency_ms",
  "cost_delta_percent",
  "tool_failure_rate_percent",
];

function parseScopeList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function scopeLabel(scope: string[] | undefined, fallback: string): string {
  if (!scope || scope.length === 0) return fallback;
  return scope.join(", ");
}

function thresholdValue(
  thresholds: Record<string, unknown> | undefined,
  key: string,
): string | null {
  const raw = thresholds?.[key];
  if (raw === null || raw === undefined || raw === "") return null;
  return String(raw);
}

function thresholdSummary(
  thresholds: Record<string, unknown> | undefined,
): string {
  if (!thresholds || Object.keys(thresholds).length === 0) {
    return "Auto-rollback thresholds not configured.";
  }
  const rows = [
    ["error rate", thresholdValue(thresholds, "error_rate_percent"), "%"],
    ["p95 latency", thresholdValue(thresholds, "p95_latency_ms"), " ms"],
    ["cost delta", thresholdValue(thresholds, "cost_delta_percent"), "%"],
    [
      "tool failure",
      thresholdValue(thresholds, "tool_failure_rate_percent"),
      "%",
    ],
  ]
    .filter(([, value]) => value)
    .map(([label, value, unit]) => `${label} <= ${value}${unit}`);
  return rows.length > 0
    ? rows.join(" · ")
    : "Auto-rollback thresholds not configured.";
}

function thresholdMetricOptions(dep: Deployment): string[] {
  const keys = Object.keys(dep.autoRollbackThresholds ?? {});
  return keys.length > 0 ? keys : DEFAULT_THRESHOLD_METRICS;
}

function thresholdDefaultObserved(dep: Deployment, metric: string): number {
  const raw = dep.autoRollbackThresholds?.[metric];
  const value =
    typeof raw === "number" ? raw : typeof raw === "string" ? Number(raw) : 0;
  return Number.isFinite(value) ? value : 0;
}

function thresholdLabel(metric: string): string {
  return metric.replaceAll("_", " ");
}

export interface DeployTimelineProps {
  agentId: string;
  initialDeployments: Deployment[];
  initialEvidencePacks?: EvidencePack[];
  approvedChangePackage?: ChangePackage | null;
  focusedDeploymentId?: string | undefined;
  focusedPanel?: string | undefined;
  degradedReason?: string | undefined;
  startCanary?: StartFn;
  exportPack?: ExportEvidencePackFn;
  evaluateThreshold?: EvaluateThresholdFn;
  promote?: ActionFn;
  ramp?: RampFn;
  pause?: ActionFn;
  rollback?: ActionFn;
}

type Toast = { kind: "success" | "error"; message: string } | null;

function statusColor(status: Deployment["status"]): string {
  switch (status) {
    case "shadow":
      return "border-info/40 bg-info/10 text-info";
    case "canary":
      return "border-warning/40 bg-warning/10 text-warning";
    case "ramp":
      return "border-info/40 bg-info/10 text-info";
    case "live":
      return "border-success/40 bg-success/10 text-success";
    case "paused":
      return "border-border bg-muted text-foreground";
    case "rolled_back":
      return "border-destructive/40 bg-destructive/10 text-destructive";
    case "superseded":
      return "border-border bg-card text-muted-foreground";
    default:
      return "border-border bg-card text-foreground";
  }
}

/**
 * Vertical timeline of deployments for an agent. Editors can promote a
 * canary to 100% live, pause an in-flight rollout, or roll back a live
 * deployment to the previous version.
 */
export function DeployTimeline({
  agentId,
  initialDeployments,
  initialEvidencePacks = [],
  approvedChangePackage = null,
  focusedDeploymentId,
  focusedPanel,
  degradedReason,
  startCanary = defaultStartCanary,
  exportPack = defaultExportEvidencePack,
  evaluateThreshold = defaultEvaluateThreshold,
  promote = defaultPromote,
  ramp = defaultRamp,
  pause = defaultPause,
  rollback = defaultRollback,
}: DeployTimelineProps) {
  const [items, setItems] = useState<Deployment[]>(initialDeployments);
  const [evidencePacks, setEvidencePacks] =
    useState<EvidencePack[]>(initialEvidencePacks);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);
  const [rampTargets, setRampTargets] = useState<Record<string, number>>({});
  const [thresholdInputs, setThresholdInputs] = useState<
    Record<string, ThresholdInputState>
  >({});
  const [trafficPercent, setTrafficPercent] = useState(5);
  const [channelScope, setChannelScope] = useState(DEFAULT_CHANNEL_SCOPE);
  const [regionScope, setRegionScope] = useState(DEFAULT_REGION_SCOPE);
  const [segmentScope, setSegmentScope] = useState(DEFAULT_SEGMENT_SCOPE);
  const [holdTimeMinutes, setHoldTimeMinutes] = useState(30);
  const [errorRatePercent, setErrorRatePercent] = useState(2);
  const [p95LatencyMs, setP95LatencyMs] = useState(2500);
  const [costDeltaPercent, setCostDeltaPercent] = useState(20);
  const [toolFailureRatePercent, setToolFailureRatePercent] = useState(2);

  async function runAction(
    dep: Deployment,
    action: "promote" | "pause" | "rollback",
  ) {
    setBusy(`${dep.id}:${action}`);
    setToast(null);
    try {
      const fn =
        action === "promote" ? promote : action === "pause" ? pause : rollback;
      const updated = await fn(agentId, dep.id);
      setItems((prev) => {
        const next = prev.map((d) => (d.id === updated.id ? updated : d));
        if (action === "promote") {
          for (let i = 0; i < next.length; i += 1) {
            const item = next[i];
            if (!item) continue;
            if (item.id !== updated.id && item.status === "live") {
              next[i] = { ...item, status: "superseded", trafficPercent: 0 };
            }
          }
        }
        return next;
      });
      setToast({
        kind: "success",
        message:
          action === "promote"
            ? `Promoted ${dep.id} to 100% live.`
            : action === "pause"
              ? `Paused ${dep.id}.`
              : `Rolled back ${dep.id}.`,
      });
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? `${action} failed.`,
      });
    } finally {
      setBusy(null);
    }
  }

  async function handleStartRollout(stage: "shadow" | "canary") {
    if (!approvedChangePackage) return;
    setBusy(`start-${stage}`);
    setToast(null);
    try {
      const result = await startCanary(agentId, {
        change_package_id: approvedChangePackage.id,
        version_id: approvedChangePackage.to_version_id,
        stage,
        traffic_percent: stage === "shadow" ? 0 : trafficPercent,
        channel_scope: parseScopeList(channelScope),
        region_scope: parseScopeList(regionScope),
        segment_scope: parseScopeList(segmentScope),
        hold_time_minutes: holdTimeMinutes,
        auto_rollback_thresholds: {
          error_rate_percent: errorRatePercent,
          p95_latency_ms: p95LatencyMs,
          cost_delta_percent: costDeltaPercent,
          tool_failure_rate_percent: toolFailureRatePercent,
        },
        notes: `Started ${stage} from ${approvedChangePackage.evidence_pack_id}; hold ${holdTimeMinutes} min.`,
      });
      setItems((prev) => [result.deployment, ...prev]);
      if (result.evidence_pack) {
        setEvidencePacks((prev) => [result.evidence_pack!, ...prev]);
      }
      setToast({
        kind: "success",
        message: `Started ${stage} ${result.deployment.id}; evidence pack ${result.deployment.evidencePackId ?? "created"}.`,
      });
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? "start canary failed.",
      });
    } finally {
      setBusy(null);
    }
  }

  async function handleRamp(dep: Deployment) {
    const target =
      rampTargets[dep.id] ??
      Math.min(99, Math.max(dep.trafficPercent + 25, 25));
    setBusy(`${dep.id}:ramp`);
    setToast(null);
    try {
      const updated = await ramp(agentId, dep.id, target);
      setItems((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
      setRampTargets((prev) => {
        const next = { ...prev };
        delete next[dep.id];
        return next;
      });
      setToast({
        kind: "success",
        message: `Ramped ${dep.id} to ${updated.trafficPercent}% traffic.`,
      });
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? "ramp failed.",
      });
    } finally {
      setBusy(null);
    }
  }

  function thresholdInputFor(dep: Deployment): ThresholdInputState {
    const existing = thresholdInputs[dep.id];
    if (existing) return existing;
    const metric = thresholdMetricOptions(dep)[0] ?? "error_rate_percent";
    return {
      metric,
      observed: thresholdDefaultObserved(dep, metric),
      policy: "rollback",
    };
  }

  function updateThresholdInput(
    dep: Deployment,
    patch: Partial<ThresholdInputState>,
  ) {
    setThresholdInputs((prev) => ({
      ...prev,
      [dep.id]: {
        ...thresholdInputFor(dep),
        ...patch,
      },
    }));
  }

  async function handleEvaluateThreshold(dep: Deployment) {
    const thresholdInput = thresholdInputFor(dep);
    setBusy(`${dep.id}:threshold`);
    setToast(null);
    try {
      const result = await evaluateThreshold(agentId, dep.id, {
        metric: thresholdInput.metric,
        observed: thresholdInput.observed,
        policy: thresholdInput.policy,
        window: "5m",
        reason: "Manual Workbench rollout threshold check.",
      });
      setItems((prev) =>
        prev.map((item) =>
          item.id === result.deployment.id ? result.deployment : item,
        ),
      );
      setToast({
        kind: "success",
        message:
          result.decision === "no_action"
            ? `${thresholdLabel(result.metric)} is within threshold.`
            : `${thresholdLabel(result.metric)} breached; deployment ${result.decision}.`,
      });
    } catch (err) {
      setToast({
        kind: "error",
        message: (err as Error).message ?? "threshold evaluation failed.",
      });
    } finally {
      setBusy(null);
    }
  }

  const canary = items.find(
    (d) => d.status === "canary" || d.status === "ramp",
  );
  const live = items.find((d) => d.status === "live");
  const rolloutFocused =
    focusedPanel === "rollout" || focusedPanel === "promotion";
  const rollbackFocused = focusedPanel === "rollback";
  const evidenceById = new Map(evidencePacks.map((pack) => [pack.id, pack]));
  const deploymentEvidenceIds = new Set(
    items.map((item) => item.evidencePackId).filter(Boolean),
  );
  const latestUnmatchedEvidencePack =
    evidencePacks.find((pack) => !deploymentEvidenceIds.has(pack.id)) ?? null;

  return (
    <section className="flex flex-col gap-4" data-testid="deploy-timeline">
      {rolloutFocused || rollbackFocused ? (
        <p
          className="rounded-md border border-info/40 bg-info/5 px-3 py-2 text-sm text-info"
          data-testid="deploy-focused-panel"
        >
          Opened from evidence link:{" "}
          {focusedPanel === "promotion"
            ? "promotion controls are highlighted."
            : rolloutFocused
              ? "rollout controls are highlighted."
            : "rollback candidates are highlighted."}
        </p>
      ) : null}
      <header className="flex flex-col gap-1">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Deploys</h2>
            <p className="text-xs text-muted-foreground">
              Rollout starts only from an approved Change Package and creates an
              Evidence Pack.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-md border bg-background px-3 py-2 text-xs font-medium hover:bg-muted/50 disabled:opacity-50"
              data-testid="deploy-start-shadow"
              disabled={!approvedChangePackage || busy !== null}
              onClick={() => void handleStartRollout("shadow")}
              type="button"
            >
              {busy === "start-shadow" ? "Starting..." : "Start shadow"}
            </button>
            <button
              className="rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              data-testid="deploy-start-canary"
              disabled={!approvedChangePackage || busy !== null}
              onClick={() => void handleStartRollout("canary")}
              type="button"
            >
              {busy === "start-canary" ? "Starting..." : "Start canary"}
            </button>
          </div>
        </div>
        <p
          className="text-xs text-muted-foreground"
          data-testid="deploy-current-canary"
        >
          {canary
            ? `${canary.status === "ramp" ? "Ramp" : "Canary"} at ${canary.trafficPercent}% traffic (${canary.versionId}).`
            : "No active canary."}
        </p>
        <p
          className="text-xs text-muted-foreground"
          data-testid="deploy-current-live"
        >
          {live
            ? `Live: ${live.versionId} at ${live.trafficPercent}%.`
            : "No live deployment."}
        </p>
      </header>

      <section
        className={`rounded-lg border bg-card/70 p-3 ${
          rolloutFocused ? "ring-2 ring-focus ring-offset-2 ring-offset-background" : ""
        }`}
        data-testid="rollout-plan-controls"
        data-focused={rolloutFocused ? "true" : "false"}
      >
        <div className="flex flex-col gap-1">
          <h3 className="text-sm font-semibold">Rollout plan controls</h3>
          <p className="text-xs text-muted-foreground">
            Shadow and canary starts must declare traffic, channel scope,
            region scope, segment scope, hold time, and auto-rollback limits.
          </p>
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1 text-xs font-medium">
            Canary traffic %
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-traffic-percent"
              max={99}
              min={1}
              onChange={(event) =>
                setTrafficPercent(Number(event.target.value))
              }
              type="number"
              value={trafficPercent}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Channel scope
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-channel-scope"
              onChange={(event) => setChannelScope(event.target.value)}
              placeholder="web_chat, whatsapp"
              type="text"
              value={channelScope}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Region scope
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-region-scope"
              onChange={(event) => setRegionScope(event.target.value)}
              placeholder="global, eu-west-2"
              type="text"
              value={regionScope}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Segment scope
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-segment-scope"
              onChange={(event) => setSegmentScope(event.target.value)}
              placeholder="all-customers, enterprise"
              type="text"
              value={segmentScope}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Hold time minutes
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-hold-time"
              min={1}
              onChange={(event) =>
                setHoldTimeMinutes(Number(event.target.value))
              }
              type="number"
              value={holdTimeMinutes}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Error rate limit %
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-error-rate"
              min={0}
              onChange={(event) =>
                setErrorRatePercent(Number(event.target.value))
              }
              type="number"
              value={errorRatePercent}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            p95 latency limit ms
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-p95-latency"
              min={1}
              onChange={(event) => setP95LatencyMs(Number(event.target.value))}
              type="number"
              value={p95LatencyMs}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Cost delta limit %
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-cost-delta"
              min={0}
              onChange={(event) =>
                setCostDeltaPercent(Number(event.target.value))
              }
              type="number"
              value={costDeltaPercent}
            />
          </label>
          <label className="flex flex-col gap-1 text-xs font-medium">
            Tool failure limit %
            <input
              className="rounded-md border bg-background px-2 py-1 text-sm"
              data-testid="rollout-tool-failure"
              min={0}
              onChange={(event) =>
                setToolFailureRatePercent(Number(event.target.value))
              }
              type="number"
              value={toolFailureRatePercent}
            />
          </label>
        </div>
      </section>

      {degradedReason ? (
        <p
          className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
          data-testid="deploy-degraded"
          role="status"
        >
          Deployment history is unavailable. {degradedReason}
        </p>
      ) : null}

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="deploy-empty">
          {degradedReason
            ? "Deployment state cannot be confirmed until the control plane responds."
            : "No deployments yet for this agent."}
        </p>
      ) : (
        <ol className="flex flex-col gap-2" data-testid="deploy-list">
          {items.map((dep) => {
            const colors = statusColor(dep.status);
            const isActiveRollout =
              dep.status === "canary" || dep.status === "ramp";
            const isLive = dep.status === "live";
            const thresholdInput = thresholdInputFor(dep);
            const target =
              rampTargets[dep.id] ??
              Math.min(99, Math.max(dep.trafficPercent + 25, 25));
            return (
              <li
                key={dep.id}
                className={`rounded border p-3 ${colors} ${
                  dep.id === focusedDeploymentId ||
                  (rollbackFocused && dep.status === "live")
                    ? "ring-2 ring-focus ring-offset-2 ring-offset-background"
                    : ""
                }`}
                data-testid={`deploy-row-${dep.id}`}
                data-focused={
                  dep.id === focusedDeploymentId ||
                  (rollbackFocused && dep.status === "live")
                    ? "true"
                    : "false"
                }
                data-status={dep.status}
              >
                {dep.id === focusedDeploymentId ? (
                  <p
                    className="mb-2 rounded-md border border-info/40 bg-info/5 px-3 py-2 text-xs text-info"
                    data-testid={`deploy-focused-${dep.id}`}
                  >
                    Opened from evidence link: deployment {dep.id} is focused.
                  </p>
                ) : null}
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">
                      {dep.id} · {dep.versionId}
                    </p>
                    <p className="text-xs">
                      {dep.stage ?? dep.status} · {dep.trafficPercent}% ·
                      created {dep.createdAt}
                    </p>
                    {dep.notes ? (
                      <p className="text-xs italic">{dep.notes}</p>
                    ) : null}
                    <p
                      className="text-xs"
                      data-testid={`deploy-scope-${dep.id}`}
                    >
                      Scope: channels{" "}
                      {scopeLabel(dep.channelScope, "not declared")} · regions{" "}
                      {scopeLabel(dep.regionScope, "not declared")} · segments{" "}
                      {scopeLabel(dep.segmentScope, "not declared")} · hold{" "}
                      {dep.holdTimeMinutes ?? "not set"} min
                    </p>
                    <p
                      className="text-xs"
                      data-testid={`deploy-thresholds-${dep.id}`}
                    >
                      {thresholdSummary(dep.autoRollbackThresholds)}
                    </p>
                    {isActiveRollout ? (
                      <div
                        className="mt-2 grid gap-2 rounded border bg-background/70 p-2 text-xs md:grid-cols-4"
                        data-testid={`deploy-threshold-evaluator-${dep.id}`}
                      >
                        <label className="flex flex-col gap-1">
                          Metric
                          <select
                            className="rounded border bg-background px-2 py-1"
                            data-testid={`deploy-threshold-metric-${dep.id}`}
                            onChange={(event) =>
                              updateThresholdInput(dep, {
                                metric: event.target.value,
                                observed: thresholdDefaultObserved(
                                  dep,
                                  event.target.value,
                                ),
                              })
                            }
                            value={thresholdInput.metric}
                          >
                            {thresholdMetricOptions(dep).map((metric) => (
                              <option key={metric} value={metric}>
                                {thresholdLabel(metric)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="flex flex-col gap-1">
                          Observed
                          <input
                            className="rounded border bg-background px-2 py-1"
                            data-testid={`deploy-threshold-observed-${dep.id}`}
                            onChange={(event) =>
                              updateThresholdInput(dep, {
                                observed: Number(event.target.value),
                              })
                            }
                            type="number"
                            value={thresholdInput.observed}
                          />
                        </label>
                        <label className="flex flex-col gap-1">
                          Policy
                          <select
                            className="rounded border bg-background px-2 py-1"
                            data-testid={`deploy-threshold-policy-${dep.id}`}
                            onChange={(event) =>
                              updateThresholdInput(dep, {
                                policy: event.target.value as ThresholdPolicy,
                              })
                            }
                            value={thresholdInput.policy}
                          >
                            <option value="rollback">Rollback</option>
                            <option value="pause">Pause</option>
                          </select>
                        </label>
                        <button
                          className="self-end rounded-md border bg-background px-2 py-1 font-medium hover:bg-muted/60 disabled:opacity-50"
                          data-testid={`deploy-threshold-evaluate-${dep.id}`}
                          disabled={busy !== null}
                          onClick={() => void handleEvaluateThreshold(dep)}
                          type="button"
                        >
                          {busy === `${dep.id}:threshold`
                            ? "Evaluating..."
                            : "Evaluate"}
                        </button>
                      </div>
                    ) : null}
                    {dep.evidencePackId ? (
                      <p className="text-xs">
                        Evidence pack:{" "}
                        <span className="font-mono">{dep.evidencePackId}</span>
                      </p>
                    ) : null}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    {isActiveRollout ? (
                      <label className="flex items-center gap-2 text-xs">
                        <span>Ramp</span>
                        <input
                          aria-label={`Ramp ${dep.id} traffic target`}
                          className="w-24"
                          data-testid={`deploy-ramp-slider-${dep.id}`}
                          disabled={busy !== null}
                          max={99}
                          min={1}
                          onChange={(event) =>
                            setRampTargets((prev) => ({
                              ...prev,
                              [dep.id]: Number(event.target.value),
                            }))
                          }
                          step={1}
                          type="range"
                          value={target}
                        />
                        <span className="tabular-nums">{target}%</span>
                      </label>
                    ) : null}
                    <div className="flex gap-1">
                      <button
                        className="rounded border border-current text-xs px-2 py-1 disabled:opacity-50"
                        data-testid={`deploy-ramp-${dep.id}`}
                        disabled={!isActiveRollout || busy !== null}
                        onClick={() => void handleRamp(dep)}
                        type="button"
                      >
                        Ramp
                      </button>
                      <button
                        className="rounded border border-current text-xs px-2 py-1 disabled:opacity-50"
                        data-testid={`deploy-promote-${dep.id}`}
                        disabled={!isActiveRollout || busy !== null}
                        onClick={() => void runAction(dep, "promote")}
                        type="button"
                      >
                        Promote
                      </button>
                      <button
                        className="rounded border border-current text-xs px-2 py-1 disabled:opacity-50"
                        data-testid={`deploy-pause-${dep.id}`}
                        disabled={!isActiveRollout || busy !== null}
                        onClick={() => void runAction(dep, "pause")}
                        type="button"
                      >
                        Pause
                      </button>
                      <button
                        className="rounded border border-current text-xs px-2 py-1 disabled:opacity-50"
                        data-testid={`deploy-rollback-${dep.id}`}
                        disabled={!isLive || busy !== null}
                        onClick={() => void runAction(dep, "rollback")}
                        type="button"
                      >
                        Rollback
                      </button>
                    </div>
                  </div>
                </div>
                {dep.evidencePackId &&
                evidenceById.has(dep.evidencePackId) ? (
                  <EvidencePackManifest
                    evidencePack={evidenceById.get(dep.evidencePackId)!}
                    agentId={agentId}
                    exportPack={exportPack}
                  />
                ) : null}
              </li>
            );
          })}
        </ol>
      )}

      {latestUnmatchedEvidencePack ? (
        <EvidencePackManifest
          evidencePack={latestUnmatchedEvidencePack}
          agentId={agentId}
          exportPack={exportPack}
          compact
        />
      ) : null}

      {toast ? (
        <p
          className={
            toast.kind === "success"
              ? "text-xs text-success"
              : "text-xs text-destructive"
          }
          data-testid={`deploy-toast-${toast.kind}`}
          role="status"
        >
          {toast.message}
        </p>
      ) : null}
    </section>
  );
}

function manifestValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "not set";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function EvidencePackManifest({
  evidencePack,
  agentId,
  exportPack,
  compact = false,
}: {
  evidencePack: EvidencePack;
  agentId: string;
  exportPack: ExportEvidencePackFn;
  compact?: boolean;
}) {
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [exportResult, setExportResult] = useState<EvidencePackExport | null>(
    null,
  );
  const [exportError, setExportError] = useState<string | null>(null);
  const manifestRows: Array<[string, unknown]> = [
    ["Version", evidencePack.version_id],
    ["Deployment", evidencePack.deployment_id],
    ["Change Package", evidencePack.change_package_id],
    ["Commitment", evidencePack.version_manifest.commitment_document_id],
    ["Release Candidate", evidencePack.version_manifest.release_candidate_id],
    ["Content hash", evidencePack.version_manifest.content_hash],
    ["Rollback plan", evidencePack.rollback_plan_ref],
  ];
  const proofRows: Array<[string, unknown]> = [
    ["Behavior diff", evidencePack.behavior_diff_ref],
    ["Tool permissions", evidencePack.tool_permission_diff_ref],
    ["Knowledge diff", evidencePack.knowledge_diff_ref],
    ["Memory policy", evidencePack.memory_policy_ref],
    ["Channel plan", evidencePack.channel_deployment_plan_ref],
    ["Eval results", evidencePack.eval_results_ref],
    ["Approvals", evidencePack.approval_records_ref],
    ["Canary results", evidencePack.canary_results_ref],
    ["Audit log", evidencePack.audit_log_ref],
  ];

  async function runExport(rawFormat: string) {
    const format = rawFormat as EvidencePackExportFormat;
    setExportingFormat(format);
    setExportError(null);
    setExportResult(null);
    try {
      const result = await exportPack(agentId, evidencePack.id, {
        format,
        purpose: "deployment evidence review",
        redactions: ["secrets", "pii", "credentials", "pricing"],
      });
      setExportResult(result);
    } catch (error) {
      setExportError((error as Error).message || "Evidence export failed.");
    } finally {
      setExportingFormat(null);
    }
  }

  return (
    <article
      className={
        compact
          ? "rounded-md border bg-background p-3"
          : "mt-3 rounded-md border bg-background/70 p-3"
      }
      data-testid={`evidence-pack-manifest-${evidencePack.id}`}
    >
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold">Evidence Pack manifest</h3>
          <p className="text-xs text-muted-foreground">
            Exportable proof bundle for reviewers, security teams, and audit.
          </p>
        </div>
        <span className="font-mono text-xs">{evidencePack.id}</span>
      </div>
      <dl className="mt-3 grid gap-2 text-xs md:grid-cols-2 lg:grid-cols-3">
        {manifestRows.map(([label, value]) => (
          <div key={label} className="rounded border bg-card/70 p-2">
            <dt className="font-medium uppercase tracking-wide text-muted-foreground">
              {label}
            </dt>
            <dd className="mt-1 break-words font-mono">
              {manifestValue(value)}
            </dd>
          </div>
        ))}
      </dl>
      <dl className="mt-3 grid gap-2 text-xs md:grid-cols-2 lg:grid-cols-3">
        {proofRows.map(([label, value]) => (
          <div key={label} className="rounded border bg-card/70 p-2">
            <dt className="font-medium uppercase tracking-wide text-muted-foreground">
              {label}
            </dt>
            <dd className="mt-1 break-words font-mono">
              {manifestValue(value)}
            </dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-muted-foreground">
        Export formats: {evidencePack.export_formats.join(", ")}
      </p>
      <div
        className="mt-3 flex flex-wrap items-center gap-2"
        data-testid={`evidence-pack-export-actions-${evidencePack.id}`}
      >
        {evidencePack.export_formats.map((format) => (
          <button
            className="rounded-md border bg-background px-2 py-1 text-xs font-medium hover:bg-muted/60 disabled:opacity-50"
            data-testid={`evidence-pack-export-${evidencePack.id}-${format}`}
            disabled={exportingFormat !== null}
            key={format}
            onClick={() => void runExport(format)}
            type="button"
          >
            {exportingFormat === format ? "Exporting..." : `Export ${format}`}
          </button>
        ))}
      </div>
      {exportResult ? (
        <p
          className="mt-2 text-xs text-success"
          data-testid={`evidence-pack-export-result-${evidencePack.id}`}
          role="status"
        >
          Export {exportResult.id} ready. Redactions:{" "}
          {exportResult.redactions.join(", ")}. Download{" "}
          <a className="underline" href={exportResult.download_url}>
            {exportResult.format}
          </a>
          .
        </p>
      ) : null}
      {exportError ? (
        <p
          className="mt-2 text-xs text-destructive"
          data-testid={`evidence-pack-export-error-${evidencePack.id}`}
          role="status"
        >
          {exportError}
        </p>
      ) : null}
    </article>
  );
}
