import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import ConversationPage from "./page";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_1", name: "Workspace" },
    isLoading: false,
  }),
}));

const ORIGINAL_BASE = process.env.LOOP_CP_API_BASE_URL;
const ORIGINAL_PUBLIC_BASE = process.env.NEXT_PUBLIC_LOOP_API_URL;

function restoreEnv(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}

describe("ConversationPage", () => {
  afterEach(() => {
    restoreEnv("LOOP_CP_API_BASE_URL", ORIGINAL_BASE);
    restoreEnv("NEXT_PUBLIC_LOOP_API_URL", ORIGINAL_PUBLIC_BASE);
    vi.unstubAllGlobals();
  });

  it("renders degraded conversation evidence instead of empty live controls when cp-api returns 404", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test/v1";
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    const fetcher = vi.fn<typeof fetch>(
      async () => new Response("missing", { status: 404 }),
    );
    vi.stubGlobal("fetch", fetcher);

    const view = render(<ConversationPage params={{ id: "conv_missing" }} />);

    await waitFor(() => {
      expect(view.container).toHaveTextContent("Conversation conv_missing");
      expect(view.container).toHaveTextContent(
        "conversation route returned 404",
      );
      expect(view.container).toHaveTextContent(
        "Conversation transcript unavailable.",
      );
    });
    expect(view.container).not.toHaveTextContent(
      "Agent is handling this conversation.",
    );
    expect(view.queryByTestId("conversation-takeover")).not.toBeInTheDocument();
    expect(view.getByTestId("conversation-composer-input")).toBeDisabled();
  });
});
