"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { type AgentVersionSummary } from "@/lib/cp-api";
import { diffConfigJson } from "@/lib/agent-version-diff";

export interface AgentVersionsTableProps {
  agentId: string;
  versions: AgentVersionSummary[];
  nextCursor: string | null;
}

function versionLabel(version: AgentVersionSummary): string {
  return `v${version.version}`;
}

function formatTimestamp(value: string | null): string {
  if (!value) return "Not deployed";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return `${parsed.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

function shortHash(value: string): string {
  return value ? value.slice(0, 12) : "None";
}

function statusClass(value: string): string {
  switch (value) {
    case "active":
    case "passed":
      return "border-green-200 bg-green-50 text-green-700";
    case "failed":
    case "rolled_back":
      return "border-red-200 bg-red-50 text-red-700";
    case "canary":
    case "running":
      return "border-blue-200 bg-blue-50 text-blue-700";
    default:
      return "border-border bg-muted text-muted-foreground";
  }
}

export function AgentVersionsTable({
  agentId,
  versions,
  nextCursor,
}: AgentVersionsTableProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const sortedVersions = useMemo(
    () => [...versions].sort((left, right) => right.version - left.version),
    [versions],
  );
  const selectedIndex = selectedId
    ? sortedVersions.findIndex((version) => version.id === selectedId)
    : -1;
  const selectedVersion =
    selectedIndex >= 0 ? sortedVersions[selectedIndex] : null;
  const priorVersion =
    selectedIndex >= 0 ? (sortedVersions[selectedIndex + 1] ?? null) : null;
  const diffRows = useMemo(
    () =>
      selectedVersion && priorVersion
        ? diffConfigJson(priorVersion.config_json, selectedVersion.config_json)
        : [],
    [priorVersion, selectedVersion],
  );
  const nextHref = nextCursor
    ? `/agents/${agentId}/versions?${new URLSearchParams({
        cursor: nextCursor,
      }).toString()}`
    : null;

  if (sortedVersions.length === 0) {
    return (
      <section
        className="rounded-lg border border-dashed p-6"
        data-testid="agent-versions-empty"
      >
        <h2 className="text-base font-medium">No versions yet</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Deploy an agent version to compare config changes over time.
        </p>
      </section>
    );
  }

  return (
    <section className="flex flex-col gap-4" data-testid="agent-versions">
      <div className="overflow-hidden rounded-lg border">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-muted text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-medium">Version</th>
              <th className="px-4 py-3 font-medium">Deploy</th>
              <th className="px-4 py-3 font-medium">Eval</th>
              <th className="px-4 py-3 font-medium">Deployed</th>
              <th className="px-4 py-3 font-medium">Code hash</th>
              <th className="px-4 py-3 text-right font-medium">Diff</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {sortedVersions.map((version) => (
              <tr key={version.id} data-testid="agent-version-row">
                <td className="px-4 py-3 font-medium">
                  {versionLabel(version)}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${statusClass(
                      version.deploy_state,
                    )}`}
                  >
                    {version.deploy_state}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${statusClass(
                      version.eval_status,
                    )}`}
                  >
                    {version.eval_status}
                  </span>
                </td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatTimestamp(version.deployed_at ?? version.created_at)}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                  {shortHash(version.code_hash)}
                </td>
                <td className="px-4 py-3 text-right">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    data-testid={`agent-version-diff-${version.version}`}
                    onClick={() => setSelectedId(version.id)}
                  >
                    View diff
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {nextHref ? (
        <div className="flex justify-end">
          <Link
            className="inline-flex h-9 items-center rounded-md border border-border px-3 text-sm font-medium hover:bg-muted"
            data-testid="agent-versions-next"
            href={nextHref}
          >
            Older versions
          </Link>
        </div>
      ) : null}

      {selectedVersion ? (
        <div
          aria-label={`${versionLabel(selectedVersion)} config diff`}
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          data-testid="agent-version-diff-modal"
          role="dialog"
        >
          <div className="flex max-h-[85vh] w-full max-w-3xl flex-col gap-4 overflow-hidden rounded-xl bg-background p-6 shadow-lg">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold">
                  {versionLabel(selectedVersion)} config diff
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  {priorVersion
                    ? `Compared with ${versionLabel(priorVersion)}`
                    : "No prior version is available to compare."}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                data-testid="agent-version-diff-close"
                onClick={() => setSelectedId(null)}
              >
                Close
              </Button>
            </div>

            {priorVersion ? (
              diffRows.length > 0 ? (
                <div className="overflow-auto rounded-md border">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="border-b bg-muted text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2 font-medium">Path</th>
                        <th className="px-3 py-2 font-medium">Before</th>
                        <th className="px-3 py-2 font-medium">After</th>
                        <th className="px-3 py-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {diffRows.map((row) => (
                        <tr
                          key={`${row.path}:${row.status}`}
                          data-testid="agent-version-diff-row"
                        >
                          <td className="px-3 py-2 font-mono text-xs">
                            {row.path}
                          </td>
                          <td className="whitespace-pre-wrap px-3 py-2 font-mono text-xs text-muted-foreground">
                            {row.before}
                          </td>
                          <td className="whitespace-pre-wrap px-3 py-2 font-mono text-xs">
                            {row.after}
                          </td>
                          <td className="px-3 py-2">
                            <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-xs">
                              {row.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p
                  className="rounded-md border border-dashed p-4 text-sm text-muted-foreground"
                  data-testid="agent-version-diff-empty"
                >
                  No config changes from {versionLabel(priorVersion)}.
                </p>
              )
            ) : (
              <p
                className="rounded-md border border-dashed p-4 text-sm text-muted-foreground"
                data-testid="agent-version-diff-missing-prior"
              >
                Select a version with a previous version loaded on this page to
                inspect config changes.
              </p>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
