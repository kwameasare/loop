import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import MigrationParityPage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_migrate", name: "Migration Workspace" },
    isLoading: false,
  }),
}));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("migration_id=mig_missing"),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("MigrationParityPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
  });

  it("shows degraded parity evidence instead of a local destructive alert when cp-api is unavailable", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;

    render(<MigrationParityPage />);

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Migration Parity is degraded/i);
      expect(state).toHaveTextContent(/cutover evidence could not load/i);
      expect(state).toHaveTextContent(/LOOP_CP_API_BASE_URL is required/i);
    });
    expect(screen.queryByTestId("parity-harness")).not.toBeInTheDocument();
  });
});
