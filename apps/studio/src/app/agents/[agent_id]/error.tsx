"use client";

import { SectionError } from "@/components/section-states";

export default function AgentDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Agent" reset={reset} error={error} />;
}
