import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { _resetFlowNodeIds } from "@/lib/flow-nodes";

import { FlowEditor } from "./flow-editor";

beforeEach(() => {
  _resetFlowNodeIds();
});

describe("Node config sidebar", () => {
  it("clicking a node opens the sidebar with no fields for start nodes", async () => {
    render(
      <FlowEditor
        agentId="a1"
        initialNodes={[{ id: "start-1", type: "start", x: 100, y: 100 }]}
      />,
    );
    expect(screen.queryByTestId("node-sidebar")).toBeNull();
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-node-start-1"));
    });
    expect(screen.getByTestId("node-sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("node-sidebar-id").textContent).toBe("start-1");
    expect(screen.getByTestId("node-config-no-fields")).toBeInTheDocument();
  });

  it("persists a message body on blur and surfaces validation when blank", async () => {
    render(
      <FlowEditor
        agentId="a1"
        initialNodes={[{ id: "message-1", type: "message", x: 0, y: 0 }]}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-node-message-1"));
    });
    const body = screen.getByTestId("node-config-body-input");
    // Blank → blur should produce a validation error.
    await act(async () => {
      fireEvent.blur(body);
    });
    expect(
      screen.getByTestId("node-config-body-error").textContent,
    ).toMatch(/required/);
    await act(async () => {
      fireEvent.change(body, { target: { value: "Hello" } });
      fireEvent.blur(body);
    });
    expect(screen.queryByTestId("node-config-body-error")).toBeNull();
    // Closing and reopening keeps the persisted value.
    await act(async () => {
      fireEvent.click(screen.getByTestId("node-sidebar-close"));
    });
    expect(screen.queryByTestId("node-sidebar")).toBeNull();
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-node-message-1"));
    });
    expect(
      (screen.getByTestId("node-config-body-input") as HTMLTextAreaElement)
        .value,
    ).toBe("Hello");
  });

  it("validates HTTP node URLs", async () => {
    render(
      <FlowEditor
        agentId="a1"
        initialNodes={[{ id: "http-1", type: "http", x: 0, y: 0 }]}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-node-http-1"));
    });
    const url = screen.getByTestId("node-config-url-input");
    await act(async () => {
      fireEvent.change(url, { target: { value: "ftp:/oops" } });
      fireEvent.blur(url);
    });
    // ftp:/oops is parseable by URL, so try a hard invalid string instead.
    await act(async () => {
      fireEvent.change(url, { target: { value: "not a url" } });
      fireEvent.blur(url);
    });
    expect(
      screen.getByTestId("node-config-url-error").textContent,
    ).toMatch(/valid absolute URL/);
    await act(async () => {
      fireEvent.change(url, { target: { value: "https://example.com/x" } });
      fireEvent.blur(url);
    });
    expect(screen.queryByTestId("node-config-url-error")).toBeNull();
  });

  it("ai-task validates required prompt and model", async () => {
    render(
      <FlowEditor
        agentId="a1"
        initialNodes={[{ id: "ai-task-1", type: "ai-task", x: 0, y: 0 }]}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-node-ai-task-1"));
    });
    const prompt = screen.getByTestId("node-config-prompt-input");
    await act(async () => {
      fireEvent.blur(prompt);
    });
    expect(
      screen.getByTestId("node-config-prompt-error").textContent,
    ).toMatch(/required/);
    expect(screen.queryByTestId("node-config-model-error")).toBeNull();
  });
});
