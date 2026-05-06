"use client";

/**
 * S151/S153: ``/agents`` segment layout gates the route behind auth.
 *
 * The root layout owns the canonical Studio shell so every section gets
 * the same navigation, preview rail, timeline, and status footer.
 */

import { RequireAuth } from "@/components/auth/require-auth";
import type { ReactNode } from "react";

export default function AgentsLayout({ children }: { children: ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}
