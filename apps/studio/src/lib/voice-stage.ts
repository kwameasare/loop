export interface VoiceLatencySpan {
  id: string;
  label: string;
  ms: number;
  budgetMs: number;
  status: "ok" | "watch" | "over";
}

export interface VoiceEvalCase {
  id: string;
  name: string;
  passRate: number;
  coverage: string;
  evidenceRef: string;
}

export interface VoiceDemoLink {
  id: string;
  label: string;
  expiresIn: string;
  scope: string;
  audited: boolean;
}

export interface VoiceStageModel {
  agentName: string;
  callState: "dev" | "staging" | "production";
  queuedSpeech: string;
  transcript: readonly {
    id: string;
    speaker: "caller" | "agent" | "tool";
    text: string;
    timestamp: string;
  }[];
  waveform: readonly number[];
  spans: readonly VoiceLatencySpan[];
  config: {
    asr: string;
    tts: string;
    bargeIn: boolean;
    voice: string;
    phoneNumber: string;
  };
  evals: readonly VoiceEvalCase[];
  demoLinks: readonly VoiceDemoLink[];
}

export const VOICE_STAGE_FIXTURE: VoiceStageModel = {
  agentName: "Voice Receptionist",
  callState: "staging",
  queuedSpeech:
    "I can help with that. Before I look up the renewal, I need the account email or order number.",
  transcript: [
    {
      id: "turn_1",
      speaker: "caller",
      text: "I need to cancel my annual renewal, and I am pretty frustrated.",
      timestamp: "00:00.4",
    },
    {
      id: "turn_2",
      speaker: "agent",
      text: "I hear you. I can check the renewal and explain the refund options.",
      timestamp: "00:01.1",
    },
    {
      id: "turn_3",
      speaker: "tool",
      text: "lookup_order waiting for account identifier.",
      timestamp: "00:02.0",
    },
  ],
  waveform: [18, 34, 48, 36, 62, 76, 44, 30, 58, 82, 65, 42, 24, 50, 73, 38],
  spans: [
    { id: "asr", label: "ASR partial", ms: 92, budgetMs: 120, status: "ok" },
    { id: "llm", label: "LLM turn", ms: 410, budgetMs: 520, status: "ok" },
    { id: "tool", label: "Tool wait", ms: 180, budgetMs: 160, status: "watch" },
    { id: "tts", label: "TTS stream", ms: 210, budgetMs: 240, status: "ok" },
  ],
  config: {
    asr: "Deepgram Nova-2",
    tts: "ElevenLabs Turbo v2",
    bargeIn: true,
    voice: "Warm concierge",
    phoneNumber: "+1 800 555 1234",
  },
  evals: [
    {
      id: "voice_interrupt",
      name: "Barge-in interruption keeps state",
      passRate: 96,
      coverage: "Caller interrupts during TTS and changes intent.",
      evidenceRef: "voice-eval/barge-in/state",
    },
    {
      id: "voice_latency",
      name: "P95 under 900 ms before first audio",
      passRate: 94,
      coverage: "ASR, first token, TTS first packet, and channel latency.",
      evidenceRef: "voice-eval/latency/p95",
    },
    {
      id: "voice_handoff",
      name: "Urgent handoff creates operator card",
      passRate: 91,
      coverage: "Legal threat, medical emergency, and VIP escalation variants.",
      evidenceRef: "voice-eval/handoff/operator-card",
    },
  ],
  demoLinks: [
    {
      id: "demo_exec",
      label: "Executive five-minute voice demo",
      expiresIn: "47 minutes",
      scope: "Voice-only, no tools that write",
      audited: true,
    },
    {
      id: "demo_sales",
      label: "Customer preview without Loop branding",
      expiresIn: "2 hours",
      scope: "Whitelabel, rate-limited to 20 turns",
      audited: true,
    },
  ],
};
