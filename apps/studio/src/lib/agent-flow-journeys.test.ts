import { describe, expect, it } from "vitest";

import {
  AGENT_FLOW_JOURNEY_IDS,
  AGENT_FLOW_JOURNEYS,
  findAgentFlowJourneyRouteGaps,
} from "@/lib/agent-flow-journeys";
import { STUDIO_ROUTES } from "@/lib/route-audit";

describe("AGENT_FLOW_JOURNEYS", () => {
  it("captures the five merged implementation flows with testable proofs", () => {
    expect(AGENT_FLOW_JOURNEY_IDS).toEqual([
      "flow-a-create-billing-support-agent",
      "flow-b-migrate-from-botpress",
      "flow-c-fix-production-issue",
      "flow-d-add-high-risk-tool",
      "flow-e-add-voice-after-web-whatsapp",
    ]);

    for (const id of AGENT_FLOW_JOURNEY_IDS) {
      const journey = AGENT_FLOW_JOURNEYS[id];
      expect(journey.steps.length).toBeGreaterThanOrEqual(5);
      expect(journey.routes.length).toBeGreaterThanOrEqual(5);
      expect(journey.proofs.length).toBeGreaterThanOrEqual(5);
      expect(journey.acceptance.length).toBeGreaterThanOrEqual(4);
    }
  });

  it("keeps every merged journey route wired to the Studio IA registry", () => {
    const knownRoutes = new Set(STUDIO_ROUTES.map((entry) => entry.route));
    expect(findAgentFlowJourneyRouteGaps(knownRoutes)).toEqual([]);
  });

  it("makes support-agent lifecycle and Botpress migration explicit gates", () => {
    const support = AGENT_FLOW_JOURNEYS["flow-a-create-billing-support-agent"];
    expect(support.proofs).toEqual(
      expect.arrayContaining([
        "agent.id",
        "commitment_document.id",
        "eval.suite_id",
        "channel_binding.id",
      ]),
    );
    expect(support.routes).toEqual(
      expect.arrayContaining([
        "/agents/[agent_id]/contract",
        "/agents/[agent_id]/tools",
        "/agents/[agent_id]/evals",
        "/agents/[agent_id]/channels",
      ]),
    );

    const botpress = AGENT_FLOW_JOURNEYS["flow-b-migrate-from-botpress"];
    expect(botpress.proofs).toEqual(
      expect.arrayContaining([
        "migration.run_id",
        "parity.report_id",
        "lineage.evidence_ref",
      ]),
    );
    expect(botpress.routes).toEqual(
      expect.arrayContaining(["/migrate", "/migrate/parity"]),
    );
  });
});
