"use client";

import { SectionError } from "@/components/section-states";

export default function CostsError({ reset }: { reset: () => void }) {
  return <SectionError title="Costs" reset={reset} />;
}
