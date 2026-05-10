import { render, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import EnterprisePage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_enterprise", name: "Enterprise Workspace" },
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("EnterprisePage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("renders degraded SAML evidence when the workspace SAML route is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () => new Response("missing", { status: 404 })),
    );

    const view = render(<EnterprisePage />);

    await waitFor(() => {
      expect(view.getByTestId("idp-degraded")).toHaveTextContent(
        "SAML evidence unavailable",
      );
    });
    expect(view.getByTestId("idp-degraded")).toHaveTextContent(
      "enterprise SAML route returned 404",
    );
    expect(view.getByTestId("idp-connect-submit")).toBeDisabled();
    expect(view.queryByRole("alert")).not.toBeInTheDocument();
  });
});
