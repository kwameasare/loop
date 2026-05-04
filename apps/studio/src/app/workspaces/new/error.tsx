"use client";

import { SectionError } from "@/components/section-states";

export default function NewWorkspaceError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Create workspace" reset={reset} error={error} />;
}
