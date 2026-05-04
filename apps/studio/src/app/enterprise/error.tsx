"use client";

import { SectionError } from "@/components/section-states";

export default function EnterpriseError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Enterprise" reset={reset} error={error} />;
}
