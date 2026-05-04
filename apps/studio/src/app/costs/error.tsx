"use client";

import { SectionError } from "@/components/section-states";

export default function CostsError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Costs" reset={reset} error={error} />;
}
