import { targetUxFixtures } from "@/lib/target-ux";

export type SimulatorChannel =
  | "web"
  | "slack"
  | "whatsapp"
  | "sms"
  | "email"
  | "voice";

export type SimulatorMemoryMode =
  | "current"
  | "cleared"
  | "snapshot"
  | "read-only";

export type SimulatorModelAlias =
  | "production"
  | "fast-draft"
  | "quality"
  | "budget-safe";

export type SimulatorPersonaId =
  | "standard-user"
  | "angry-customer"
  | "premium-admin"
  | "new-user";

export type SimulatorSeededContextId =
  | "trace_refund_742"
  | "scene_escalation_legal_threat"
  | "blank";

export type SimulatorToolMode = "mock" | "live";

export interface SimulatorConfig {
  channel: SimulatorChannel;
  modelAlias: SimulatorModelAlias;
  memoryMode: SimulatorMemoryMode;
  personaId: SimulatorPersonaId;
  seededContextId: SimulatorSeededContextId;
  disabledTools: string[];
  injectedContext: string;
  replayTurn: number | null;
  diffAgainst: string;
  toolMode: SimulatorToolMode;
}

export interface SimulatorChannelShell {
  id: SimulatorChannel;
  label: string;
  previewLabel: string;
  constraint: string;
  composer: string;
  delivery: string;
}

export interface SimulatorPersona {
  id: SimulatorPersonaId;
  label: string;
  evidence: string;
  prompt: string;
}

export interface SimulatorModelOption {
  id: SimulatorModelAlias;
  label: string;
  impact: string;
}

export interface SimulatorMemoryOption {
  id: SimulatorMemoryMode;
  label: string;
  evidence: string;
}

export interface SimulatorCommandResult {
  ok: boolean;
  message: string;
  nextConfig: SimulatorConfig;
}

export interface SimulatorRunDetail {
  contextLabel: string;
  contextEvidence: string;
  personaLabel: string;
  channelLabel: string;
  modelLabel: string;
  memoryLabel: string;
  modelInput: string;
  modelOutput: string;
  productionOutput: string;
  draftOutput: string;
  traceId: string;
  replayLabel: string;
  costUsd: number;
  latencyMs: number;
  policyFlags: string[];
  unsupported: string[];
  toolCalls: {
    name: string;
    status: "mocked" | "live" | "disabled" | "blocked";
    evidence: string;
  }[];
  retrievedChunks: {
    source: string;
    excerpt: string;
    evidence: string;
  }[];
  memoryEvents: {
    kind: "read" | "write" | "blocked";
    label: string;
    evidence: string;
  }[];
  evalScores: {
    scorer: string;
    score: string;
    evidence: string;
  }[];
  waterfall: {
    label: string;
    durationMs: number;
    evidence: string;
  }[];
  diffRows: {
    label: string;
    production: string;
    draft: string;
    evidence: string;
  }[];
}

export const SIMULATOR_CHANNELS: SimulatorChannelShell[] = [
  {
    id: "web",
    label: "Web",
    previewLabel: "Website widget",
    constraint: "Rich text, links, and inline follow-up buttons.",
    composer: "Customer types in the embedded support widget.",
    delivery: "Delivered as a web chat bubble.",
  },
  {
    id: "slack",
    label: "Slack",
    previewLabel: "Slack thread",
    constraint:
      "Threaded reply, short blocks, and no payment details in channel.",
    composer: "Teammate sends a Slack mention.",
    delivery: "Delivered as a Slack thread reply.",
  },
  {
    id: "whatsapp",
    label: "WhatsApp",
    previewLabel: "WhatsApp chat",
    constraint: "Concise mobile copy with policy links shortened.",
    composer: "Customer sends a WhatsApp message.",
    delivery: "Delivered as a WhatsApp template-safe reply.",
  },
  {
    id: "sms",
    label: "SMS",
    previewLabel: "SMS",
    constraint: "One short message, no markdown, link count minimized.",
    composer: "Customer sends a text message.",
    delivery: "Delivered as a 160 character aware SMS.",
  },
  {
    id: "email",
    label: "Email",
    previewLabel: "Email reply",
    constraint: "Subject, greeting, body, and support-safe signature.",
    composer: "Customer replies to a support email.",
    delivery: "Delivered as an email draft.",
  },
  {
    id: "voice",
    label: "Voice",
    previewLabel: "Voice transcript",
    constraint: "Speech-friendly answer with queued TTS preview.",
    composer: "Caller speaks into the voice channel.",
    delivery: "Delivered as queued speech plus transcript.",
  },
];

export const SIMULATOR_PERSONAS: SimulatorPersona[] = [
  {
    id: "standard-user",
    label: "Standard user",
    evidence: "Production replay cohort: refund_cancel_standard",
    prompt: "I want to cancel my annual renewal before it charges again.",
  },
  {
    id: "angry-customer",
    label: "Angry customer",
    evidence: targetUxFixtures.inbox[0]?.traceId ?? "trace_refund_742",
    prompt: "You charged me again after I cancelled. Fix it now.",
  },
  {
    id: "premium-admin",
    label: "Premium admin",
    evidence: "Injected account tier from ChatOps context",
    prompt:
      "Can you confirm whether my premium workspace can get a renewal refund?",
  },
  {
    id: "new-user",
    label: "New user",
    evidence: "Synthetic persona anchored to scene_escalation_legal_threat",
    prompt:
      "I am new here. How do refunds work if the renewal already happened?",
  },
];

export const SIMULATOR_MODELS: SimulatorModelOption[] = [
  {
    id: "production",
    label: "production",
    impact: "Matches live v23.1.4 routing.",
  },
  {
    id: "fast-draft",
    label: "fast-draft",
    impact: "Lower latency; run refund eval before promotion.",
  },
  {
    id: "quality",
    label: "quality",
    impact: "Higher reasoning budget for policy-heavy turns.",
  },
  {
    id: "budget-safe",
    label: "budget-safe",
    impact: "Cheaper fallback with stricter tool gating.",
  },
];

export const SIMULATOR_MEMORY_MODES: SimulatorMemoryOption[] = [
  {
    id: "current",
    label: "Current memory",
    evidence: "Uses durable memory policy from active workspace.",
  },
  {
    id: "cleared",
    label: "Cleared memory",
    evidence: "Replays without durable user facts.",
  },
  {
    id: "snapshot",
    label: "Snapshot memory",
    evidence: targetUxFixtures.snapshots[0]?.id ?? "snap_refund_may",
  },
  {
    id: "read-only",
    label: "Read-only memory",
    evidence: "Reads facts but blocks new writes.",
  },
];

export const SIMULATOR_COMMANDS = [
  "/swap model=fast-draft",
  "/disable tool=lookup_order",
  '/inject ctx="user is on premium tier"',
  "/as-user persona=angry-customer",
  "/replay turn=3 with-memory=cleared",
  "/diff against=v23",
] as const;

export const DEFAULT_SIMULATOR_CONFIG: SimulatorConfig = {
  channel: "web",
  modelAlias: "production",
  memoryMode: "current",
  personaId: "standard-user",
  seededContextId: "trace_refund_742",
  disabledTools: [],
  injectedContext: "",
  replayTurn: null,
  diffAgainst: "v23",
  toolMode: "mock",
};

function byId<T extends { id: string }>(items: T[], id: string): T {
  return items.find((item) => item.id === id) ?? items[0]!;
}

function toolNames(): string[] {
  return targetUxFixtures.tools.map((tool) => tool.name);
}

function isModelAlias(value: string): value is SimulatorModelAlias {
  return SIMULATOR_MODELS.some((model) => model.id === value);
}

function isPersona(value: string): value is SimulatorPersonaId {
  return SIMULATOR_PERSONAS.some((persona) => persona.id === value);
}

function isMemoryMode(value: string): value is SimulatorMemoryMode {
  return SIMULATOR_MEMORY_MODES.some((mode) => mode.id === value);
}

function withToolDisabled(
  config: SimulatorConfig,
  toolName: string,
): SimulatorConfig {
  if (!toolNames().includes(toolName)) {
    return config;
  }
  if (config.disabledTools.includes(toolName)) return config;
  return {
    ...config,
    disabledTools: [...config.disabledTools, toolName],
  };
}

export function parseSimulatorCommand(
  input: string,
  config: SimulatorConfig,
): SimulatorCommandResult {
  const command = input.trim();
  if (!command.startsWith("/")) {
    return {
      ok: false,
      message: "Enter a slash command or send a simulated turn.",
      nextConfig: config,
    };
  }

  if (command.startsWith("/swap")) {
    const model = command.match(/model=([^\s]+)/)?.[1];
    if (!model || !isModelAlias(model)) {
      return {
        ok: false,
        message: "Unsupported model alias. Try /swap model=fast-draft.",
        nextConfig: config,
      };
    }
    return {
      ok: true,
      message: `Model swapped to ${model}.`,
      nextConfig: { ...config, modelAlias: model },
    };
  }

  if (command.startsWith("/disable")) {
    const tool = command.match(/tool=([^\s]+)/)?.[1];
    if (!tool || !toolNames().includes(tool)) {
      return {
        ok: false,
        message: "Tool is not available in this simulator fixture.",
        nextConfig: config,
      };
    }
    return {
      ok: true,
      message: `${tool} disabled for this run.`,
      nextConfig: withToolDisabled(config, tool),
    };
  }

  if (command.startsWith("/inject")) {
    const context =
      command.match(/ctx="([^"]+)"/)?.[1] ?? command.match(/ctx=([^\s]+)/)?.[1];
    if (!context) {
      return {
        ok: false,
        message: 'Add context with /inject ctx="...".',
        nextConfig: config,
      };
    }
    return {
      ok: true,
      message: "Context injected into the next turn.",
      nextConfig: { ...config, injectedContext: context },
    };
  }

  if (command.startsWith("/as-user")) {
    const persona = command.match(/persona=([^\s]+)/)?.[1];
    if (!persona || !isPersona(persona)) {
      return {
        ok: false,
        message: "Persona is not part of this simulator fixture.",
        nextConfig: config,
      };
    }
    return {
      ok: true,
      message: `Persona switched to ${byId(SIMULATOR_PERSONAS, persona).label}.`,
      nextConfig: { ...config, personaId: persona },
    };
  }

  if (command.startsWith("/replay")) {
    const turn = Number(command.match(/turn=(\d+)/)?.[1] ?? "3");
    const memory = command.match(/with-memory=([^\s]+)/)?.[1];
    const nextMemory =
      memory && isMemoryMode(memory) ? memory : config.memoryMode;
    return {
      ok: true,
      message: `Replay queued from turn ${turn} with ${nextMemory} memory.`,
      nextConfig: { ...config, replayTurn: turn, memoryMode: nextMemory },
    };
  }

  if (command.startsWith("/diff")) {
    const against = command.match(/against=([^\s]+)/)?.[1] ?? "v23";
    return {
      ok: true,
      message: `Diff target set to ${against}.`,
      nextConfig: { ...config, diffAgainst: against },
    };
  }

  return {
    ok: false,
    message: `Unsupported command: ${command.split(" ")[0]}.`,
    nextConfig: config,
  };
}

export function buildSimulatorRun(
  config: SimulatorConfig,
  agentId: string,
): SimulatorRunDetail {
  const channel = byId(SIMULATOR_CHANNELS, config.channel);
  const persona = byId(SIMULATOR_PERSONAS, config.personaId);
  const model = byId(SIMULATOR_MODELS, config.modelAlias);
  const memory = byId(SIMULATOR_MEMORY_MODES, config.memoryMode);
  const trace = targetUxFixtures.traces[0]!;
  const scene = targetUxFixtures.scenes[0]!;
  const snapshot = targetUxFixtures.snapshots[0]!;
  const evalSuite = targetUxFixtures.evals[0]!;
  const memoryFact = targetUxFixtures.memory[0]!;
  const contextLabel =
    config.seededContextId === "blank"
      ? "No seeded context"
      : config.seededContextId === "scene_escalation_legal_threat"
        ? scene.name
        : trace.title;
  const contextEvidence =
    config.seededContextId === "blank"
      ? "No trace or scene context attached to this run."
      : config.seededContextId === "scene_escalation_legal_threat"
        ? `${scene.id}: ${scene.summary}`
        : `${trace.id}: ${trace.spans[0]?.evidence ?? trace.title}`;

  const lookupDisabled = config.disabledTools.includes("lookup_order");
  const refundDisabled = config.disabledTools.includes("issue_refund");
  const replayLabel =
    config.replayTurn === null
      ? "No replay turn queued"
      : `Replaying turn ${config.replayTurn} from ${trace.id}`;
  const injected = config.injectedContext
    ? `\nInjected context: ${config.injectedContext}`
    : "";
  const disabledList =
    config.disabledTools.length > 0 ? config.disabledTools.join(", ") : "none";

  const modelInput = [
    `agent=${agentId}`,
    `channel=${channel.id}`,
    `persona=${persona.label}`,
    `model=${model.id}`,
    `memory=${memory.id}`,
    `tools_disabled=${disabledList}`,
    `seed=${contextLabel}`,
    `user="${persona.prompt}"${injected}`,
  ].join("\n");

  const productionOutput =
    "I can help with the renewal cancellation. I will check the order and cite the current refund policy before suggesting next steps.";
  const draftOutput = lookupDisabled
    ? "I can explain the cancellation policy, but order lookup is disabled in this run, so I cannot verify refund eligibility."
    : refundDisabled
      ? "I found the renewal and can summarize the refund window. Refund issuance is disabled, so I will hand off the money-moving step."
      : "I found the renewal, cited the current policy, and can prepare the next safe refund step for approval.";

  const baseLatency =
    config.modelAlias === "fast-draft"
      ? 760
      : config.modelAlias === "quality"
        ? 1280
        : config.modelAlias === "budget-safe"
          ? 910
          : 1030;
  const latencyMs =
    baseLatency +
    (channel.id === "voice" ? 240 : channel.id === "email" ? 120 : 0);
  const costUsd =
    config.modelAlias === "quality"
      ? 0.061
      : config.modelAlias === "budget-safe"
        ? 0.026
        : config.modelAlias === "fast-draft"
          ? 0.031
          : 0.043;

  const unsupported =
    channel.id === "voice"
      ? [
          "Live microphone capture is not enabled in this lab. Voice uses queued transcript and TTS preview evidence.",
        ]
      : [];

  return {
    contextLabel,
    contextEvidence,
    personaLabel: persona.label,
    channelLabel: channel.label,
    modelLabel: model.label,
    memoryLabel: memory.label,
    modelInput,
    modelOutput: draftOutput,
    productionOutput,
    draftOutput,
    traceId: trace.id,
    replayLabel,
    costUsd,
    latencyMs,
    policyFlags: [
      refundDisabled
        ? "Money-moving tool disabled; handoff required."
        : "Money-moving tool stays gated by approval policy.",
      config.toolMode === "mock"
        ? "Tool calls run in mock mode."
        : "Live tools require workspace permission.",
    ],
    unsupported,
    toolCalls: targetUxFixtures.tools.map((tool) => {
      const disabled = config.disabledTools.includes(tool.name);
      return {
        name: tool.name,
        status: disabled
          ? "disabled"
          : config.toolMode === "live" && tool.authMode === "secret"
            ? "blocked"
            : config.toolMode === "live"
              ? "live"
              : "mocked",
        evidence: disabled
          ? "Disabled by simulator control or /disable command."
          : `${tool.owner}; ${tool.sideEffect}; ${tool.authMode} auth.`,
      };
    }),
    retrievedChunks: [
      {
        source: "refund_policy_2026.pdf",
        excerpt:
          "Annual renewals can be reviewed during the current refund window.",
        evidence: trace.spans[0]?.evidence ?? trace.id,
      },
      {
        source: scene.id,
        excerpt: scene.summary,
        evidence: `Scene source: ${scene.source}; eval linked: ${scene.evalLinked ? "yes" : "no"}.`,
      },
    ],
    memoryEvents:
      config.memoryMode === "cleared"
        ? [
            {
              kind: "blocked",
              label: "Durable memory cleared for replay",
              evidence: "No user facts are read or written in this run.",
            },
          ]
        : config.memoryMode === "read-only"
          ? [
              {
                kind: "read",
                label: `${memoryFact.key}: ${memoryFact.after}`,
                evidence: memoryFact.source,
              },
              {
                kind: "blocked",
                label: "New writes blocked",
                evidence: "Read-only memory mode selected.",
              },
            ]
          : [
              {
                kind: "read",
                label: `${memoryFact.key}: ${memoryFact.after}`,
                evidence: memoryFact.source,
              },
              {
                kind: "write",
                label: "Preference confirmation queued",
                evidence:
                  config.memoryMode === "snapshot"
                    ? snapshot.id
                    : memoryFact.policy,
              },
            ],
    evalScores: [
      {
        scorer: evalSuite.name,
        score: `${evalSuite.passRate}% pass`,
        evidence: `${evalSuite.id}; ${evalSuite.coverage}`,
      },
      {
        scorer: "Channel constraint check",
        score: channel.id === "sms" ? "Needs concise rewrite" : "Pass",
        evidence: channel.constraint,
      },
    ],
    waterfall: [
      { label: "Channel ingress", durationMs: 82, evidence: channel.delivery },
      ...trace.spans.map((span) => ({
        label: span.label,
        durationMs: span.durationMs,
        evidence: span.evidence ?? span.status,
      })),
      {
        label: "Channel delivery",
        durationMs: 96,
        evidence: channel.constraint,
      },
    ],
    diffRows: [
      {
        label: "Model",
        production: "production",
        draft: model.label,
        evidence: model.impact,
      },
      {
        label: "Memory",
        production: "Current memory",
        draft: memory.label,
        evidence: memory.evidence,
      },
      {
        label: "Tools",
        production: "lookup_order and issue_refund available",
        draft:
          config.disabledTools.length > 0
            ? `${config.disabledTools.join(", ")} disabled`
            : "No tools disabled",
        evidence: "Simulator tool allow/deny set.",
      },
      {
        label: "Replay",
        production: trace.version,
        draft: replayLabel,
        evidence: `Diff against ${config.diffAgainst}.`,
      },
    ],
  };
}
