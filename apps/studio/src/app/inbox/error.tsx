"use client";

import { SectionError } from "@/components/section-states";

export default function InboxError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Inbox" reset={reset} error={error} />;
}
