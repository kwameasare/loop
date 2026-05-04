"use client";

import { SectionError } from "@/components/section-states";

export default function WorkspaceEnterpriseError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Enterprise SSO" reset={reset} error={error} />;
}
