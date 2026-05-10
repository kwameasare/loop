"use client";

import { TelemetryConsentCard } from "@/components/help/telemetry-consent-card";

/**
 * Route-agnostic telemetry consent surface.
 *
 * The card itself returns null once consent is current, so the shell can mount
 * this gate globally without turning the homepage into a recurring consent
 * billboard.
 */
export function TelemetryConsentGate(): JSX.Element {
  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-40 w-[min(34rem,calc(100vw-2rem))]"
      data-testid="telemetry-consent-gate"
      aria-live="polite"
    >
      <div className="pointer-events-auto">
        <TelemetryConsentCard />
      </div>
    </div>
  );
}
