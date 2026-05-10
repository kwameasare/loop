import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import AgentMemoryPage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-user", () => ({
  useUser: () => ({
    user: { sub: "alice", email: "alice@example.test" },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("AgentMemoryPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("renders Memory Studio degraded instead of a route-level error when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(
      <AgentMemoryPage
        params={{ agent_id: "agent_memory" }}
        searchParams={{ policy_id: "mp_local_user" }}
      />,
    );

    expect(await screen.findByTestId("memory-studio")).toBeInTheDocument();
    expect(screen.getByText("Memory data is empty")).toBeInTheDocument();
    expect(screen.getAllByText(/LOOP_CP_API_BASE_URL/i).length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText("Acme Support Concierge")).not.toBeInTheDocument();
  });
});
