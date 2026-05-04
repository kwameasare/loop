"use client";

/**
 * S594: workspace creation form with region selector.
 *
 * Renders a form with name, slug, and a region dropdown. The region
 * dropdown defaults to the value returned by ``inferRegion()`` (which
 * uses the browser's IANA timezone) and shows a clear
 * cannot-change-later notice — region pinning is enforced by the
 * control plane (S593) and the workspace row is region-bound for the
 * lifetime of the tenant.
 *
 * On submit we POST to ``/v1/workspaces`` (mirrored from
 * ``Operations.PostWorkspaces`` in openapi-types.ts). The submit
 * handler is a prop so the page route can swap in a real client; this
 * keeps the form testable in isolation without faking ``fetch``.
 */

import { useEffect, useState } from "react";
import type { RegionName, WorkspaceCreate } from "@/lib/openapi-types";
import { DEFAULT_REGION, REGIONS, inferRegion } from "@/lib/regions";

export interface WorkspaceCreateFormProps {
  onSubmit: (payload: WorkspaceCreate) => Promise<void> | void;
  /** Override inferred region for tests. */
  initialRegion?: RegionName;
}

export function WorkspaceCreateForm({ onSubmit, initialRegion }: WorkspaceCreateFormProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [region, setRegion] = useState<RegionName>(initialRegion ?? DEFAULT_REGION);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-run inference once the client has hydrated; on the server we
  // ship DEFAULT_REGION so the prerender is stable.
  useEffect(() => {
    if (initialRegion) return;
    setRegion(inferRegion());
  }, [initialRegion]);

  const selected =
    REGIONS.find((r) => r.value === region) ??
    REGIONS[0] ??
    { value: region, label: region, description: "" };

  return (
    <form
      data-testid="workspace-create-form"
      className="flex max-w-md flex-col gap-4"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!name || !slug) {
          setError("Workspace name and slug are required.");
          return;
        }
        setError(null);
        setSubmitting(true);
        try {
          await onSubmit({ name, slug, region });
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to create workspace.");
        } finally {
          setSubmitting(false);
        }
      }}
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Workspace name</span>
        <input
          data-testid="workspace-create-name"
          className="rounded-md border bg-background px-2 py-1"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Slug</span>
        <input
          data-testid="workspace-create-slug"
          className="rounded-md border bg-background px-2 py-1"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          required
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Region</span>
        <select
          data-testid="workspace-create-region"
          className="rounded-md border bg-background px-2 py-1"
          value={region}
          onChange={(e) => setRegion(e.target.value as RegionName)}
        >
          {REGIONS.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        <span
          data-testid="workspace-create-region-description"
          className="text-xs text-muted-foreground"
        >
          {selected.description}
        </span>
      </label>

      <p
        data-testid="workspace-create-region-notice"
        role="note"
        className="rounded-md border border-amber-500/50 bg-amber-500/10 p-2 text-xs text-amber-900 dark:text-amber-200"
      >
        <strong>Region cannot be changed after the workspace is created.</strong>{" "}
        All data, telemetry, and inference for this workspace will stay in the selected
        region. To change region you must create a new workspace and migrate data
        manually.
      </p>

      {error ? (
        <p data-testid="workspace-create-error" role="alert" className="text-sm text-red-600">
          {error}
        </p>
      ) : null}

      <button
        type="submit"
        data-testid="workspace-create-submit"
        disabled={submitting}
        className="rounded-md border bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        {submitting ? "Creating…" : "Create workspace"}
      </button>
    </form>
  );
}
