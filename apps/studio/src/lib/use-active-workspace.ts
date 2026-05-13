"use client";

/**
 * S154: ``useActiveWorkspace`` — read & set the active workspace.
 *
 * Source of truth (in priority order):
 *   1. ``?ws=<slug>`` on the current URL.
 *   2. ``localStorage["loop:active-workspace"]`` for cross-tab persistence.
 *   3. The first authorized workspace returned by ``listWorkspaces()``.
 *
 * Updates flow back through the router so the URL stays in sync with
 * the dropdown selection — this also gives us deep-link support for
 * sharing workspace-scoped URLs.
 */

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { listWorkspaces, type Workspace } from "@/lib/workspaces";

const STORAGE_KEY = "loop:active-workspace";

export interface UseActiveWorkspaceResult {
  workspaces: Workspace[];
  active: Workspace | null;
  isLoading: boolean;
  degradedReason?: string | undefined;
  setActive: (workspace: Workspace) => void;
}

export function useActiveWorkspace(): UseActiveWorkspaceResult {
  const router = useRouter();
  const pathname = usePathname();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [storedSlug, setStoredSlug] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [degradedReason, setDegradedReason] = useState<string | undefined>();

  useEffect(() => {
    let cancelled = false;
    void listWorkspaces()
      .catch((error: unknown) => ({
        workspaces: [],
        degraded_reason:
          error instanceof Error
            ? error.message
            : "Could not load workspace context.",
      }))
      .then((res) => {
        if (cancelled) return;
        setWorkspaces(res.workspaces);
        setDegradedReason(res.degraded_reason);
        setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setStoredSlug(window.localStorage.getItem(STORAGE_KEY));
    setSearch(window.location.search);

    function onStorage(event: StorageEvent) {
      if (event.key !== STORAGE_KEY) return;
      setStoredSlug(event.newValue);
    }

    function onPopState() {
      setSearch(window.location.search);
    }

    window.addEventListener("storage", onStorage);
    window.addEventListener("popstate", onPopState);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("popstate", onPopState);
    };
  }, []);

  const params = new URLSearchParams(search);
  const urlSlug = params.get("ws");
  const targetSlug = urlSlug || storedSlug;
  const active =
    workspaces.find((w) => w.slug === targetSlug) || workspaces[0] || null;

  const setActive = useCallback(
    (workspace: Workspace) => {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, workspace.slug);
        setStoredSlug(workspace.slug);
      }
      const next = new URLSearchParams(search);
      next.set("ws", workspace.slug);
      const nextSearch = `?${next.toString()}`;
      setSearch(nextSearch);
      router.replace(`${pathname}${nextSearch}`);
    },
    [pathname, router, search],
  );

  return { workspaces, active, isLoading, degradedReason, setActive };
}
