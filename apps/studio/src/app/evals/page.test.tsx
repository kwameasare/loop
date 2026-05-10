import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import EvalsIndexPage, { resolveEvalWorkspaceId } from "./page";

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;
const ORIGINAL_WORKSPACE = process.env.LOOP_DEFAULT_WORKSPACE_ID;
const ORIGINAL_TOKEN = process.env.LOOP_TOKEN;

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("resolveEvalWorkspaceId", () => {
  afterEach(() => {
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
  });

  it("prefers the authorized workspace list and does not invent ids", () => {
    expect(
      resolveEvalWorkspaceId([
        {
          id: "ws_live",
          name: "Live workspace",
          slug: "live",
          role: "owner",
        },
      ]),
    ).toBe("ws_live");
    expect(resolveEvalWorkspaceId([], undefined)).toBeNull();
  });
});

describe("EvalsIndexPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    restoreEnv("LOOP_DEFAULT_WORKSPACE_ID", ORIGINAL_WORKSPACE);
    restoreEnv("LOOP_TOKEN", ORIGINAL_TOKEN);
    vi.unstubAllGlobals();
  });

  it("loads suites through the workspace-scoped control-plane route", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    process.env.LOOP_TOKEN = "test-token";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    delete process.env.LOOP_DEFAULT_WORKSPACE_ID;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url === "https://cp.test/v1/workspaces") {
        return Response.json({
          items: [
            {
              id: "ws_eval",
              name: "Eval workspace",
              slug: "eval",
              role: "owner",
            },
          ],
        });
      }
      if (url === "https://cp.test/v1/workspaces/ws_eval/eval-suites") {
        return Response.json({
          items: [
            {
              id: "suite_eval",
              name: "Trace regression",
              cases: 8,
              last_run_at: "2026-05-09T10:05:00Z",
              pass_rate: 0.875,
            },
          ],
        });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(await EvalsIndexPage());

    expect(screen.getByTestId("eval-foundry")).toBeInTheDocument();
    expect(screen.getByTestId("eval-suite-suite_eval")).toHaveTextContent(
      "Trace regression",
    );
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws_eval/eval-suites",
      expect.objectContaining({ method: "GET" }),
    );
    expect(screen.queryByText(/Eval suites unavailable/)).toBeNull();
  });

  it("keeps focused case links visible in Eval Foundry", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    process.env.LOOP_TOKEN = "test-token";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    delete process.env.LOOP_DEFAULT_WORKSPACE_ID;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url === "https://cp.test/v1/workspaces") {
        return Response.json({
          items: [
            {
              id: "ws_eval",
              name: "Eval workspace",
              slug: "eval",
              role: "owner",
            },
          ],
        });
      }
      if (url === "https://cp.test/v1/workspaces/ws_eval/eval-suites") {
        return Response.json({ items: [] });
      }
      return new Response("missing", { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(
      await EvalsIndexPage({
        searchParams: {
          case_id: "case_refund_regression",
        },
      }),
    );

    expect(screen.getByTestId("eval-foundry-focused-case")).toHaveTextContent(
      "case_refund_regression",
    );
  });

  it("surfaces missing workspace context instead of fixture suites", async () => {
    delete process.env.LOOP_CP_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    delete process.env.LOOP_DEFAULT_WORKSPACE_ID;
    delete process.env.LOOP_TOKEN;

    render(await EvalsIndexPage());

    expect(screen.getByTestId("eval-foundry")).toBeInTheDocument();
    expect(screen.getByText("Eval suites unavailable")).toBeInTheDocument();
    expect(
      screen.getByText(/Workspace context is required/),
    ).toBeInTheDocument();
  });
});
