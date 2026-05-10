import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type PersonaSet = "first-user" | "support-risk" | "accessibility";

export interface PersonaSimulationItem {
  persona: string;
  scenarios: number;
  pass_rate: number;
  failed_scenarios: number;
  candidate_eval_id: string;
  evidence_ref: string;
}

export interface PersonaSimulationResponse {
  persona_set: string;
  items: PersonaSimulationItem[];
}

export interface PersonaEvalCaseResponse {
  ok: true;
  suite_id: string;
  case_id: string;
  case: {
    id: string;
    name: string;
    source: string;
    source_ref: string;
  };
  next_url: string;
}

export const PERSONA_SET_LABELS: Record<PersonaSet, string> = {
  "first-user": "First user",
  "support-risk": "Support risk",
  accessibility: "Accessibility",
};

type PersonaSimulatorClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

export async function runPersonaSimulation(
  agentId: string,
  personaSet: PersonaSet,
  opts: PersonaSimulatorClientOptions = {},
): Promise<PersonaSimulationResponse> {
  return cpJson<PersonaSimulationResponse>(
    `/agents/${encodeURIComponent(agentId)}/persona-test`,
    {
      ...opts,
      method: "POST",
      body: { persona_set: personaSet },
      allowFallback: opts.allowFixture === true,
      fallback: {
        persona_set: personaSet,
        items: [
          {
            persona: "journalist",
            scenarios: 10,
            pass_rate: 0.9,
            failed_scenarios: 1,
            candidate_eval_id: "eval.persona.journalist.policy_provenance",
            evidence_ref: `persona-test/${agentId}/journalist`,
          },
          {
            persona: "english-as-second-language",
            scenarios: 10,
            pass_rate: 0.84,
            failed_scenarios: 2,
            candidate_eval_id: "eval.persona.esl.refund_paraphrase",
            evidence_ref: `persona-test/${agentId}/esl`,
          },
          {
            persona: "adversary",
            scenarios: 10,
            pass_rate: 0.96,
            failed_scenarios: 0,
            candidate_eval_id: "eval.persona.adversary.refund_limits",
            evidence_ref: `persona-test/${agentId}/adversary`,
          },
          {
            persona: "accessibility-tool-user",
            scenarios: 10,
            pass_rate: 0.92,
            failed_scenarios: 1,
            candidate_eval_id: "eval.persona.accessibility.turn_recap",
            evidence_ref: `persona-test/${agentId}/accessibility`,
          },
          {
            persona: "angry-repeat-customer",
            scenarios: 10,
            pass_rate: 0.88,
            failed_scenarios: 2,
            candidate_eval_id: "eval.persona.angry_repeat.empathy_handoff",
            evidence_ref: `persona-test/${agentId}/angry-repeat`,
          },
        ],
      },
    },
  );
}

export async function savePersonaFailureAsEvalCase(
  agentId: string,
  input: {
    personaSet: PersonaSet | string;
    item: PersonaSimulationItem;
    expectedBehavior: string;
    riskTags?: readonly string[];
  },
  opts: PersonaSimulatorClientOptions = {},
): Promise<PersonaEvalCaseResponse> {
  return cpJson<PersonaEvalCaseResponse>(
    `/agents/${encodeURIComponent(agentId)}/persona-test/eval-cases`,
    {
      ...opts,
      method: "POST",
      body: {
        persona_set: input.personaSet,
        persona: input.item.persona,
        candidate_eval_id: input.item.candidate_eval_id,
        evidence_ref: input.item.evidence_ref,
        scenarios: input.item.scenarios,
        failed_scenarios: input.item.failed_scenarios,
        pass_rate: input.item.pass_rate,
        expected_behavior: input.expectedBehavior,
        risk_tags: input.riskTags ?? ["persona-test", input.item.persona],
      },
      allowFallback: false,
      fallback: {
        ok: true,
        suite_id: "",
        case_id: "",
        case: {
          id: "",
          name: `${input.item.persona} persona failure`,
          source: "persona-test",
          source_ref: input.item.evidence_ref,
        },
        next_url: "",
      },
    },
  );
}
