"use client";

import { SectionError } from "@/components/section-states";

export default function BillingError({ reset }: { reset: () => void }) {
  return <SectionError title="Billing" reset={reset} />;
}
