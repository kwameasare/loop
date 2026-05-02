/**
 * S178: Tests for typing indicator + history persistence (sessionStorage).
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { ChatWidget } from "./widget";
import type { WebChannelEvent } from "./index";

// ---------------------------------------------------------------------------
// sessionStorage stub
// ---------------------------------------------------------------------------

const store: Record<string, string> = {};
const sessionStorageMock = {
  getItem: (k: string) => store[k] ?? null,
  setItem: (k: string, v: string) => {
    store[k] = v;
  },
  removeItem: (k: string) => {
    delete store[k];
  },
  clear: () => {
    for (const k of Object.keys(store)) delete store[k];
  },
};
Object.defineProperty(globalThis, "sessionStorage", {
  value: sessionStorageMock,
  writable: true,
});

// ---------------------------------------------------------------------------
// Stream test harness
// ---------------------------------------------------------------------------

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

describe("ChatWidget -- S178 typing indicator", () => {
  beforeEach(() => sessionStorageMock.clear());
  afterEach(() => sessionStorageMock.clear());

  it("shows typing indicator while streaming before any tokens arrive", async () => {
    const harness = makeStream();
    render(<ChatWidget stream={() => harness.stream()} />);

    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "ping" },
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId("chat-send"));
      await Promise.resolve();
    });

    // No token yet -- typing indicator should appear
    expect(screen.getByTestId("chat-typing-indicator")).toBeInTheDocument();

    // After token arrives typing indicator should disappear
    await act(async () => {
      harness.push({ type: "token", text: "Hi" });
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.queryByTestId("chat-typing-indicator")).toBeNull();

    // Cleanup
    await act(async () => {
      harness.push({ type: "complete", text: "Hi" });
      harness.end();
      await Promise.resolve();
      await Promise.resolve();
    });
  });

  it("hides typing indicator once the response completes", async () => {
    const harness = makeStream();
    render(<ChatWidget stream={() => harness.stream()} />);

    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "hello" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("chat-send"));
      await Promise.resolve();
    });

    await act(async () => {
      harness.push({ type: "token", text: "Hey" });
      harness.push({ type: "complete", text: "Hey" });
      harness.end();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.queryByTestId("chat-typing-indicator")).toBeNull();
  });
});

describe("ChatWidget -- S178 history persistence", () => {
  beforeEach(() => sessionStorageMock.clear());
  afterEach(() => sessionStorageMock.clear());

  it("restores messages from sessionStorage on mount", () => {
    const history = [
      { id: "m_1", role: "user" as const, text: "Old question", status: "complete" as const },
      { id: "m_2", role: "assistant" as const, text: "Old answer", status: "complete" as const },
    ];
    sessionStorageMock.setItem("test-key", JSON.stringify(history));

    render(<ChatWidget stream={async function* () {}} historyKey="test-key" />);

    expect(screen.getByText("Old question")).toBeInTheDocument();
    expect(screen.getByText("Old answer")).toBeInTheDocument();
  });

  it("persists completed messages to sessionStorage after a full exchange", async () => {
    const harness = makeStream();
    render(
      <ChatWidget stream={() => harness.stream()} historyKey="chat-persist" />,
    );

    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "test msg" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("chat-send"));
      await Promise.resolve();
    });
    await act(async () => {
      harness.push({ type: "complete", text: "reply" });
      harness.end();
      await Promise.resolve();
      await Promise.resolve();
    });

    const stored = sessionStorageMock.getItem("chat-persist");
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored!) as Array<{ text: string }>;
    expect(parsed.some((m) => m.text === "test msg")).toBe(true);
    expect(parsed.some((m) => m.text === "reply")).toBe(true);
  });

  it("does not persist when historyKey is not provided", async () => {
    const harness = makeStream();
    render(<ChatWidget stream={() => harness.stream()} />);

    fireEvent.change(screen.getByTestId("chat-input"), {
      target: { value: "no persist" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("chat-send"));
      harness.push({ type: "complete", text: "ok" });
      harness.end();
      await Promise.resolve();
      await Promise.resolve();
    });

    // Nothing was written to sessionStorage
    expect(Object.keys(store)).toHaveLength(0);
  });

  it("ignores sessionStorage entries with streaming/error status on restore", () => {
    const history = [
      { id: "m_bad", role: "assistant" as const, text: "partial", status: "streaming" as const },
    ];
    sessionStorageMock.setItem("test-key2", JSON.stringify(history));

    render(<ChatWidget stream={async function* () {}} historyKey="test-key2" />);

    // The partial streaming message should not appear
    expect(screen.queryByText("partial")).toBeNull();
  });
});
