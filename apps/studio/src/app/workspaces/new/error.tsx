"use client";

import { SectionError } from "@/components/section-states";

export default function NewWorkspaceError({ reset }: { reset: () => void }) {
  return <SectionError title="Create workspace" reset={reset} />;
}
