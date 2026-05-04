"use client";

import { SectionError } from "@/components/section-states";

export default function WorkspaceEnterpriseError({
  reset,
}: {
  reset: () => void;
}) {
  return <SectionError title="Enterprise SSO" reset={reset} />;
}
