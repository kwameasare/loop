import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  EMPTY_COMMITMENT_BODY,
  buildLocalCommitmentDocument,
} from "@/lib/agent-commitment";

import AgentContractPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentContractPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("loads current Commitment Document and version history from cp-api", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const body = {
      ...EMPTY_COMMITMENT_BODY,
      business_responsibility: "Resolve billing support safely.",
      target_users: "Enterprise customers.",
      owner_user_id: "owner@acme.test",
      worst_case_failure: "Refunds outside policy.",
      channels: ["web"],
      systems_touched: ["billing"],
      regions: ["us-east-1"],
      languages: ["en"],
    };
    const current = {
      ...buildLocalCommitmentDocument("agent_contract", body),
      id: "commit_current",
      version: 2,
      workspace_id: "ws_1",
      status: "draft",
      content_hash: "hash_current_contract",
      created_from: "test:contract",
    };
    const accepted = {
      ...current,
      id: "commit_previous",
      version: 1,
      status: "accepted",
      accepted_at: "2026-05-08T12:00:00Z",
      content_hash: "hash_previous_contract",
    };
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/agents/agent_contract/commitment/current")) {
        return Response.json(current);
      }
      if (url.endsWith("/agents/agent_contract/commitments")) {
        return Response.json({ items: [accepted, current] });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      await AgentContractPage({
        params: { agent_id: "agent_contract" },
        searchParams: { commitment_id: "commit_previous" },
      }),
    );

    expect(screen.getByTestId("contract-version")).toHaveTextContent("v2");
    expect(screen.getByTestId("contract-version-history")).toHaveTextContent(
      "2 versions",
    );
    expect(
      screen.getByTestId("contract-history-commit_previous"),
    ).toHaveAttribute("data-focused", "true");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_contract/commitments",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("shows unavailable commitment state instead of a local saved draft when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(
      await AgentContractPage({
        params: { agent_id: "agent_contract" },
      }),
    );

    expect(screen.getByTestId("contract-degraded")).toHaveTextContent(
      "LOOP_CP_API_BASE_URL",
    );
    expect(screen.getByTestId("contract-status")).toHaveTextContent(
      "unavailable",
    );
    expect(screen.getByTestId("contract-version")).toHaveTextContent(
      "Not loaded",
    );
    expect(screen.getByTestId("contract-version-history")).toHaveTextContent(
      "0 versions",
    );
  });
});
