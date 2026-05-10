"use client";

import { SectionError } from "@/components/section-states";

export default function MembersError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return (
    <SectionError
      title="Members"
      reset={reset}
      error={error}
      description="Workspace membership and role evidence could not load. Retry or sign back in if the session expired."
    />
  );
}
