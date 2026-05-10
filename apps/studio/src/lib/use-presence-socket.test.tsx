import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { usePresenceSocket } from "./use-presence-socket";

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  readonly url: string;
  readonly sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.onclose?.();
  }

  open(): void {
    this.onopen?.();
  }

  receive(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
}

function PresenceHarness(): JSX.Element {
  const state = usePresenceSocket({
    workspaceId: "ws_1",
    callerSub: "sam@example.test",
    display: "Sam Reviewer",
    focus: "trace/t-1",
  });
  return (
    <div>
      <p data-testid="socket-url">{state.socketUrl}</p>
      <p data-testid="connected">{state.connected ? "yes" : "no"}</p>
      <p data-testid="error">{state.error ?? "none"}</p>
      <ul>
        {state.users.map((user) => (
          <li key={user.id} data-testid={`presence-${user.id}`}>
            {user.display} · {user.status} · {user.focus}
          </li>
        ))}
      </ul>
    </div>
  );
}

describe("usePresenceSocket", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    MockWebSocket.instances = [];
  });

  it("subscribes to cp-api presence websocket and applies peer updates", async () => {
    vi.stubEnv("NEXT_PUBLIC_LOOP_API_URL", "https://cp.example.test");
    vi.stubGlobal("WebSocket", MockWebSocket);

    render(<PresenceHarness />);

    const socket = MockWebSocket.instances[0]!;
    expect(socket.url).toBe(
      "wss://cp.example.test/v1/workspaces/ws_1/presence?caller_sub=sam%40example.test",
    );
    expect(screen.getByTestId("presence-sam@example.test")).toHaveTextContent(
      "Sam Reviewer",
    );

    act(() => socket.open());

    await waitFor(() => {
      expect(screen.getByTestId("connected")).toHaveTextContent("yes");
    });
    expect(JSON.parse(socket.sent[0]!)).toMatchObject({
      type: "presence.update",
      display: "Sam Reviewer",
      status: "active",
      focus: "trace/t-1",
    });

    act(() =>
      socket.receive({
        type: "presence.update",
        user: "maya@example.test",
        display: "Maya Ops",
        status: "viewing",
        focus: "trace/t-2",
      }),
    );

    expect(screen.getByTestId("presence-maya@example.test")).toHaveTextContent(
      "Maya Ops · viewing · trace/t-2",
    );

    act(() =>
      socket.receive({
        type: "presence.left",
        user: "maya@example.test",
      }),
    );

    expect(
      screen.queryByTestId("presence-maya@example.test"),
    ).not.toBeInTheDocument();
  });

  it("does not invent realtime presence when websocket configuration is absent", () => {
    render(<PresenceHarness />);

    expect(MockWebSocket.instances).toHaveLength(0);
    expect(screen.getByTestId("socket-url")).toHaveTextContent("");
    expect(screen.getByTestId("connected")).toHaveTextContent("no");
    expect(screen.queryByTestId("presence-sam@example.test")).toBeNull();
  });
});
