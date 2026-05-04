"use client";

import { useId, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  type AgentSummary,
  type CreateAgentInput,
  createAgent as defaultCreateAgent,
} from "@/lib/cp-api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$/;

export interface NewAgentModalProps {
  /** Slugs already used in this workspace; submit is blocked if name collides. */
  existingSlugs: string[];
  /** Override for tests so we don't hit the real cp-api. */
  createAgent?: (input: CreateAgentInput) => Promise<AgentSummary>;
}

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "error"; message: string };

/**
 * "New agent" modal. Renders a trigger button; opening the dialog shows
 * a form (name, slug, description). On submit we POST to cp-api and
 * navigate to /agents/{id}. Slug uniqueness is validated client-side
 * against the list passed in by the agents index page so we surface
 * conflicts before the round-trip.
 */
export function NewAgentModal({
  existingSlugs,
  createAgent = defaultCreateAgent,
}: NewAgentModalProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const slugErrorId = useId();
  const formErrorId = useId();

  const trimmedName = name.trim();
  const trimmedSlug = slug.trim();
  const slugFormatBad =
    trimmedSlug.length > 0 && !SLUG_RE.test(trimmedSlug);
  const slugTaken =
    trimmedSlug.length > 0 && existingSlugs.includes(trimmedSlug);
  const slugError = slugFormatBad
    ? "Use 1–40 lowercase letters, numbers, or hyphens."
    : slugTaken
    ? "An agent with this slug already exists in the workspace."
    : null;
  const canSubmit =
    trimmedName.length > 0 &&
    trimmedSlug.length > 0 &&
    !slugError &&
    status.kind !== "submitting";

  function reset() {
    setName("");
    setSlug("");
    setDescription("");
    setStatus({ kind: "idle" });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setStatus({ kind: "submitting" });
    try {
      const created = await createAgent({
        name: trimmedName,
        slug: trimmedSlug,
        ...(description.trim() ? { description: description.trim() } : {}),
      });
      setOpen(false);
      reset();
      router.push(`/agents/${created.id}`);
    } catch (err) {
      setStatus({
        kind: "error",
        message: err instanceof Error ? err.message : "Failed to create agent.",
      });
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen && status.kind !== "submitting") {
          reset();
        }
      }}
    >
      <DialogTrigger asChild>
        <button
          type="button"
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          data-testid="new-agent-button"
        >
          New agent
        </button>
      </DialogTrigger>
      <DialogContent
        aria-label="Create agent"
        data-testid="new-agent-modal"
        className="max-w-md"
      >
        <form
          onSubmit={handleSubmit}
          className="flex w-full flex-col gap-4"
          noValidate
        >
          <DialogHeader>
            <DialogTitle>Create agent</DialogTitle>
          </DialogHeader>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Name</span>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              data-testid="new-agent-name"
              className="rounded-md border px-2 py-1"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Slug</span>
            <input
              type="text"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              required
              pattern="[a-z0-9][a-z0-9-]{0,39}"
              aria-invalid={slugError ? true : undefined}
              aria-describedby={slugError ? slugErrorId : undefined}
              data-testid="new-agent-slug"
              className="rounded-md border px-2 py-1 font-mono"
            />
            {slugError ? (
              <span
                id={slugErrorId}
                role="alert"
                data-testid="new-agent-slug-error"
                className="text-xs text-red-600"
              >
                {slugError}
              </span>
            ) : null}
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium">Description</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              data-testid="new-agent-description"
              className="rounded-md border px-2 py-1"
            />
          </label>
          {status.kind === "error" ? (
            <p
              id={formErrorId}
              role="alert"
              data-testid="new-agent-error"
              className="text-sm text-red-600"
            >
              {status.message}
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="rounded-md border px-3 py-1 text-sm"
              data-testid="new-agent-cancel"
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!canSubmit}
              data-testid="new-agent-submit"
              className="rounded-md bg-primary px-3 py-1 text-sm font-medium text-primary-foreground disabled:opacity-50"
            >
              {status.kind === "submitting" ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
