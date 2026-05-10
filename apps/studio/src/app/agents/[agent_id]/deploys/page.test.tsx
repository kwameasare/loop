import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import AgentDeploysPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentDeploysPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
  });

  it("passes evidence panel query state into deploy surfaces", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(
      await AgentDeploysPage({
        params: { agent_id: "agent_deploy" },
        searchParams: { panel: "release-candidate" },
      }),
    );

    expect(screen.getByTestId("change-package-focused-panel")).toHaveTextContent(
      "release candidate evidence is highlighted",
    );
    expect(
      screen.getByTestId("change-package-release-candidate-card"),
    ).toHaveAttribute("data-focused", "true");
  });

  it("focuses promotion controls from Workbench deploy links", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(
      await AgentDeploysPage({
        params: { agent_id: "agent_deploy" },
        searchParams: { panel: "promotion" },
      }),
    );

    expect(
      screen.getByTestId("change-package-focused-workbench-panel"),
    ).toHaveTextContent("review the Change Package before starting promotion");
    expect(screen.getByTestId("deploy-focused-panel")).toHaveTextContent(
      "promotion controls are highlighted",
    );
    expect(screen.getByTestId("rollout-plan-controls")).toHaveAttribute(
      "data-focused",
      "true",
    );
  });
});
