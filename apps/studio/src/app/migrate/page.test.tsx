import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import MigratePage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_migrate", name: "Migration Workspace" },
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("MigratePage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
  });

  it("shows degraded migration evidence while preserving the import surface when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(<MigratePage />);

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Migration Atelier is degraded/i);
      expect(state).toHaveTextContent(/parity evidence could not load/i);
      expect(state).toHaveTextContent(/LOOP_CP_API_BASE_URL is required/i);
    });
    expect(screen.getByTestId("migration-screen")).toBeInTheDocument();
    expect(
      screen.getByText(/No migration evidence loaded/i),
    ).toBeInTheDocument();
  });
});
