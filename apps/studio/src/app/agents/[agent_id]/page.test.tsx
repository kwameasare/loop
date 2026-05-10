import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { buildLocalCommitmentDocument } from "@/lib/agent-commitment";
import { buildLocalChannelBindings } from "@/lib/channel-bindings";
import { localMemoryPolicies } from "@/lib/memory-policies";
import { localToolContracts } from "@/lib/tool-contracts";

import AgentOverviewPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentOverviewPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("marks last deploy unavailable when deployment history cannot load", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(await AgentOverviewPage({ params: { agent_id: "agent_support" } }));

    expect(screen.getByTestId("agent-workbench-degraded")).toHaveTextContent(
      "deployment history",
    );
    expect(screen.getByTestId("overview-deploy-time")).toHaveTextContent(
      "Unavailable",
    );
    expect(
      screen.getByTestId("overview-deploy-unavailable"),
    ).toHaveTextContent("LOOP_CP_API_BASE_URL");
    expect(screen.queryByTestId("overview-deploy-version")).toBeNull();
  });

  it("uses deployment history as the last-deploy source of truth", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/agents/agent_live/deployments")) {
        return Response.json({
          items: [
            {
              id: "dep_old",
              agentId: "agent_live",
              versionId: "ver_4",
              status: "live",
              trafficPercent: 100,
              createdAt: "2026-05-07T10:00:00Z",
              promotedAt: "2026-05-07T11:00:00Z",
              pausedAt: null,
              rolledBackAt: null,
              notes: null,
            },
            {
              id: "dep_new",
              agentId: "agent_live",
              versionId: "ver_12",
              status: "canary",
              trafficPercent: 25,
              createdAt: "2026-05-09T10:00:00Z",
              promotedAt: null,
              pausedAt: null,
              rolledBackAt: null,
              notes: "latest canary",
            },
          ],
        });
      }
      if (url.endsWith("/agents/agent_live/commitment/current")) {
        return Response.json(buildLocalCommitmentDocument("agent_live"));
      }
      if (url.endsWith("/agents/agent_live/channel-bindings")) {
        return Response.json({
          items: buildLocalChannelBindings("agent_live").map((binding) =>
            binding.channel_type === "whatsapp"
              ? {
                  ...binding,
                  status: "ready",
                  readiness: binding.readiness.map((check) => ({
                    ...check,
                    status: "passed",
                    evidence_ref: `channel/${binding.id}/${check.id}`,
                  })),
                }
              : binding,
          ),
        });
      }
      if (url.endsWith("/agents/agent_live/tool-contracts")) {
        return Response.json({
          items: localToolContracts("agent_live", [
            "lookup_order",
            "refund_payment",
          ]),
        });
      }
      if (url.endsWith("/agents/agent_live/memory-policies")) {
        return Response.json({
          items: localMemoryPolicies("agent_live").map((policy) =>
            policy.scope === "workspace"
              ? { ...policy, approval_status: "approved" }
              : policy,
          ),
        });
      }
      if (url.endsWith("/evals/suites")) {
        return Response.json({
          items: [
            {
              id: "suite_live",
              name: "Live support suite",
              agentId: "agent_live",
              cases: 18,
              lastRunAt: "2026-05-09T12:00:00Z",
              passRate: 0.97,
            },
          ],
        });
      }
      if (url.endsWith("/agents/agent_live")) {
        return Response.json({
          id: "agent_live",
          name: "Live Support",
          description: "Handles live support.",
          slug: "live-support",
          active_version: 4,
          created_at: "2026-05-01T09:00:00Z",
          workspace_id: "ws_1",
        });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(await AgentOverviewPage({ params: { agent_id: "agent_live" } }));

    expect(screen.getByTestId("overview-deploy-version")).toHaveTextContent(
      "v12",
    );
    expect(screen.getByTestId("overview-deploy-status")).toHaveTextContent(
      "canary",
    );
    expect(screen.getByTestId("agent-outline-channels")).toHaveTextContent(
      "1/9 channel binding ready",
    );
    expect(screen.getByTestId("agent-outline-tools")).toHaveTextContent(
      "2 tool contracts loaded",
    );
    expect(screen.getByTestId("agent-outline-memory")).toHaveTextContent(
      "3 memory policies loaded",
    );
    expect(screen.getByTestId("agent-outline-evals")).toHaveTextContent(
      "Live support suite at 97%",
    );
    expect(screen.queryByTestId("overview-deploy-unavailable")).toBeNull();
  });
});
