"use client";

import { SectionError } from "@/components/section-states";

export default function EvalsError({ reset }: { reset: () => void }) {
  return <SectionError title="Evals" reset={reset} />;
}
