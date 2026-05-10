"use client";

/**
 * S151/S153: ``/agents`` segment layout gates the route behind auth.
 *
 * Agent-scoped evidence, emulator, and activity surfaces are mounted by
 * agent routes so the global shell never leaks fixture liveness.
 */

import { RequireAuth } from "@/components/auth/require-auth";
import type { ReactNode } from "react";

export default function AgentsLayout({ children }: { children: ReactNode }) {
  return <RequireAuth>{children}</RequireAuth>;
}
