"use client";

import { useState } from "react";

import {
  pauseDeployment as defaultPause,
  promoteDeployment as defaultPromote,
  rollbackDeployment as defaultRollback,
  startCanaryDeployment as defaultStartCanary,
  type Deployment,
} from "@/lib/deploys";
import type { ChangePackage } from "@/lib/change-package";

type ActionFn = (agentId: string, depId: string) => Promise<Deployment>;
type StartFn = (
  agentId: string,
  input: {
    change_package_id: string;
    version_id?: string;
    traffic_percent?: number;
    channel_scope?: string[];
    notes?: string | null;
  },
) => Promise<{ deployment: Deployment }>;

export interface DeployTimelineProps {
  agentId: string;
  initialDeployments: Deployment[];
  approvedChangePackage?: ChangePackage | null;
  startCanary?: StartFn;
  promote?: ActionFn;
  pause?: ActionFn;
  rollback?: ActionFn;
}

type Toast = { kind: "success" | "error"; message: string } | null;

function statusColor(status: Deployment["status"]): string {
  switch (status) {
    case "canary":
      return "border-amber-300 bg-amber-50 text-amber-900";
    case "live":
      return "border-emerald-300 bg-emerald-50 text-emerald-900";
    case "paused":
      return "border-slate-300 bg-slate-50 text-slate-900";
    case "rolled_back":
      return "border-red-300 bg-red-50 text-red-900";
    case "superseded":
      return "border-gray-200 bg-white text-gray-500";
    default:
      return "border-gray-200 bg-white text-gray-700";
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
  approvedChangePackage = null,
  startCanary = defaultStartCanary,
  promote = defaultPromote,
  pause = defaultPause,
  rollback = defaultRollback,
}: DeployTimelineProps) {
  const [items, setItems] = useState<Deployment[]>(initialDeployments);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);

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

  async function handleStartCanary() {
    if (!approvedChangePackage) return;
    setBusy("start-canary");
    setToast(null);
    try {
      const result = await startCanary(agentId, {
        change_package_id: approvedChangePackage.id,
        version_id: approvedChangePackage.to_version_id,
        traffic_percent: 5,
        channel_scope: ["web_chat"],
        notes: `Started from ${approvedChangePackage.evidence_pack_id}`,
      });
      setItems((prev) => [result.deployment, ...prev]);
      setToast({
        kind: "success",
        message: `Started canary ${result.deployment.id}; evidence pack ${result.deployment.evidencePackId ?? "created"}.`,
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

  const canary = items.find((d) => d.status === "canary");
  const live = items.find((d) => d.status === "live");

  return (
    <section className="flex flex-col gap-4" data-testid="deploy-timeline">
      <header className="flex flex-col gap-1">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Deploys</h2>
            <p className="text-xs text-muted-foreground">
              Rollout starts only from an approved Change Package and creates an
              Evidence Pack.
            </p>
          </div>
          <button
            className="rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            data-testid="deploy-start-canary"
            disabled={!approvedChangePackage || busy !== null}
            onClick={handleStartCanary}
            type="button"
          >
            {busy === "start-canary" ? "Starting..." : "Start canary"}
          </button>
        </div>
        <p
          className="text-xs text-muted-foreground"
          data-testid="deploy-current-canary"
        >
          {canary
            ? `Canary at ${canary.trafficPercent}% traffic (${canary.versionId}).`
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

      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="deploy-empty">
          No deployments yet for this agent.
        </p>
      ) : (
        <ol className="flex flex-col gap-2" data-testid="deploy-list">
          {items.map((dep) => {
            const colors = statusColor(dep.status);
            const isCanary = dep.status === "canary";
            const isLive = dep.status === "live";
            return (
              <li
                key={dep.id}
                className={`rounded border p-3 ${colors}`}
                data-testid={`deploy-row-${dep.id}`}
                data-status={dep.status}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">
                      {dep.id} · {dep.versionId}
                    </p>
                    <p className="text-xs">
                      {dep.status} · {dep.trafficPercent}% · created{" "}
                      {dep.createdAt}
                    </p>
                    {dep.notes ? (
                      <p className="text-xs italic">{dep.notes}</p>
                    ) : null}
                    {dep.evidencePackId ? (
                      <p className="text-xs">
                        Evidence pack:{" "}
                        <span className="font-mono">{dep.evidencePackId}</span>
                      </p>
                    ) : null}
                  </div>
                  <div className="flex gap-1">
                    <button
                      className="rounded border border-current text-xs px-2 py-1 disabled:opacity-50"
                      data-testid={`deploy-promote-${dep.id}`}
                      disabled={!isCanary || busy !== null}
                      onClick={() => runAction(dep, "promote")}
                      type="button"
                    >
                      Promote
                    </button>
                    <button
                      className="rounded border border-current text-xs px-2 py-1 disabled:opacity-50"
                      data-testid={`deploy-pause-${dep.id}`}
                      disabled={!isCanary || busy !== null}
                      onClick={() => runAction(dep, "pause")}
                      type="button"
                    >
                      Pause
                    </button>
                    <button
                      className="rounded border border-current text-xs px-2 py-1 disabled:opacity-50"
                      data-testid={`deploy-rollback-${dep.id}`}
                      disabled={!isLive || busy !== null}
                      onClick={() => runAction(dep, "rollback")}
                      type="button"
                    >
                      Rollback
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {toast ? (
        <p
          className={
            toast.kind === "success"
              ? "text-xs text-emerald-700"
              : "text-xs text-red-600"
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
