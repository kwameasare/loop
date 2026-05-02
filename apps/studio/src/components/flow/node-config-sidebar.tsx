"use client";

import { useEffect, useState } from "react";

import {
  type AnyNodeConfig,
  type ValidationErrors,
  defaultConfigFor,
  validateNodeConfig,
} from "@/lib/flow-node-config";
import { type FlowNode, getNodeKind } from "@/lib/flow-nodes";

export interface NodeConfigSidebarProps {
  node: FlowNode;
  config: AnyNodeConfig | undefined;
  onPersist: (next: AnyNodeConfig) => void;
  onClose: () => void;
}

export function NodeConfigSidebar(props: NodeConfigSidebarProps) {
  const kind = getNodeKind(props.node.type);
  const [draft, setDraft] = useState<AnyNodeConfig>(
    props.config ?? defaultConfigFor(props.node.type),
  );
  const [errors, setErrors] = useState<ValidationErrors>({});

  // When the selected node changes, refresh draft from props.
  useEffect(() => {
    setDraft(props.config ?? defaultConfigFor(props.node.type));
    setErrors({});
    // Only reset when the user selects a different node; persisting the
    // current node's config via onPersist must not clobber local state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.node.id, props.node.type]);

  function commit(next: AnyNodeConfig) {
    const errs = validateNodeConfig(props.node.type, next);
    setErrors(errs);
    props.onPersist(next);
  }

  function setField<K extends string>(key: K, value: unknown) {
    setDraft((d) => {
      const next = {
        ...(d as Record<string, unknown>),
        [key]: value,
      } as AnyNodeConfig;
      setErrors(validateNodeConfig(props.node.type, next));
      return next;
    });
  }

  function blur() {
    commit(draft);
  }

  return (
    <aside
      aria-label="Node configuration"
      className="flex w-80 flex-col gap-4 border-l bg-white p-4"
      data-testid="node-sidebar"
    >
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className={`flex h-7 w-7 items-center justify-center rounded text-base ${kind.color}`}
          >
            {kind.icon}
          </span>
          <div>
            <p className="text-xs uppercase text-zinc-500">
              {kind.label} node
            </p>
            <p
              className="font-mono text-xs text-zinc-700"
              data-testid="node-sidebar-id"
            >
              {props.node.id}
            </p>
          </div>
        </div>
        <button
          aria-label="Close node configuration"
          className="rounded border px-2 py-1 text-xs hover:bg-zinc-50"
          data-testid="node-sidebar-close"
          onClick={props.onClose}
          type="button"
        >
          Close
        </button>
      </header>

      <label className="flex flex-col gap-1 text-sm">
        <span className="text-xs uppercase text-zinc-500">Label</span>
        <input
          className="rounded border px-2 py-1"
          data-testid="node-config-label"
          onBlur={blur}
          onChange={(e) => setField("label", e.target.value)}
          type="text"
          value={(draft as { label?: string }).label ?? ""}
        />
      </label>

      {props.node.type === "message" ? (
        <Field error={errors.body} label="Body" testid="node-config-body">
          <textarea
            className="rounded border px-2 py-1"
            data-testid="node-config-body-input"
            onBlur={blur}
            onChange={(e) => setField("body", e.target.value)}
            rows={4}
            value={(draft as { body?: string }).body ?? ""}
          />
        </Field>
      ) : null}

      {props.node.type === "condition" ? (
        <Field
          error={errors.expression}
          label="Expression"
          testid="node-config-expression"
        >
          <input
            className="rounded border px-2 py-1 font-mono"
            data-testid="node-config-expression-input"
            onBlur={blur}
            onChange={(e) => setField("expression", e.target.value)}
            type="text"
            value={(draft as { expression?: string }).expression ?? ""}
          />
        </Field>
      ) : null}

      {props.node.type === "ai-task" ? (
        <>
          <Field
            error={errors.model}
            label="Model"
            testid="node-config-model"
          >
            <input
              className="rounded border px-2 py-1"
              data-testid="node-config-model-input"
              onBlur={blur}
              onChange={(e) => setField("model", e.target.value)}
              type="text"
              value={(draft as { model?: string }).model ?? ""}
            />
          </Field>
          <Field
            error={errors.prompt}
            label="Prompt"
            testid="node-config-prompt"
          >
            <textarea
              className="rounded border px-2 py-1"
              data-testid="node-config-prompt-input"
              onBlur={blur}
              onChange={(e) => setField("prompt", e.target.value)}
              rows={4}
              value={(draft as { prompt?: string }).prompt ?? ""}
            />
          </Field>
        </>
      ) : null}

      {props.node.type === "http" ? (
        <>
          <Field
            error={undefined}
            label="Method"
            testid="node-config-method"
          >
            <select
              className="rounded border px-2 py-1"
              data-testid="node-config-method-input"
              onBlur={blur}
              onChange={(e) => setField("method", e.target.value)}
              value={(draft as { method?: string }).method ?? "GET"}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </Field>
          <Field error={errors.url} label="URL" testid="node-config-url">
            <input
              className="rounded border px-2 py-1 font-mono"
              data-testid="node-config-url-input"
              onBlur={blur}
              onChange={(e) => setField("url", e.target.value)}
              type="url"
              value={(draft as { url?: string }).url ?? ""}
            />
          </Field>
        </>
      ) : null}

      {props.node.type === "code" ? (
        <Field
          error={errors.source}
          label="Source"
          testid="node-config-source"
        >
          <textarea
            className="rounded border px-2 py-1 font-mono text-xs"
            data-testid="node-config-source-input"
            onBlur={blur}
            onChange={(e) => setField("source", e.target.value)}
            rows={6}
            value={(draft as { source?: string }).source ?? ""}
          />
        </Field>
      ) : null}

      {props.node.type === "start" || props.node.type === "end" ? (
        <p
          className="rounded border border-dashed border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-500"
          data-testid="node-config-no-fields"
        >
          {kind.label} nodes have no additional configuration.
        </p>
      ) : null}
    </aside>
  );
}

function Field({
  children,
  error,
  label,
  testid,
}: {
  children: React.ReactNode;
  error: string | undefined;
  label: string;
  testid: string;
}) {
  return (
    <div className="flex flex-col gap-1 text-sm" data-testid={testid}>
      <span className="text-xs uppercase text-zinc-500">{label}</span>
      {children}
      {error ? (
        <p
          className="text-xs text-red-600"
          data-testid={`${testid}-error`}
          role="alert"
        >
          {error}
        </p>
      ) : null}
    </div>
  );
}
