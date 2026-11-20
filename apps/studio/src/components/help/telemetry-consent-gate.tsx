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
      className="pointer-events-none fixed bottom-4 right-4 z-40 w-[min(22rem,calc(100vw-2rem))]"
      data-testid="telemetry-consent-gate"
      aria-live="polite"
    >
      <div className="pointer-events-auto transition-transform duration-gentle ease-standard max-md:translate-y-[calc(100%-4.25rem)] max-md:focus-within:translate-y-0 max-md:hover:translate-y-0">
        <TelemetryConsentCard />
      </div>
    </div>
  );
}
