"use client";

import { SectionError } from "@/components/section-states";

export default function VoiceError({ reset }: { reset: () => void }) {
  return <SectionError title="Voice channel" reset={reset} />;
}
