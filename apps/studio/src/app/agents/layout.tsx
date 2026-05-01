"use client";

/**
 * S151: ``/agents`` segment layout — gates the route behind auth.
 *
 * Wrapping the segment in a client layout means every leaf below
 * ``/agents`` inherits the guard without each page repeating the
 * boilerplate. The leaf pages stay as server components for data
 * fetching; the layout only adds the client-side auth check.
 */

import { RequireAuth } from "@/components/auth/require-auth";
import type { ReactNode } from "react";

export default function AgentsLayout({ children }: { children: ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}
