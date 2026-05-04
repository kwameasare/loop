"use client";

import { SectionError } from "@/components/section-states";

export default function VoiceConfigError({ reset }: { reset: () => void }) {
  return <SectionError title="Voice channel configuration" reset={reset} />;
}
