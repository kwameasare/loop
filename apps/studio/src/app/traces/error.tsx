"use client";

import { SectionError } from "@/components/section-states";

export default function TracesError({ reset }: { reset: () => void }) {
  return <SectionError title="Traces" reset={reset} />;
}
