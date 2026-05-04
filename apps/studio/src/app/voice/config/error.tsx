"use client";

import { SectionError } from "@/components/section-states";

export default function VoiceConfigError({
  error,
  reset,
}: {
  error: Error & { digest?: string; request_id?: string; requestId?: string };
  reset: () => void;
}) {
  return (
    <SectionError
      title="Voice channel configuration"
      reset={reset}
      error={error}
    />
  );
}
