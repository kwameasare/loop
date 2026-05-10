"use client";

import { useEffect, useState } from "react";
import { History, PackageCheck, TriangleAlert } from "lucide-react";

import {
  deprecateMarketplaceItem,
  listMarketplaceInstalls,
  publishMarketplaceItemVersion,
  type MarketplaceInstall,
  type MarketplaceItem,
} from "@/lib/marketplace";
import { cn } from "@/lib/utils";

export interface MarketplaceOperationsProps {
  item: MarketplaceItem;
  workspaceId?: string;
  installStatus?: MarketplaceInstall | null;
  installError?: string | null;
  onItemChanged?: (item: MarketplaceItem) => void;
}

export function MarketplaceOperations({
  item,
  workspaceId,
  installStatus,
  installError,
  onItemChanged,
}: MarketplaceOperationsProps) {
  const [version, setVersion] = useState("");
  const [changelog, setChangelog] = useState("");
  const [deprecationReason, setDeprecationReason] = useState("");
  const [installs, setInstalls] = useState<MarketplaceInstall[]>([]);
  const [busy, setBusy] = useState<"version" | "deprecate" | "history" | null>(
    null,
  );
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canManage = item.publisher === "private-workspace";

  useEffect(() => {
    setInstalls([]);
    setStatus(null);
    setError(null);
    if (!workspaceId) return;
    let cancelled = false;
    setBusy("history");
    void listMarketplaceInstalls(workspaceId, item.id)
      .then((next) => {
        if (!cancelled) setInstalls(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load install history.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setBusy(null);
      });
    return () => {
      cancelled = true;
    };
  }, [item.id, workspaceId]);

  useEffect(() => {
    if (!installStatus) return;
    setInstalls((current) => {
      if (current.some((install) => install.installId === installStatus.installId)) {
        return current;
      }
      return [installStatus, ...current];
    });
    setStatus(`Installed ${installStatus.version}. Audit: ${installStatus.auditRef}.`);
  }, [installStatus]);

  async function publishVersion() {
    if (!workspaceId) {
      setError("Select a workspace before publishing a version.");
      return;
    }
    setBusy("version");
    setError(null);
    setStatus(null);
    try {
      const updated = await publishMarketplaceItemVersion(workspaceId, item.id, {
        version,
        changelog,
      });
      onItemChanged?.(updated);
      setStatus(`Published version ${version}.`);
      setVersion("");
      setChangelog("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not publish this version.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function deprecateItem() {
    if (!workspaceId) {
      setError("Select a workspace before deprecating an item.");
      return;
    }
    setBusy("deprecate");
    setError(null);
    setStatus(null);
    try {
      const updated = await deprecateMarketplaceItem(
        workspaceId,
        item.id,
        deprecationReason,
      );
      onItemChanged?.(updated);
      setStatus("Deprecated item and recorded the audit event.");
      setDeprecationReason("");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not deprecate this item.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <aside
      className="flex flex-col gap-4 rounded-md border border-border bg-card p-4"
      data-testid="marketplace-operations"
      aria-labelledby="marketplace-operations-heading"
    >
      <header>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Workspace lifecycle
        </p>
        <h2 className="mt-1 text-sm font-semibold" id="marketplace-operations-heading">
          Install history, versions, and deprecation
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Marketplace changes must leave audit evidence; private workspace items
          can be versioned or deprecated from here.
        </p>
      </header>

      {!workspaceId ? (
        <p className="rounded-md border border-warning/50 bg-warning/10 p-3 text-xs text-warning">
          Select a workspace before installing, publishing, or reviewing usage.
        </p>
      ) : null}

      {installError ? (
        <p
          className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
          role="alert"
          data-testid="marketplace-install-error"
        >
          {installError}
        </p>
      ) : null}

      {status ? (
        <p
          className="rounded-md border border-success/40 bg-success/10 p-3 text-xs text-success"
          role="status"
          data-testid="marketplace-operation-status"
        >
          {status}
        </p>
      ) : null}

      {error ? (
        <p
          className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
          role="alert"
          data-testid="marketplace-operation-error"
        >
          {error}
        </p>
      ) : null}

      <section className="rounded-md border border-border bg-background p-3">
        <h3 className="flex items-center gap-2 text-sm font-medium">
          <History aria-hidden="true" className="h-4 w-4" />
          Install audit
        </h3>
        {busy === "history" ? (
          <p className="mt-2 text-xs text-muted-foreground">Loading install history...</p>
        ) : installs.length > 0 ? (
          <ul className="mt-2 flex flex-col gap-2" data-testid="marketplace-installs">
            {installs.map((install) => (
              <li
                key={install.installId}
                className="rounded-sm border border-border p-2 text-xs"
              >
                <p className="font-medium">v{install.version}</p>
                <p className="text-muted-foreground">
                  {install.installedBy} · {install.installedAt}
                </p>
                <p className="font-mono text-muted-foreground">{install.auditRef}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-xs text-muted-foreground" data-testid="marketplace-installs-empty">
            No installs recorded for this workspace yet.
          </p>
        )}
      </section>

      <section
        className={cn(
          "rounded-md border border-border bg-background p-3",
          !canManage && "opacity-70",
        )}
      >
        <h3 className="flex items-center gap-2 text-sm font-medium">
          <PackageCheck aria-hidden="true" className="h-4 w-4" />
          Publish private version
        </h3>
        {!canManage ? (
          <p className="mt-2 text-xs text-muted-foreground">
            Version publishing is controlled by the item publisher.
          </p>
        ) : (
          <div className="mt-3 flex flex-col gap-2">
            <label className="flex flex-col gap-1 text-xs">
              <span className="font-medium">Version</span>
              <input
                type="text"
                value={version}
                onChange={(event) => setVersion(event.target.value)}
                placeholder="1.1.0"
                className="h-9 rounded-md border border-border bg-card px-3 text-sm focus:outline-none focus:ring-2 focus:ring-focus"
                data-testid="marketplace-version-input"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs">
              <span className="font-medium">Changelog</span>
              <textarea
                value={changelog}
                onChange={(event) => setChangelog(event.target.value)}
                rows={3}
                className="rounded-md border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-focus"
                data-testid="marketplace-version-changelog"
              />
            </label>
            <button
              type="button"
              disabled={!workspaceId || !version || !changelog || busy === "version"}
              onClick={() => void publishVersion()}
              className="inline-flex h-9 items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              data-testid="marketplace-publish-version"
            >
              {busy === "version" ? "Publishing..." : "Publish version"}
            </button>
          </div>
        )}
      </section>

      <section
        className={cn(
          "rounded-md border border-border bg-background p-3",
          !canManage && "opacity-70",
        )}
      >
        <h3 className="flex items-center gap-2 text-sm font-medium">
          <TriangleAlert aria-hidden="true" className="h-4 w-4" />
          Deprecate private item
        </h3>
        {!canManage ? (
          <p className="mt-2 text-xs text-muted-foreground">
            Deprecation is controlled by the item publisher.
          </p>
        ) : (
          <div className="mt-3 flex flex-col gap-2">
            <label className="flex flex-col gap-1 text-xs">
              <span className="font-medium">Reason</span>
              <textarea
                value={deprecationReason}
                onChange={(event) => setDeprecationReason(event.target.value)}
                rows={3}
                className="rounded-md border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-focus"
                data-testid="marketplace-deprecate-reason"
              />
            </label>
            <button
              type="button"
              disabled={!workspaceId || busy === "deprecate"}
              onClick={() => void deprecateItem()}
              className="inline-flex h-9 items-center justify-center rounded-md border border-destructive/40 bg-background px-3 text-sm font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50"
              data-testid="marketplace-deprecate"
            >
              {busy === "deprecate" ? "Deprecating..." : "Deprecate item"}
            </button>
          </div>
        )}
      </section>
    </aside>
  );
}
