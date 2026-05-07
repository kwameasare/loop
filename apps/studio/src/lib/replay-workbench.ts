import { targetUxFixtures } from "@/lib/target-ux";

export type ReplayRisk = "low" | "medium" | "high";

export interface ProductionConversationCandidate {
  id: string;
  title: string;
  agentName: string;
  sourceVersion: string;
  draftVersion: string;
  snapshotId: string;
  traceId: string;
  turns: number;
  risk: ReplayRisk;
  issue: string;
}

export interface FutureReplayDiff {
  id: string;
  frame: string;
  baseline: string;
  draft: string;
  status: "same" | "changed" | "improved" | "regressed";
  evidenceRef: string;
}

export interface FutureReplaySummary {
  conversationId: string;
  behavioralDistance: number;
  changedFrames: number;
  latencyDeltaMs: number;
  costDeltaPct: number;
  mostLikelyBreak: string;
  diffRows: readonly FutureReplayDiff[];
}

export interface PersonaSimulationResult {
  id: string;
  persona: string;
  lens: string;
  scenarios: number;
  passRate: number;
  failedScenarios: number;
  candidateEvalId: string;
  insight: string;
}

export interface ConversationPropertyResult {
  id: string;
  axis: string;
  samples: number;
  robustness: number;
  failures: number;
  representativeFailure: string;
  nextAction: string;
}

export interface ReplayFailureCluster {
  id: string;
  label: string;
  count: number;
  severity: ReplayRisk;
  nextAction: string;
  evidenceRef: string;
}

export interface CanonicalScene {
  id: string;
  name: string;
  source: "production" | "synthetic" | "migration";
  turns: number;
  evalLinked: boolean;
  summary: string;
  provenance: string;
  linkedTraceId: string;
}

export interface ReplayWorkbenchModel {
  conversations: readonly ProductionConversationCandidate[];
  selectedReplay: FutureReplaySummary;
  personas: readonly PersonaSimulationResult[];
  properties: readonly ConversationPropertyResult[];
  clusters: readonly ReplayFailureCluster[];
  scenes: readonly CanonicalScene[];
}

const conversations: readonly ProductionConversationCandidate[] = [
  {
    id: "prod_refund_legal",
    title: "Cancellation with legal threat",
    agentName: "Acme Support Concierge",
    sourceVersion: "v23.1.4",
    draftVersion: "draft/refund-clarity",
    snapshotId: "snap_refund_may",
    traceId: "trace_refund_742",
    turns: 9,
    risk: "high",
    issue: "Policy citation and escalation changed under the draft.",
  },
  {
    id: "prod_spanish_refund",
    title: "Spanish refund paraphrase",
    agentName: "Acme Support Concierge",
    sourceVersion: "v23.1.4",
    draftVersion: "draft/refund-clarity",
    snapshotId: "snap_refund_may",
    traceId: "trace_refund_es",
    turns: 6,
    risk: "medium",
    issue: "Localized refusal copy may lose citation precision.",
  },
  {
    id: "prod_angry_repeat",
    title: "Angry repeat customer asks for manager",
    agentName: "Acme Support Concierge",
    sourceVersion: "v23.1.4",
    draftVersion: "draft/refund-clarity",
    snapshotId: "snap_refund_may",
    traceId: "trace_repeat_204",
    turns: 11,
    risk: "medium",
    issue: "Draft resolves faster but may skip empathy requirement.",
  },
];

const selectedReplay: FutureReplaySummary = {
  conversationId: "prod_refund_legal",
  behavioralDistance: 34,
  changedFrames: 4,
  latencyDeltaMs: -180,
  costDeltaPct: -7,
  mostLikelyBreak:
    "The draft can answer before the legal-escalation rule fires if the user says attorney instead of legal review.",
  diffRows: [
    {
      id: "frame_1",
      frame: "turn 2 / retrieval",
      baseline: "refund_policy_2026.pdf ranked first with legal escalation note.",
      draft: "refund_policy_2026.pdf remains first; metadata filter adds region=US.",
      status: "improved",
      evidenceRef: "trace_refund_742/retrieval/frame-2",
    },
    {
      id: "frame_2",
      frame: "turn 3 / tool",
      baseline: "lookup_order called before escalation decision.",
      draft: "lookup_order and entitlement lookup are batched.",
      status: "improved",
      evidenceRef: "trace_refund_742/tools/frame-3",
    },
    {
      id: "frame_3",
      frame: "turn 4 / policy",
      baseline: "Legal threat triggers handoff before refund promise.",
      draft: "Attorney paraphrase misses the handoff rule.",
      status: "regressed",
      evidenceRef: "trace_refund_742/policy/frame-4",
    },
    {
      id: "frame_4",
      frame: "turn 5 / answer",
      baseline: "Answer cites policy and creates handoff ticket.",
      draft: "Answer cites policy but leaves handoff as optional.",
      status: "changed",
      evidenceRef: "trace_refund_742/answer/frame-5",
    },
  ],
};

const personas: readonly PersonaSimulationResult[] = [
  {
    id: "persona_journalist",
    persona: "Journalist",
    lens: "Asks for quotable policy language and provenance.",
    scenarios: 10,
    passRate: 90,
    failedScenarios: 1,
    candidateEvalId: "eval.persona.journalist.policy_provenance",
    insight: "Strong citations, one answer exposed internal policy phrasing.",
  },
  {
    id: "persona_esl",
    persona: "English-as-second-language user",
    lens: "Short sentences, paraphrases, language switches.",
    scenarios: 10,
    passRate: 84,
    failedScenarios: 2,
    candidateEvalId: "eval.persona.esl.refund_paraphrase",
    insight: "Spanish paraphrase drops legal escalation coverage.",
  },
  {
    id: "persona_adversary",
    persona: "Adversarial customer",
    lens: "Pressure, prompt injection, unsafe refund requests.",
    scenarios: 10,
    passRate: 96,
    failedScenarios: 0,
    candidateEvalId: "eval.persona.adversary.refund_limits",
    insight: "Tool caps and refusal rules held under pressure.",
  },
  {
    id: "persona_accessibility",
    persona: "Screen-reader user",
    lens: "Verbose clarification, repeated context, slow pacing.",
    scenarios: 10,
    passRate: 92,
    failedScenarios: 1,
    candidateEvalId: "eval.persona.accessibility.turn_recap",
    insight: "Needs a shorter recap before asking for order details.",
  },
  {
    id: "persona_angry_repeat",
    persona: "Angry repeat customer",
    lens: "Escalation pressure and prior bad support history.",
    scenarios: 10,
    passRate: 88,
    failedScenarios: 2,
    candidateEvalId: "eval.persona.angry_repeat.empathy_handoff",
    insight: "Draft is faster but loses one empathy acknowledgement.",
  },
];

const properties: readonly ConversationPropertyResult[] = [
  {
    id: "prop_typos",
    axis: "Typos and missing punctuation",
    samples: 100,
    robustness: 96,
    failures: 3,
    representativeFailure: "cnacel my renewal pls legal will hear",
    nextAction: "Add attorney/legal synonyms to the escalation classifier eval.",
  },
  {
    id: "prop_language",
    axis: "Language switch mid-turn",
    samples: 100,
    robustness: 82,
    failures: 14,
    representativeFailure: "I want cancelar, mi abogado asked for policy.",
    nextAction: "Generate bilingual handoff cases from the failing cluster.",
  },
  {
    id: "prop_context",
    axis: "Missing order context",
    samples: 100,
    robustness: 91,
    failures: 7,
    representativeFailure: "Need refund, annual plan, no order number.",
    nextAction: "Keep lookup_order disabled until the order number is present.",
  },
];

const clusters: readonly ReplayFailureCluster[] = [
  {
    id: "cluster_legal_synonyms",
    label: "Legal synonym misses",
    count: 17,
    severity: "high",
    nextAction: "Promote attorney, counsel, chargeback, and regulator phrases into the escalation rule.",
    evidenceRef: "cluster/legal-synonyms/17-traces",
  },
  {
    id: "cluster_empathy",
    label: "Empathy acknowledgement skipped",
    count: 9,
    severity: "medium",
    nextAction: "Keep the short apology sentence when refund refusal confidence is medium.",
    evidenceRef: "cluster/empathy/9-traces",
  },
  {
    id: "cluster_metadata",
    label: "Region metadata absent",
    count: 6,
    severity: "medium",
    nextAction: "Backfill region metadata for renewal-policy chunks and regenerate retrieval evals.",
    evidenceRef: "cluster/metadata/6-traces",
  },
];

const scenes: readonly CanonicalScene[] = targetUxFixtures.scenes.map((scene) => ({
  id: scene.id,
  name: scene.name,
  source: scene.source,
  turns: scene.turns,
  evalLinked: scene.evalLinked,
  summary: scene.summary,
  provenance: "Saved from production trace trace_refund_742 and signed snapshot snap_refund_may.",
  linkedTraceId: "trace_refund_742",
}));

export function getReplayWorkbenchModel(): ReplayWorkbenchModel {
  return {
    conversations,
    selectedReplay,
    personas,
    properties,
    clusters,
    scenes,
  };
}
