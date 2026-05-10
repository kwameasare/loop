import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import AgentsPage from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;
const ORIGINAL_WORKSPACE = process.env.LOOP_DEFAULT_WORKSPACE_ID;

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = value;
  }
}

describe("AgentsPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
  });

  it("keeps workspace and agent registry load failures visible", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";
    process.env.LOOP_DEFAULT_WORKSPACE_ID = "";

    render(await AgentsPage());

    expect(screen.getByTestId("agents-workspace-degraded")).toHaveTextContent(
      "control-plane workspace endpoint",
    );
    expect(screen.getByTestId("agents-degraded")).toHaveTextContent(
      "LOOP_CP_API_BASE_URL is required to list agents",
    );
  });
});
