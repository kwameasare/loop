import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CollaborateReviewPage from "./page";

const collaborationMocks = vi.hoisted(() => ({
  fetchCollaborationWorkspace: vi.fn(),
}));

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_review", name: "Review Workspace" },
    isLoading: false,
  }),
}));

vi.mock("@/lib/collaboration", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/collaboration")>();
  return {
    ...actual,
    fetchCollaborationWorkspace: collaborationMocks.fetchCollaborationWorkspace,
  };
});

describe("CollaborateReviewPage", () => {
  beforeEach(() => {
    collaborationMocks.fetchCollaborationWorkspace.mockReset();
  });

  it("shows degraded collaboration evidence while preserving the review workspace", async () => {
    collaborationMocks.fetchCollaborationWorkspace.mockRejectedValue(
      new Error("cp-api GET collaboration workspace -> 503"),
    );

    render(<CollaborateReviewPage />);

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Collaboration evidence is degraded/i);
      expect(state).toHaveTextContent(/changeset, comment, and pair-debug/i);
      expect(state).toHaveTextContent(/cp-api GET collaboration workspace/i);
    });
    expect(screen.getByTestId("collaborate-review-page")).toBeInTheDocument();
    expect(screen.getByTestId("changeset-empty")).toBeInTheDocument();
    expect(screen.getByTestId("comments-empty")).toBeInTheDocument();
  });
});
