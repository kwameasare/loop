"use client";

import { useEffect, useId, useState, type FormEvent } from "react";

import {
  type AgentSecret,
  type AddAgentSecretInput,
  type RotateAgentSecretInput,
  addAgentSecret as defaultAddAgentSecret,
  rotateAgentSecret as defaultRotateAgentSecret,
} from "@/lib/agent-secrets";

export interface SecretsListProps {
  agentId: string;
  initialSecrets: AgentSecret[];
  /** Override for tests. */
  addSecret?: (input: AddAgentSecretInput) => Promise<AgentSecret>;
  rotateSecret?: (
    input: RotateAgentSecretInput,
  ) => Promise<{ secretId: string; rotated_at: string }>;
}

type Toast = { kind: "success" | "error"; message: string } | null;

const SECRET_NAME_HINT =
  "Use SCREAMING_SNAKE_CASE — only A–Z, 0–9 and underscore.";
const NAME_RE = /^[A-Z][A-Z0-9_]*$/;

/**
 * Secrets tab. Lists existing secret references (name + KMS ref +
 * last-rotated timestamp) and lets editors add new ones or trigger a
 * rotation. Secret values are never fetched into the browser — the
 * UI deliberately renders only opaque KMS pointers.
 */
export function SecretsList({
  agentId,
  initialSecrets,
  addSecret = defaultAddAgentSecret,
  rotateSecret = defaultRotateAgentSecret,
}: SecretsListProps) {
  const [secrets, setSecrets] = useState(initialSecrets);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [secretRef, setSecretRef] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [pendingRotateId, setPendingRotateId] = useState<string | null>(null);
  const [toast, setToast] = useState<Toast>(null);

  const nameId = useId();
  const refId = useId();

  useEffect(() => setSecrets(initialSecrets), [initialSecrets]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 4000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const trimmedName = name.trim();
  const trimmedRef = secretRef.trim();
  const nameValid = trimmedName.length > 0 && NAME_RE.test(trimmedName);
  const duplicate = secrets.some((s) => s.name === trimmedName);
  const refValid = trimmedRef.length > 0;
  const canSubmit =
    nameValid && refValid && !duplicate && !submitting;

  function reset() {
    setName("");
    setSecretRef("");
    setFormError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!nameValid) {
      setFormError(SECRET_NAME_HINT);
      return;
    }
    if (duplicate) {
      setFormError(`A secret named ${trimmedName} already exists.`);
      return;
    }
    if (!refValid) {
      setFormError("Secret ref is required.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    try {
      const created = await addSecret({
        agentId,
        name: trimmedName,
        ref: trimmedRef,
      });
      setSecrets((prev) => [...prev, created]);
      setOpen(false);
      reset();
      setToast({
        kind: "success",
        message: `Added secret ${created.name}.`,
      });
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to add secret.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRotate(secret: AgentSecret) {
    setPendingRotateId(secret.id);
    try {
      const result = await rotateSecret({ secretId: secret.id });
      setSecrets((prev) =>
        prev.map((s) =>
          s.id === secret.id ? { ...s, rotated_at: result.rotated_at } : s,
        ),
      );
      setToast({
        kind: "success",
        message: `Rotated ${secret.name}.`,
      });
    } catch (err) {
      setToast({
        kind: "error",
        message:
          err instanceof Error
            ? `Rotate failed: ${err.message}`
            : "Rotate failed.",
      });
    } finally {
      setPendingRotateId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4" data-testid="secrets-pane">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">Secrets</h2>
        <button
          type="button"
          onClick={() => setOpen(true)}
          data-testid="add-secret-button"
          className="rounded-md border px-3 py-1.5 text-sm font-medium"
        >
          Add secret
        </button>
      </div>
      {secrets.length === 0 ? (
        <p
          className="text-sm text-muted-foreground"
          data-testid="secrets-empty"
        >
          No secrets attached. Add one to expose it to this agent at runtime.
        </p>
      ) : (
        <ul
          className="divide-y divide-border rounded-lg border"
          data-testid="secrets-list"
        >
          {secrets.map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between gap-4 p-4"
              data-testid={`secret-row-${s.name}`}
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium">{s.name}</span>
                <code
                  className="text-xs text-muted-foreground"
                  data-testid={`secret-ref-${s.name}`}
                >
                  {s.ref}
                </code>
                <span
                  className="text-xs text-muted-foreground"
                  data-testid={`secret-rotated-${s.name}`}
                >
                  {s.rotated_at
                    ? `Rotated ${new Date(s.rotated_at).toLocaleString()}`
                    : "Never rotated"}
                </span>
              </div>
              <button
                type="button"
                onClick={() => handleRotate(s)}
                disabled={pendingRotateId === s.id}
                data-testid={`secret-rotate-${s.name}`}
                className="rounded-md border px-2 py-1 text-xs font-medium disabled:opacity-50"
              >
                {pendingRotateId === s.id ? "Rotating…" : "Rotate"}
              </button>
            </li>
          ))}
        </ul>
      )}
      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          data-testid="add-secret-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        >
          <form
            onSubmit={handleSubmit}
            className="flex w-full max-w-md flex-col gap-3 rounded-lg bg-background p-6 shadow"
          >
            <h3 className="text-base font-semibold">Add secret</h3>
            <div className="flex flex-col gap-1">
              <label htmlFor={nameId} className="text-sm font-medium">
                Name
              </label>
              <input
                id={nameId}
                value={name}
                onChange={(e) => setName(e.target.value.toUpperCase())}
                data-testid="add-secret-name"
                className="rounded-md border px-2 py-1 text-sm"
                placeholder="OPENAI_API_KEY"
                autoFocus
              />
              <span className="text-xs text-muted-foreground">
                {SECRET_NAME_HINT}
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor={refId} className="text-sm font-medium">
                KMS reference
              </label>
              <input
                id={refId}
                value={secretRef}
                onChange={(e) => setSecretRef(e.target.value)}
                data-testid="add-secret-ref"
                className="rounded-md border px-2 py-1 text-sm"
                placeholder="kms://prod/openai-key"
              />
              <span className="text-xs text-muted-foreground">
                We never store the value. Provide the KMS pointer only.
              </span>
            </div>
            {formError ? (
              <p
                className="text-xs text-red-600"
                data-testid="add-secret-error"
              >
                {formError}
              </p>
            ) : null}
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  reset();
                }}
                data-testid="add-secret-cancel"
                className="rounded-md border px-3 py-1.5 text-sm"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                data-testid="add-secret-submit"
                className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground disabled:opacity-50"
              >
                {submitting ? "Adding…" : "Add"}
              </button>
            </div>
          </form>
        </div>
      ) : null}
      {toast ? (
        <div
          role="status"
          aria-live="polite"
          data-testid={`secret-toast-${toast.kind}`}
          className={
            "fixed bottom-4 right-4 z-50 rounded-md px-3 py-2 text-sm shadow " +
            (toast.kind === "success"
              ? "bg-green-600 text-white"
              : "bg-red-600 text-white")
          }
        >
          {toast.message}
        </div>
      ) : null}
    </div>
  );
}
