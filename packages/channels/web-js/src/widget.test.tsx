import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { ChatWidget } from "./widget";
import type { WebChannelEvent } from "./index";

function makeStream() {
  const queue: WebChannelEvent[] = [];
  let resolveNext: (() => void) | null = null;
  let done = false;
  const stream = async function* () {
    while (true) {
      while (queue.length > 0) yield queue.shift()!;
      if (done) return;
      await new Promise<void>((r) => {
        resolveNext = r;
      });
    }
  };
  return {
    stream,
    push(event: WebChannelEvent) {
      queue.push(event);
      resolveNext?.();
      resolveNext = null;
    },
    end() {
      done = true;
      resolveNext?.();
      resolveNext = null;
    },
  };
}

describe("ChatWidget", () => {
  it("renders the empty state when no messages exist", () => {
    render(<ChatWidget stream={async function* () {}} />);
    expect(screen.getByTestId("chat-empty")).toBeInTheDocument();
  });

  it("submits the prompt, streams tokens into a single bubble, and closes on complete", async () => {
    const harness = makeStream();
    render(<ChatWidget stream={() => harness.stream()} />);

    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "hello" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("chat-send"));
      await Promise.resolve();
    });

    expect(screen.getByTestId("chat-message-user")).toHaveTextContent("hello");

    await act(async () => {
      harness.push({ type: "token", text: "Hi" });
      await Promise.resolve();
      await Promise.resolve();
    });
    await act(async () => {
      harness.push({ type: "token", text: " there" });
      await Promise.resolve();
      await Promise.resolve();
    });
    await act(async () => {
      harness.push({
        type: "complete",
        text: "Hi there",
      });
      harness.end();
      await Promise.resolve();
      await Promise.resolve();
    });

    const assistant = screen.getByTestId("chat-message-assistant");
    expect(assistant).toHaveTextContent("Hi there");
    expect(assistant.getAttribute("data-status")).toBe("complete");
  });

  it("surfaces stream errors as a banner and marks the bubble as error", async () => {
    const stream = vi.fn(async function* () {
      yield {
        type: "error" as const,
        message: "boom",
        status: 500,
        requestId: "req_42",
      };
    });
    render(<ChatWidget stream={stream as never} />);
    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "hi" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("chat-send"));
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByTestId("chat-error")).toHaveTextContent("boom");
    expect(screen.getByTestId("chat-error")).toHaveTextContent("req_42");
    expect(
      screen.getByTestId("chat-message-assistant").getAttribute("data-status"),
    ).toBe("error");
  });

  it("disables Send while streaming", async () => {
    const harness = makeStream();
    render(<ChatWidget stream={() => harness.stream()} />);
    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "hi" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("chat-send"));
      await Promise.resolve();
    });
    const send = screen.getByTestId("chat-send") as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    await act(async () => {
      harness.end();
      await Promise.resolve();
      await Promise.resolve();
    });
  });
});
