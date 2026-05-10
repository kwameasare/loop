"use client";

import { useEffect, useRef, useState } from "react";

import type { FlowEdge } from "@/lib/flow-edges";
import type { FlowNode } from "@/lib/flow-nodes";
import {
  type FlowApi,
  flowFromYaml,
  flowToYaml,
} from "@/lib/flow-yaml";

export interface FlowPersistencePanelProps {
  agentId: string;
  api: FlowApi;
  /** Current in-memory flow doc to be saved. */
  doc: { nodes: FlowNode[]; edges: FlowEdge[] };
  /** Called when ``Load`` (mount or button) returns a doc. */
  onLoad: (doc: { nodes: FlowNode[]; edges: FlowEdge[] }) => void;
}

type Status =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "saving" }
  | { kind: "saved"; versionTag: string }
  | { kind: "loaded"; versionTag: string }
  | { kind: "conflict"; serverTag: string }
  | { kind: "error"; message: string };

export function FlowPersistencePanel(props: FlowPersistencePanelProps) {
  const [versionTag, setVersionTag] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const loadedOnce = useRef(false);

  async function load() {
    setStatus({ kind: "loading" });
    try {
      const v = await props.api.load(props.agentId);
      if (!v) {
        setStatus({ kind: "idle" });
        setVersionTag(null);
        return;
      }
      const parsed = flowFromYaml(v.flowYaml);
      props.onLoad(parsed);
      setVersionTag(v.versionTag);
      setStatus({ kind: "loaded", versionTag: v.versionTag });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "load failed",
      });
    }
  }

  useEffect(() => {
    if (loadedOnce.current) return;
    loadedOnce.current = true;
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.agentId]);

  async function save() {
    setStatus({ kind: "saving" });
    const yaml = flowToYaml(props.doc);
    try {
      const result = await props.api.save(props.agentId, {
        flowYaml: yaml,
        baseVersionTag: versionTag,
      });
      if (result.ok && result.versionTag) {
        setVersionTag(result.versionTag);
        setStatus({ kind: "saved", versionTag: result.versionTag });
        return;
      }
      if (result.error === "stale_version_tag") {
        setStatus({
          kind: "conflict",
          serverTag: result.serverVersionTag ?? "(unknown)",
        });
        return;
      }
      setStatus({
        kind: "error",
        message: result.error ?? "save failed",
      });
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "save failed",
      });
    }
  }

  async function reloadFromServer() {
    await load();
    setStatus({ kind: "idle" });
  }

  return (
    <section
      aria-label="Flow persistence"
      className="flex items-center gap-3 border-b bg-card px-4 py-2"
      data-testid="flow-persistence"
    >
      <button
        className="rounded bg-primary px-3 py-1 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground"
        data-testid="flow-save"
        disabled={status.kind === "saving" || status.kind === "loading"}
        onClick={save}
        type="button"
      >
        Save
      </button>
      <button
        className="rounded border bg-background px-3 py-1 text-sm text-foreground hover:bg-muted disabled:opacity-50"
        data-testid="flow-reload"
        disabled={status.kind === "loading"}
        onClick={reloadFromServer}
        type="button"
      >
        Reload
      </button>
      <span
        className="font-mono text-xs text-muted-foreground"
        data-testid="flow-version-tag"
      >
        {versionTag ? `version: ${versionTag}` : "version: (unsaved)"}
      </span>
      {status.kind === "saving" || status.kind === "loading" ? (
        <span
          className="text-xs text-muted-foreground"
          data-testid="flow-persistence-busy"
        >
          {status.kind === "saving" ? "Saving…" : "Loading…"}
        </span>
      ) : null}
      {status.kind === "saved" ? (
        <span
          className="text-xs text-success"
          data-testid="flow-saved"
          role="status"
        >
          Saved as {status.versionTag}.
        </span>
      ) : null}
      {status.kind === "loaded" ? (
        <span
          className="text-xs text-muted-foreground"
          data-testid="flow-loaded"
          role="status"
        >
          Loaded {status.versionTag}.
        </span>
      ) : null}
      {status.kind === "error" ? (
        <span
          className="text-xs text-destructive"
          data-testid="flow-persistence-error"
          role="alert"
        >
          {status.message}
        </span>
      ) : null}
      {status.kind === "conflict" ? (
        <div
          className="flex items-center gap-2 rounded border border-warning/30 bg-warning/10 px-2 py-1 text-xs text-warning"
          data-testid="flow-conflict"
          role="alert"
        >
          <span>
            Server has a newer version ({status.serverTag}). Reload before
            saving.
          </span>
          <button
            className="rounded border border-warning/40 bg-background px-2 py-0.5 hover:bg-warning/10"
            data-testid="flow-conflict-reload"
            onClick={reloadFromServer}
            type="button"
          >
            Reload now
          </button>
        </div>
      ) : null}
    </section>
  );
}
