"use client";

import { SectionError } from "@/components/section-states";

export default function EnterpriseError({ reset }: { reset: () => void }) {
  return <SectionError title="Enterprise" reset={reset} />;
}
