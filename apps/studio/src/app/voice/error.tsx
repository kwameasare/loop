"use client";

import { SectionError } from "@/components/section-states";

export default function VoiceError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return <SectionError title="Voice channel" reset={reset} error={error} />;
}
