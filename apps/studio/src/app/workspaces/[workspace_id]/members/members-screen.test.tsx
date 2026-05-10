import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MembersScreen } from "./members-screen";

const membersMocks = vi.hoisted(() => ({
  addMember: vi.fn(),
  listMembers: vi.fn(),
  removeMember: vi.fn(),
  updateMemberRole: vi.fn(),
}));

vi.mock("@/lib/members", () => ({
  addMember: membersMocks.addMember,
  listMembers: membersMocks.listMembers,
  removeMember: membersMocks.removeMember,
  updateMemberRole: membersMocks.updateMemberRole,
}));

describe("MembersScreen", () => {
  beforeEach(() => {
    membersMocks.addMember.mockReset();
    membersMocks.listMembers.mockReset();
    membersMocks.removeMember.mockReset();
    membersMocks.updateMemberRole.mockReset();
  });

  it("shows degraded membership evidence instead of a raw route alert when members cannot load", async () => {
    membersMocks.listMembers.mockRejectedValue(
      new Error("LOOP_CP_API_BASE_URL is required for member calls"),
    );

    render(
      <MembersScreen workspaceId="ws_members" currentUserSub="user_admin" />,
    );

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Members is degraded/i);
      expect(state).toHaveTextContent(/membership and role evidence/i);
      expect(state).toHaveTextContent(/LOOP_CP_API_BASE_URL is required/i);
    });
  });
});
