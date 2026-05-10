import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import AgentConductorPage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentConductorPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("renders conductor degraded evidence when the cp-api route is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      <AgentConductorPage params={{ agent_id: "agent_conductor" }} />,
    );

    expect(await screen.findByTestId("conductor-studio")).toBeInTheDocument();
    expect(screen.getByText("Conductor data degraded")).toBeInTheDocument();
    expect(screen.getAllByText(/conductor route returned 404/i).length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText("Refund Specialist")).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_conductor/conductor",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("renders conductor degraded evidence instead of a raw route error when cp-api is unconfigured", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(
      <AgentConductorPage params={{ agent_id: "agent_conductor" }} />,
    );

    expect(await screen.findByTestId("conductor-studio")).toBeInTheDocument();
    expect(screen.getByText("Conductor data degraded")).toBeInTheDocument();
    expect(screen.getAllByText(/LOOP_CP_API_BASE_URL/i).length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
