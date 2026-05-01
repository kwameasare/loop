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
  const { workspaces, active, isLoading, setActive } = useActiveWorkspace();
  if (isLoading) {
    return (
      <span className="text-sm text-muted-foreground" data-testid="workspace-switcher-loading">
        Loading workspaces…
      </span>
    );
  }
  if (workspaces.length === 0 || !active) {
    return null;
  }
  return (
    <label className="flex items-center gap-2 text-sm" data-testid="workspace-switcher">
      <span className="sr-only">Active workspace</span>
      <select
        value={active.slug}
        onChange={(event) => {
          const next = workspaces.find((w) => w.slug === event.target.value);
          if (next) setActive(next);
        }}
        className="rounded-md border bg-background px-2 py-1 text-sm font-medium"
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
