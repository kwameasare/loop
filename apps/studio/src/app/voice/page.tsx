"use client";

import { VoiceWidget } from "@/components/voice/voice-widget";
import { makeFixtureTransport } from "@/lib/voice-transport";

export default function VoicePage(): JSX.Element {
  // The fixture transport never actually opens a microphone; production
  // pages would inject a WebRTC-backed transport instead.
  const transport = makeFixtureTransport();
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Voice channel
        </h1>
        <p className="text-muted-foreground text-sm">
          Embed this widget anywhere in the studio to talk to your agent
          directly in the browser. Push-to-talk and always-on modes are both
          supported.
        </p>
      </header>
      <VoiceWidget agentName="Voice Concierge" transport={transport} />
    </main>
  );
}
