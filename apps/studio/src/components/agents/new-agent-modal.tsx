"use client";

import { useId, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  type AgentSummary,
  type CreateAgentInput,
  createAgent as defaultCreateAgent,
} from "@/lib/cp-api";
import {
  EMPTY_COMMITMENT_BODY,
  type CommitmentBody,
  type CommitmentDocument,
  type CommitmentDraftInput,
  commitmentFieldLabel,
  missingCommitmentFields,
  parseList,
  saveCommitmentDraft as defaultSaveCommitmentDraft,
} from "@/lib/agent-commitment";
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
  /** Override for tests so the creation wizard can seed the contract without cp-api. */
  saveCommitmentDraft?: (
    agentId: string,
    input: CommitmentDraftInput,
  ) => Promise<CommitmentDocument>;
}

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "error"; message: string };

/**
 * "New agent" modal. Creation starts with the Agent Contract, not an
 * empty shell. The modal captures the minimum enterprise commitment,
 * creates the agent, saves the first Commitment Document draft, then
 * lands the builder on the contract page to finish acceptance.
 */
export function NewAgentModal({
  existingSlugs,
  createAgent = defaultCreateAgent,
  saveCommitmentDraft = defaultSaveCommitmentDraft,
}: NewAgentModalProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [contract, setContract] = useState<CommitmentBody>({
    ...EMPTY_COMMITMENT_BODY,
    channels: ["web"],
    languages: ["en"],
  });
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const slugErrorId = useId();
  const formErrorId = useId();

  const trimmedName = name.trim();
  const trimmedSlug = slug.trim();
  const slugFormatBad = trimmedSlug.length > 0 && !SLUG_RE.test(trimmedSlug);
  const slugTaken =
    trimmedSlug.length > 0 && existingSlugs.includes(trimmedSlug);
  const slugError = slugFormatBad
    ? "Use 1–40 lowercase letters, numbers, or hyphens."
    : slugTaken
      ? "An agent with this slug already exists in the workspace."
      : null;
  const missingContract = missingCommitmentFields(contract);
  const canSubmit =
    trimmedName.length > 0 &&
    trimmedSlug.length > 0 &&
    missingContract.length === 0 &&
    !slugError &&
    status.kind !== "submitting";

  function reset() {
    setName("");
    setSlug("");
    setContract({
      ...EMPTY_COMMITMENT_BODY,
      channels: ["web"],
      languages: ["en"],
    });
    setStatus({ kind: "idle" });
  }

  function updateContract<K extends keyof CommitmentBody>(
    field: K,
    value: CommitmentBody[K],
  ) {
    setContract((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setStatus({ kind: "submitting" });
    try {
      const created = await createAgent({
        name: trimmedName,
        slug: trimmedSlug,
        description: contract.business_responsibility.trim(),
      });
      await saveCommitmentDraft(created.id, {
        body: contract,
        created_from: "studio:new_agent_wizard",
      });
      setOpen(false);
      reset();
      router.push(`/agents/${created.id}/contract`);
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
        className="max-h-[90vh] max-w-3xl overflow-y-auto"
      >
        <form
          onSubmit={handleSubmit}
          className="flex w-full flex-col gap-5"
          noValidate
        >
          <DialogHeader>
            <DialogTitle>Create agent contract</DialogTitle>
            <DialogDescription>
              Define what this agent is accountable for before any behavior,
              tools, channels, or deployments are configured.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 rounded-md border bg-muted/30 p-4 md:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">Name</span>
              <input
                autoFocus
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                data-testid="new-agent-name"
                className="rounded-md border bg-background px-2 py-1"
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
                className="rounded-md border bg-background px-2 py-1 font-mono"
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
          </div>

          <div className="grid gap-4">
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium">Business responsibility</span>
              <textarea
                value={contract.business_responsibility}
                onChange={(e) =>
                  updateContract("business_responsibility", e.target.value)
                }
                rows={3}
                data-testid="new-agent-business-responsibility"
                className="rounded-md border bg-background px-2 py-1"
              />
            </label>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Target users</span>
                <textarea
                  value={contract.target_users}
                  onChange={(e) =>
                    updateContract("target_users", e.target.value)
                  }
                  rows={3}
                  data-testid="new-agent-target-users"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Worst-case failure</span>
                <textarea
                  value={contract.worst_case_failure}
                  onChange={(e) =>
                    updateContract("worst_case_failure", e.target.value)
                  }
                  rows={3}
                  data-testid="new-agent-worst-case-failure"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Owner</span>
                <input
                  value={contract.owner_user_id}
                  onChange={(e) =>
                    updateContract("owner_user_id", e.target.value)
                  }
                  data-testid="new-agent-owner"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Backup owner</span>
                <input
                  value={contract.backup_owner_user_id}
                  onChange={(e) =>
                    updateContract("backup_owner_user_id", e.target.value)
                  }
                  data-testid="new-agent-backup-owner"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Channels</span>
                <textarea
                  value={contract.channels.join(", ")}
                  onChange={(e) =>
                    updateContract("channels", parseList(e.target.value))
                  }
                  rows={2}
                  data-testid="new-agent-channels"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Systems touched</span>
                <textarea
                  value={contract.systems_touched.join(", ")}
                  onChange={(e) =>
                    updateContract("systems_touched", parseList(e.target.value))
                  }
                  rows={2}
                  data-testid="new-agent-systems"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Regions</span>
                <textarea
                  value={contract.regions.join(", ")}
                  onChange={(e) =>
                    updateContract("regions", parseList(e.target.value))
                  }
                  rows={2}
                  data-testid="new-agent-regions"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Languages</span>
                <textarea
                  value={contract.languages.join(", ")}
                  onChange={(e) =>
                    updateContract("languages", parseList(e.target.value))
                  }
                  rows={2}
                  data-testid="new-agent-languages"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
            </div>
          </div>

          {missingContract.length > 0 ? (
            <p
              className="rounded-md border border-warning/50 bg-warning/10 px-3 py-2 text-xs text-muted-foreground"
              data-testid="new-agent-contract-gaps"
            >
              Missing contract fields:{" "}
              {missingContract.map(commitmentFieldLabel).join(", ")}
            </p>
          ) : null}
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
              {status.kind === "submitting" ? "Creating…" : "Create contract"}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
