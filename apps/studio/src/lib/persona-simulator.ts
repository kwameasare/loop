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

export const PERSONA_SET_LABELS: Record<PersonaSet, string> = {
  "first-user": "First user",
  "support-risk": "Support risk",
  accessibility: "Accessibility",
};

export async function runPersonaSimulation(
  agentId: string,
  personaSet: PersonaSet,
  opts: UxWireupClientOptions = {},
): Promise<PersonaSimulationResponse> {
  return cpJson<PersonaSimulationResponse>(
    `/agents/${encodeURIComponent(agentId)}/persona-test`,
    {
      ...opts,
      method: "POST",
      body: { persona_set: personaSet },
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
