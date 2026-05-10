"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ShieldCheck, XCircle } from "lucide-react";

import { StatePanel } from "@/components/target";
import {
  createPreApprovedClass,
  revokePreApprovedClass,
  type PreApprovedClass,
  type PreApprovedClassCreateInput,
  type PreApprovedRiskCeiling,
} from "@/lib/pre-approved-classes";

interface PreApprovedClassesPanelProps {
  agentId: string;
  initialItems: PreApprovedClass[];
  createClass?: (
    agentId: string,
    input: PreApprovedClassCreateInput,
  ) => Promise<PreApprovedClass>;
  revokeClass?: (
    agentId: string,
    classId: string,
  ) => Promise<PreApprovedClass>;
}

function csv(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function defaultExpiry(): string {
  const date = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  return date.toISOString().slice(0, 16);
}

function formatDate(value: string): string {
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp)
    ? value
    : new Date(timestamp).toISOString().replace(".000Z", "Z");
}

function changePackageHref(agentId: string, packageId: string): string {
  return `/agents/${encodeURIComponent(
    agentId,
  )}/deploys?change_package_id=${encodeURIComponent(packageId)}`;
}

function lifecycleText(item: PreApprovedClass): string | null {
  if (item.status === "expired") {
    return `Automatically expired and revoked ${
      item.expired_at ? formatDate(item.expired_at) : "when the time box ended"
    }.`;
  }
  if (item.status === "revoked") {
    return `Manually revoked ${
      item.revoked_at ? formatDate(item.revoked_at) : "by a reviewer"
    }.`;
  }
  if (item.status === "invalidated") {
    return `Invalidated ${
      item.invalidated_at ? formatDate(item.invalidated_at) : "by a policy change"
    }.`;
  }
  return null;
}

export function PreApprovedClassesPanel({
  agentId,
  initialItems,
  createClass = createPreApprovedClass,
  revokeClass = revokePreApprovedClass,
}: PreApprovedClassesPanelProps) {
  const [items, setItems] = useState(initialItems);
  const [grantedTo, setGrantedTo] = useState("");
  const [teamId, setTeamId] = useState("");
  const [allowed, setAllowed] = useState("instruction");
  const [excluded, setExcluded] = useState("tool,memory,channel,budget");
  const [risk, setRisk] = useState<PreApprovedRiskCeiling>("low");
  const [expiresAt, setExpiresAt] = useState(defaultExpiry);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const activeCount = useMemo(
    () => items.filter((item) => item.status === "active").length,
    [items],
  );
  const closedCount = items.length - activeCount;

  async function handleCreate() {
    setError(null);
    setNotice(null);
    const allowedTypes = csv(allowed);
    const excludedTypes = csv(excluded);
    if (!grantedTo.trim() && !teamId.trim()) {
      setError("Grant the class to a user or a team.");
      return;
    }
    if (allowedTypes.length === 0) {
      setError("Add at least one allowed change type.");
      return;
    }
    if (excludedTypes.length === 0) {
      setError("Name the excluded change types so the corridor stays narrow.");
      return;
    }
    if (risk === "high") {
      setError("High-risk changes require full approval, not a pre-approved class.");
      return;
    }
    const expiry = Date.parse(expiresAt);
    if (Number.isNaN(expiry)) {
      setError("Choose a valid expiration time.");
      return;
    }
    if (expiry > Date.now() + 30 * 24 * 60 * 60 * 1000) {
      setError("Pre-approved classes cannot run longer than 30 days.");
      return;
    }
    setBusy(true);
    try {
      const created = await createClass(agentId, {
        granted_to_user_id: grantedTo.trim(),
        team_id: teamId.trim(),
        allowed_change_types: allowedTypes,
        excluded_change_types: excludedTypes,
        risk_ceiling: risk,
        expires_at: new Date(expiresAt).toISOString(),
        reason: reason.trim(),
      });
      setItems((current) => [created, ...current]);
      setNotice(`Created pre-approved class ${created.id}.`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not create pre-approved class.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke(classId: string) {
    setError(null);
    setNotice(null);
    setRevokingId(classId);
    try {
      const revoked = await revokeClass(agentId, classId);
      setItems((current) =>
        current.map((item) => (item.id === revoked.id ? revoked : item)),
      );
      setNotice(`Revoked pre-approved class ${revoked.id}.`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not revoke pre-approved class.",
      );
    } finally {
      setRevokingId(null);
    }
  }

  return (
    <div className="space-y-4" data-testid="preapproved-classes-panel">
      <div className="rounded-md border bg-background/60 p-3 text-sm">
        <p className="font-medium">
          {activeCount} active pre-approved class{activeCount === 1 ? "" : "es"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Narrow, time-boxed approval corridors only. Tool, memory, channel,
          budget, and high-risk changes should stay excluded unless explicitly
          approved.
        </p>
        {closedCount > 0 ? (
          <p className="mt-2 text-xs font-medium text-muted-foreground">
            {closedCount} closed corridor{closedCount === 1 ? "" : "s"} retained
            for deployment evidence.
          </p>
        ) : null}
      </div>

      {error ? (
        <StatePanel state="error" title="Pre-approved class action failed">
          {error}
        </StatePanel>
      ) : null}
      {notice ? (
        <StatePanel state="success" title="Pre-approved class updated">
          {notice}
        </StatePanel>
      ) : null}

      <div className="grid gap-3 rounded-md border bg-background/60 p-3 text-sm md:grid-cols-2">
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Granted to user
          </span>
          <input
            className="h-9 w-full rounded-md border bg-background px-2"
            value={grantedTo}
            onChange={(event) => setGrantedTo(event.currentTarget.value)}
            placeholder="builder@example.com"
            data-testid="preapproved-user"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Or team
          </span>
          <input
            className="h-9 w-full rounded-md border bg-background px-2"
            value={teamId}
            onChange={(event) => setTeamId(event.currentTarget.value)}
            placeholder="support-ops"
            data-testid="preapproved-team"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Allowed change types
          </span>
          <input
            className="h-9 w-full rounded-md border bg-background px-2"
            value={allowed}
            onChange={(event) => setAllowed(event.currentTarget.value)}
            data-testid="preapproved-allowed"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Excluded change types
          </span>
          <input
            className="h-9 w-full rounded-md border bg-background px-2"
            value={excluded}
            onChange={(event) => setExcluded(event.currentTarget.value)}
            data-testid="preapproved-excluded"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Risk ceiling
          </span>
          <select
            className="h-9 w-full rounded-md border bg-background px-2"
            value={risk}
            onChange={(event) =>
              setRisk(event.currentTarget.value as PreApprovedRiskCeiling)
            }
            data-testid="preapproved-risk"
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-xs font-medium text-muted-foreground">
            Expires
          </span>
          <input
            className="h-9 w-full rounded-md border bg-background px-2"
            type="datetime-local"
            value={expiresAt}
            onChange={(event) => setExpiresAt(event.currentTarget.value)}
            data-testid="preapproved-expires"
          />
        </label>
        <label className="space-y-1 md:col-span-2">
          <span className="text-xs font-medium text-muted-foreground">
            Reason
          </span>
          <textarea
            className="min-h-16 w-full rounded-md border bg-background p-2"
            value={reason}
            onChange={(event) => setReason(event.currentTarget.value)}
            data-testid="preapproved-reason"
          />
        </label>
        <button
          type="button"
          className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => void handleCreate()}
          disabled={busy}
          data-testid="preapproved-create"
        >
          <ShieldCheck className="h-4 w-4" aria-hidden />
          {busy ? "Creating" : "Create class"}
        </button>
      </div>

      {items.length > 0 ? (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="rounded-md border bg-background/60 p-3 text-sm"
              data-testid={`preapproved-class-${item.id}`}
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="font-medium">
                    {item.id} - {item.status}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    allowed {item.allowed_change_types.join(", ")}; excludes{" "}
                    {item.excluded_change_types.join(", ") || "none"}; risk{" "}
                    {"<="}{" "}
                    {item.risk_ceiling}; expires {formatDate(item.expires_at)}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    grantee: {item.granted_to_user_id || item.team_id}
                  </p>
                  {lifecycleText(item) ? (
                    <p
                      className="mt-1 text-xs font-medium text-muted-foreground"
                      data-testid={`preapproved-lifecycle-${item.id}`}
                    >
                      {lifecycleText(item)}
                    </p>
                  ) : null}
                  <div
                    className="mt-2 text-xs text-muted-foreground"
                    data-testid={`preapproved-usage-${item.id}`}
                  >
                    {item.used_by_change_packages.length > 0 ? (
                      <>
                        <span>Used by </span>
                        <span className="inline-flex flex-wrap gap-1">
                          {item.used_by_change_packages.map((packageId) => (
                            <Link
                              key={packageId}
                              href={changePackageHref(agentId, packageId)}
                              className="rounded-md border bg-card px-1.5 py-0.5 font-mono text-[0.7rem] underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                              data-testid={`preapproved-usage-link-${packageId}`}
                            >
                              {packageId}
                            </Link>
                          ))}
                        </span>
                      </>
                    ) : (
                      <span>No Change Package has used this class yet.</span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  className="inline-flex w-fit items-center gap-2 rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                  onClick={() => void handleRevoke(item.id)}
                  disabled={item.status !== "active" || revokingId === item.id}
                  data-testid={`preapproved-revoke-${item.id}`}
                >
                  <XCircle className="h-4 w-4" aria-hidden />
                  {revokingId === item.id ? "Revoking" : "Revoke"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="rounded-md border border-dashed p-3 text-sm text-muted-foreground">
          No pre-approved classes are active for this agent.
        </p>
      )}
    </div>
  );
}
