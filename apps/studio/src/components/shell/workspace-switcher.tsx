"use client";

/**
 * S154: Workspace switcher dropdown.
 *
 * Renders a ``<select>``-driven dropdown listing the user's
 * workspaces. The current selection is reflected in the URL
 * (``?ws=<slug>``) and persisted to localStorage so the studio
 * remembers the user's last context across sessions.
 *
 * We use a native ``<select>`` to keep the surface a11y-friendly and
 * dependency-free; a richer combobox can ship later as design
 * matures.
 */

import { useActiveWorkspace } from "@/lib/use-active-workspace";

export function WorkspaceSwitcher() {
  const { workspaces, active, isLoading, degradedReason, setActive } =
    useActiveWorkspace();
  if (isLoading) {
    return (
      <span
        className="interactive-lift inline-flex h-8 items-center rounded-md border bg-card/70 px-2 text-sm font-medium shadow-sm backdrop-blur"
        data-testid="workspace-switcher-loading"
      >
        Workspace
      </span>
    );
  }
  if (workspaces.length === 0 || !active) {
    if (degradedReason) {
      return (
        <span
          className="interactive-lift inline-flex h-8 items-center rounded-md border border-warning/40 bg-warning/10 px-2 text-sm font-medium text-warning shadow-sm backdrop-blur"
          data-testid="workspace-switcher-degraded"
          role="status"
          title={degradedReason}
        >
          Workspace unavailable
        </span>
      );
    }
    return null;
  }
  return (
    <label
      className="flex items-center gap-2 text-sm"
      data-testid="workspace-switcher"
    >
      <span className="sr-only">Active workspace</span>
      <select
        value={active.slug}
        onChange={(event) => {
          const next = workspaces.find((w) => w.slug === event.target.value);
          if (next) setActive(next);
        }}
        className="interactive-lift h-8 rounded-md border bg-card/70 px-2 text-sm font-medium shadow-sm backdrop-blur"
        data-testid="workspace-switcher-select"
      >
        {workspaces.map((w) => (
          <option key={w.id} value={w.slug}>
            {w.name}
          </option>
        ))}
      </select>
    </label>
  );
}
