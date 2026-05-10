import { describe, expect, it } from "vitest";

import {
  agentProductionLabel,
  agentStateLabel,
  agentStateSentence,
} from "./agent-detail-data";
import type { AgentSummary } from "@/lib/cp-api";

const AGENT: AgentSummary = {
  id: "agent_1",
  name: "Refund Concierge",
  description: "Handles refunds.",
  slug: "refund-concierge",
  active_version: 24,
  object_state: "canary",
  state_reason: "Deployment dep_1 is held at 5% because evals are watching.",
  state_evidence_ref: "deployment/dep_1",
  updated_at: "2026-05-09T00:00:00Z",
  workspace_id: "workspace_1",
};

describe("agent detail state helpers", () => {
  it("derives production and state labels from the agent object", () => {
    expect(agentProductionLabel(AGENT)).toBe("v24");
    expect(agentStateLabel(AGENT)).toBe("canary");
    expect(
      agentProductionLabel({
        ...AGENT,
        active_version: null,
      }),
    ).toBe("not live");
  });

  it("builds the one-sentence workbench state from durable fields", () => {
    expect(agentStateSentence(AGENT)).toBe(
      "You are working on agent `Refund Concierge`. Current state is canary. Production is v24. Deployment dep_1 is held at 5% because evals are watching. Evidence: deployment/dep_1.",
    );
  });

  it("does not invent branch or environment state when the backend omits it", () => {
    expect(
      agentStateSentence({
        ...AGENT,
        name: "",
        active_version: null,
        object_state: "draft",
        state_reason: "",
        state_evidence_ref: "",
      }),
    ).toBe(
      "You are working on agent `agent_1`. Current state is draft. Production is not live. No additional state reason is available. No state evidence reference is available.",
    );
  });
});
