"use client";

import { SectionError } from "@/components/section-states";

export default function TracesError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Traces" reset={reset} error={error} />;
}
