"use client";

import { RequireAuth } from "@/components/auth/require-auth";
import { VoiceStage } from "@/components/voice/voice-stage";
import { VOICE_STAGE_FIXTURE } from "@/lib/voice-stage";

export default function VoicePage(): JSX.Element {
  return (
    <RequireAuth>
      <VoiceStage model={VOICE_STAGE_FIXTURE} />
    </RequireAuth>
  );
}
