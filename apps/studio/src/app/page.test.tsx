import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import HomePage from "./page";

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

describe("HomePage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
    vi.restoreAllMocks();
  });

  it("does not list agents until workspace context is known", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    process.env.NEXT_PUBLIC_LOOP_API_URL = "";
    process.env.LOOP_DEFAULT_WORKSPACE_ID = "";

    render(await HomePage());

    expect(screen.getByTestId("home-context-degraded")).toHaveTextContent(
      "Workspace context is required before listing agents.",
    );
    expect(screen.getByTestId("home-context-degraded")).toHaveTextContent(
      "control-plane workspace endpoint",
    );
  });
});
