"use client";

import { SectionError } from "@/components/section-states";

export default function BillingError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Billing" reset={reset} error={error} />;
}
