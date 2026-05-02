"use client";

import { VoiceConfigPanel } from "@/components/voice/voice-config-panel";
import { FIXTURE_VOICE_CONFIG } from "@/lib/voice-config";

async function fixtureSave() {
  return { ok: true as const };
}

export default function VoiceConfigPage(): JSX.Element {
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Voice channel configuration
        </h1>
        <p className="text-muted-foreground text-sm">
          Connect phone numbers and choose ASR / TTS providers for the
          voice channel.
        </p>
      </header>
      <VoiceConfigPanel config={FIXTURE_VOICE_CONFIG} save={fixtureSave} />
    </main>
  );
}
