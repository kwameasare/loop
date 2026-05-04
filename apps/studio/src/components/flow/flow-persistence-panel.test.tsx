import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  type FlowApi,
  flowToYaml,
  makeMemoryFlowApi,
} from "@/lib/flow-yaml";

import { FlowPersistencePanel } from "./flow-persistence-panel";

const EMPTY_DOC = { nodes: [], edges: [] };
const SAMPLE_DOC = {
  nodes: [{ id: "start-1", type: "start" as const, x: 0, y: 0 }],
  edges: [],
};

describe("FlowPersistencePanel", () => {
  it("loads on mount and reports the loaded version tag", async () => {
    const api = makeMemoryFlowApi({
      agentId: "a1",
      flowYaml: flowToYaml(SAMPLE_DOC),
      versionTag: "v-seed",
    });
    const onLoad = vi.fn();
    render(
      <FlowPersistencePanel
        agentId="a1"
        api={api}
        doc={EMPTY_DOC}
        onLoad={onLoad}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("flow-loaded").textContent).toContain(
        "v-seed",
      );
    });
    expect(onLoad).toHaveBeenCalledWith(SAMPLE_DOC);
    expect(screen.getByTestId("flow-version-tag").textContent).toContain(
      "v-seed",
    );
  });

  it("save posts and rotates the version tag on success", async () => {
    const api = makeMemoryFlowApi();
    render(
      <FlowPersistencePanel
        agentId="a1"
        api={api}
        doc={SAMPLE_DOC}
        onLoad={() => undefined}
      />,
    );
    // Wait for the initial mount load to settle (no seed → idle).
    await waitFor(() => {
      expect(screen.getByTestId("flow-version-tag").textContent).toContain(
        "(unsaved)",
      );
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-save"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("flow-saved").textContent).toContain("v-1");
    });
  });

  it("save with a stale base tag surfaces the server's tag in a conflict alert", async () => {
    let currentTag: string | null = "v-server-1";
    const stub: FlowApi = {
      async load() {
        return {
          flowYaml: flowToYaml(SAMPLE_DOC),
          versionTag: currentTag ?? "",
        };
      },
      async save(_agent, body) {
        if (body.baseVersionTag !== currentTag) {
          return currentTag
            ? {
                ok: false,
                error: "stale_version_tag",
                serverVersionTag: currentTag,
              }
            : {
                ok: false,
                error: "stale_version_tag",
              };
        }
        currentTag = "v-server-2";
        return { ok: true, versionTag: "v-server-2" };
      },
    };
    render(
      <FlowPersistencePanel
        agentId="a1"
        api={stub}
        doc={SAMPLE_DOC}
        onLoad={() => undefined}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("flow-loaded")).toBeInTheDocument();
    });
    // Simulate someone else saving to the server in the background.
    currentTag = "v-server-99";
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-save"));
    });
    await waitFor(() => {
      const conflict = screen.getByTestId("flow-conflict");
      expect(conflict.textContent).toContain("v-server-99");
    });
    expect(
      screen.getByTestId("flow-conflict-reload"),
    ).toBeInTheDocument();
  });

  it("reload after conflict pulls the server's current tag", async () => {
    let currentTag: string | null = "v-1";
    const stub: FlowApi = {
      async load() {
        return {
          flowYaml: flowToYaml(SAMPLE_DOC),
          versionTag: currentTag ?? "",
        };
      },
      async save(_agent, body) {
        if (body.baseVersionTag !== currentTag) {
          return currentTag
            ? {
                ok: false,
                error: "stale_version_tag",
                serverVersionTag: currentTag,
              }
            : {
                ok: false,
                error: "stale_version_tag",
              };
        }
        return { ok: true, versionTag: "v-next" };
      },
    };
    render(
      <FlowPersistencePanel
        agentId="a1"
        api={stub}
        doc={SAMPLE_DOC}
        onLoad={() => undefined}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("flow-loaded")).toBeInTheDocument();
    });
    currentTag = "v-2";
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-save"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("flow-conflict")).toBeInTheDocument();
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-conflict-reload"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("flow-version-tag").textContent).toContain(
        "v-2",
      );
    });
  });
});
