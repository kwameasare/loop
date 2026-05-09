import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChannelPreviewMatrix } from "./channel-preview-matrix";
import {
  type ChannelPreviewMatrixRequest,
  buildLocalChannelBindings,
  buildLocalPreviewMatrix,
} from "@/lib/channel-bindings";

describe("ChannelPreviewMatrix", () => {
  it("renders the same scenario across selected peer channels", async () => {
    const bindings = buildLocalChannelBindings("agt_1").map((binding) =>
      binding.channel_type === "whatsapp" || binding.channel_type === "email"
        ? { ...binding, status: "draft" as const }
        : binding,
    );
    const previewChannelMatrix = vi.fn(
      async (_agentId: string, input: ChannelPreviewMatrixRequest) =>
        buildLocalPreviewMatrix("agt_1", input, bindings),
    );

    render(
      <ChannelPreviewMatrix
        agentId="agt_1"
        bindings={bindings}
        previewChannelMatrix={previewChannelMatrix}
      />,
    );

    fireEvent.click(screen.getByText("Render preview matrix"));

    await waitFor(() => {
      expect(previewChannelMatrix).toHaveBeenCalledWith(
        "agt_1",
        expect.objectContaining({
          channel_types: expect.arrayContaining(["whatsapp", "email"]),
        }),
      );
    });
    expect(
      screen.getByTestId("channel-preview-row-whatsapp"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("channel-preview-row-email")).toBeInTheDocument();
  });

  it("turns channel formatting failures into eval cases", async () => {
    const bindings = buildLocalChannelBindings("agt_1").map((binding) =>
      binding.channel_type === "sms"
        ? { ...binding, status: "draft" as const }
        : binding,
    );
    const previewChannelMatrix = vi.fn(
      async (_agentId: string, input: ChannelPreviewMatrixRequest) =>
        buildLocalPreviewMatrix(
          "agt_1",
          {
            ...input,
            expected_outcome:
              "Acknowledge the duplicate charge, verify the account, explain the refund path, mention the SLA, explain escalation, and include opt-out language for short-message channels.",
            channel_types: ["sms"],
          },
          bindings,
        ),
    );
    const createChannelPreviewEvalCase = vi.fn(async () => ({
      case_id: "case_sms_1",
    }));

    render(
      <ChannelPreviewMatrix
        agentId="agt_1"
        bindings={bindings}
        previewChannelMatrix={previewChannelMatrix}
        createChannelPreviewEvalCase={createChannelPreviewEvalCase}
      />,
    );

    fireEvent.click(screen.getByText("Render preview matrix"));
    await screen.findByText("SMS preview exceeds 160 characters.");
    fireEvent.click(screen.getByText("Save as eval case"));

    await waitFor(() => {
      expect(createChannelPreviewEvalCase).toHaveBeenCalledWith(
        "agt_1",
        expect.objectContaining({
          channel_type: "sms",
          failure_reason: "SMS preview exceeds 160 characters.",
        }),
      );
    });
    expect(screen.getByText("Eval case saved: case_sms_1")).toBeInTheDocument();
  });
});
