"use client";

/**
 * S151/S153: ``/agents`` segment layout — gates the route behind
 * auth and wraps it in the studio app shell (sidebar + topbar).
 *
 * Wrapping the segment in a client layout means every leaf below
 * ``/agents`` inherits the guard plus the shell without each page
 * repeating the boilerplate. Leaf pages stay as server components for
 * data fetching; the layout adds the auth check and chrome.
 */

import { RequireAuth } from "@/components/auth/require-auth";
import { AppShell } from "@/components/shell/app-shell";
import type { ReactNode } from "react";

export default function AgentsLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}
