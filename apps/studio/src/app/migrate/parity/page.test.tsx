import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createFixtureMigrationParityWorkspace } from "@/lib/botpress-import";
import { localMigrationRun } from "@/lib/migration-runs";

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
    vi.unstubAllGlobals();
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

  it("persists accepted repairs before showing accepted state", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const run = { ...localMigrationRun("ws_migrate"), id: "mig_missing" };
    const workspace = {
      ...createFixtureMigrationParityWorkspace(),
      migrationRun: run,
    };
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/migration/parity")) {
        return Response.json(workspace);
      }
      if (
        url.endsWith("/migrations/imports/mig_missing/repairs/rep_2/accept") &&
        init?.method === "POST"
      ) {
        return Response.json({
          ...run,
          inventory: run.inventory.map((item) => ({
            ...item,
            severity: "ok",
            resolved_by_repair_id: "rep_2",
            resolved_at: "2026-05-09T12:00:00Z",
          })),
        });
      }
      return new Response("not found", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<MigrationParityPage />);

    await screen.findByTestId("parity-harness");
    fireEvent.click(screen.getByTestId("repair-accept-rep_2"));

    expect(await screen.findByTestId("repair-accepted-rep_2")).toBeInTheDocument();
    const postCall = fetcher.mock.calls.find(([input, init]) =>
      String(input).endsWith(
        "/migrations/imports/mig_missing/repairs/rep_2/accept",
      ) && init?.method === "POST",
    );
    expect(postCall).toBeDefined();
    const body = JSON.parse(String((postCall?.[1] as RequestInit).body));
    expect(body).toMatchObject({
      repair_id: "rep_2",
      evidence_ref: expect.any(String),
      patch_summary: expect.any(String),
    });
  });
});
