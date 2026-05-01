"use client";

/**
 * S154: ``useActiveWorkspace`` — read & set the active workspace.
 *
 * Source of truth (in priority order):
 *   1. ``?ws=<slug>`` on the current URL.
 *   2. ``localStorage["loop:active-workspace"]`` for cross-tab persistence.
 *   3. The first entry returned by ``listWorkspaces()``.
 *
 * Updates flow back through the router so the URL stays in sync with
 * the dropdown selection — this also gives us deep-link support for
 * sharing workspace-scoped URLs.
 */

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  listWorkspaces,
  type Workspace,
} from "@/lib/workspaces";

const STORAGE_KEY = "loop:active-workspace";

export interface UseActiveWorkspaceResult {
  workspaces: Workspace[];
  active: Workspace | null;
  isLoading: boolean;
  setActive: (workspace: Workspace) => void;
}

export function useActiveWorkspace(): UseActiveWorkspaceResult {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void listWorkspaces().then((res) => {
      if (cancelled) return;
      setWorkspaces(res.workspaces);
      setIsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const urlSlug = params.get("ws");
  const stored =
    typeof window !== "undefined"
      ? window.localStorage.getItem(STORAGE_KEY)
      : null;
  const targetSlug = urlSlug || stored;
  const active =
    workspaces.find((w) => w.slug === targetSlug) || workspaces[0] || null;

  const setActive = useCallback(
    (workspace: Workspace) => {
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, workspace.slug);
      }
      const next = new URLSearchParams(params.toString());
      next.set("ws", workspace.slug);
      router.replace(`${pathname}?${next.toString()}`);
    },
    [params, pathname, router],
  );

  return { workspaces, active, isLoading, setActive };
}
