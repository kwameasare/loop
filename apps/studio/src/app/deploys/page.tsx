import type { Metadata } from "next";

import { FlightDeckScreen } from "@/components/deploy";

export const dynamic = "force-static";

export const metadata: Metadata = {
  title: "Deployment Flight Deck · Loop Studio",
  description:
    "Environment-specific config, six-dimension preflight diffs, eval gates, approvals, canary slider, auto-rollback, and audited rollback.",
};

export default function DeploysPage() {
  return <FlightDeckScreen />;
}
