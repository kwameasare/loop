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

export interface QueuedSpeechPreview {
  text: string;
  textReadyMs: number;
  ttsStartMs: number;
  llmSpanId: string;
  cancellable: boolean;
}

export interface VoiceStageModel {
  agentName: string;
  callState: "dev" | "staging" | "production";
  queuedSpeech: string;
  queuedSpeechPreview?: QueuedSpeechPreview;
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

export interface VoiceStageClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

export interface VoiceNumberProvisionResult {
  id: string;
  phone_number: string;
  provider: string;
  provisioner?: string;
  country: string;
  status: string;
  sip_route: string;
  compliance: readonly { id: string; status: string }[];
}

function cpApiBaseUrl(override?: string): string | null {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function headers(opts: VoiceStageClientOptions): Record<string, string> {
  const out: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) out.authorization = `Bearer ${token}`;
  return out;
}

export async function fetchVoiceStageModel(
  workspaceId: string,
  opts: VoiceStageClientOptions = {},
): Promise<VoiceStageModel> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    return {
      ...VOICE_STAGE_FIXTURE,
      config: {
        ...VOICE_STAGE_FIXTURE.config,
        phoneNumber: "No number provisioned",
      },
    };
  }
  const response = await (opts.fetcher ?? fetch)(
    `${base}/workspaces/${encodeURIComponent(workspaceId)}/voice/stage`,
    {
      method: "GET",
      headers: headers(opts),
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(`cp-api GET voice stage -> ${response.status}`);
  }
  return (await response.json()) as VoiceStageModel;
}

export async function provisionVoiceNumber(
  workspaceId: string,
  opts: VoiceStageClientOptions & {
    country?: string;
    areaCode?: string;
    provider?: string;
  } = {},
): Promise<VoiceNumberProvisionResult> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    return {
      id: "num_local",
      phone_number: "+14155550100",
      provider: opts.provider ?? "twilio",
      provisioner: "deterministic",
      country: opts.country ?? "US",
      status: "provisioned",
      sip_route: `livekit://workspace/${workspaceId}/voice/local`,
      compliance: [
        { id: "business_profile", status: "ready" },
        { id: "10dlc_registration", status: "pending" },
        { id: "livekit_sip_trunk", status: "ready" },
      ],
    };
  }
  const response = await (opts.fetcher ?? fetch)(
    `${base}/workspaces/${encodeURIComponent(workspaceId)}/voice/numbers/provision`,
    {
      method: "POST",
      headers: {
        ...headers(opts),
        "content-type": "application/json",
      },
      body: JSON.stringify({
        country: opts.country ?? "US",
        area_code: opts.areaCode ?? "415",
        capability: "voice",
        provider: opts.provider ?? "twilio",
      }),
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(`cp-api voice provision -> ${response.status}`);
  }
  return (await response.json()) as VoiceNumberProvisionResult;
}

export const VOICE_STAGE_FIXTURE: VoiceStageModel = {
  agentName: "Voice Receptionist",
  callState: "staging",
  queuedSpeech:
    "I can help with that. Before I look up the renewal, I need the account email or order number.",
  queuedSpeechPreview: {
    text: "I can help with that. Before I look up the renewal, I need the account email or order number.",
    textReadyMs: 1240,
    ttsStartMs: 1740,
    llmSpanId: "llm",
    cancellable: true,
  },
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

function labelFor<T extends string>(
  entries: readonly { id: T; label: string }[],
  id: T,
): string {
  return entries.find((entry) => entry.id === id)?.label ?? id;
}

export function voiceStageFromConfig(config: VoiceConfig): VoiceStageModel {
  const primaryNumber = config.numbers[0];
  return {
    ...VOICE_STAGE_FIXTURE,
    config: {
      ...VOICE_STAGE_FIXTURE.config,
      asr: labelFor(ASR_PROVIDERS, config.asr_provider),
      tts: labelFor(TTS_PROVIDERS, config.tts_provider),
      phoneNumber: primaryNumber?.e164 ?? "No number provisioned",
    },
    demoLinks: VOICE_STAGE_FIXTURE.demoLinks.map((link) => ({
      ...link,
      audited: config.workspace_id !== "ws-fixture",
    })),
  };
}
import {
  ASR_PROVIDERS,
  TTS_PROVIDERS,
  type VoiceConfig,
} from "@/lib/voice-config";
