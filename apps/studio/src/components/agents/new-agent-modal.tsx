"use client";

import { useId, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import {
  EMPTY_COMMITMENT_BODY,
  type CommitmentBody,
  commitmentFieldLabel,
  missingCommitmentFields,
  parseList,
} from "@/lib/agent-commitment";
import {
  createAgentIntake as defaultCreateAgentIntake,
  type AgentIntakeArtifactInput,
  type AgentIntakeCreateInput,
  type AgentIntakeCreateResult,
  type AgentIntakePath,
} from "@/lib/agent-intake";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const SLUG_RE = /^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$/;

const APPROVED_TEMPLATES: Array<{
  id: string;
  label: string;
  summary: string;
  contract: Partial<CommitmentBody>;
  capabilities: string[];
  artifact: AgentIntakeArtifactInput;
}> = [
  {
    id: "tmpl_support_agent",
    label: "Enterprise support agent",
    summary: "Policy-grounded web, WhatsApp, and email support.",
    contract: {
      business_responsibility:
        "Resolve support questions using approved policy and escalation paths.",
      target_users: "Enterprise customers and support operators.",
      worst_case_failure:
        "Promises refunds, legal positions, or account actions outside approved policy.",
      channels: ["web", "whatsapp", "email"],
      systems_touched: ["crm", "billing api"],
      regions: ["us-east-1", "eu-west-2"],
      languages: ["en"],
      success_metric: "95% eval pass rate before canary.",
      compliance_domain: "SOC2 support operations",
      expected_volume: "10k turns per month",
      budget_target: "$0.08 per resolved turn",
      out_of_scope: "Legal advice and refunds above policy.",
      escalation_policy:
        "Escalate policy conflicts, legal threats, and refund exceptions to the support lead.",
    },
    capabilities: [
      "Answer policy-backed support questions",
      "Escalate billing and legal risk",
      "Preserve channel formatting",
    ],
    artifact: {
      name: "enterprise-support-template.md",
      kind: "runbook",
      text: "Use approved policy. Escalate legal threats. Never refund outside policy.",
      source_ref: "template/tmpl_support_agent/runbook",
    },
  },
  {
    id: "tmpl_voice_receptionist",
    label: "Voice receptionist",
    summary: "Voice and SMS receptionist with handoff-safe routing.",
    contract: {
      business_responsibility:
        "Handle inbound calls, answer basic questions, and route callers to the right team.",
      target_users: "Prospects, customers, and operators calling the business.",
      worst_case_failure:
        "Books, cancels, or promises appointments without confirmation.",
      channels: ["voice", "sms"],
      systems_touched: ["calendar", "crm"],
      regions: ["us-east-1"],
      languages: ["en"],
      success_metric: "90% successful route or callback capture.",
      compliance_domain: "Customer communications",
      expected_volume: "3k calls per month",
      budget_target: "$0.12 per handled call",
      out_of_scope: "Medical, legal, or financial advice.",
      escalation_policy:
        "Escalate urgent, regulated, or frustrated callers to the human queue.",
    },
    capabilities: [
      "Answer front-desk questions",
      "Schedule handoffs",
      "Collect callback context",
    ],
    artifact: {
      name: "voice-receptionist-template.md",
      kind: "runbook",
      text: "Confirm identity before scheduling. Keep speech concise. Escalate urgent callers.",
      source_ref: "template/tmpl_voice_receptionist/runbook",
    },
  },
];

export interface NewAgentModalProps {
  /** Slugs already used in this workspace; submit is blocked if name collides. */
  existingSlugs: string[];
  /** Active workspace receiving the governed intake. */
  workspaceId?: string | null | undefined;
  /** Override for tests so the wizard doesn't hit the real cp-api. */
  createAgentIntake?: (
    workspaceId: string,
    input: AgentIntakeCreateInput,
  ) => Promise<AgentIntakeCreateResult>;
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
  workspaceId,
  createAgentIntake = defaultCreateAgentIntake,
}: NewAgentModalProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [creationPath, setCreationPath] =
    useState<AgentIntakePath>("business_intent");
  const [templateId, setTemplateId] = useState(APPROVED_TEMPLATES[0]!.id);
  const [contract, setContract] = useState<CommitmentBody>({
    ...EMPTY_COMMITMENT_BODY,
    channels: ["web"],
    languages: ["en"],
  });
  const [capabilities, setCapabilities] = useState<string[]>([
    "Answer from knowledge",
  ]);
  const [artifact, setArtifact] = useState<AgentIntakeArtifactInput>({
    name: "",
    kind: "transcript",
    text: "",
    source_ref: "",
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
  const effectiveWorkspaceId = workspaceId?.trim() || "local-workspace";
  const canSubmit =
    trimmedName.length > 0 &&
    trimmedSlug.length > 0 &&
    missingContract.length === 0 &&
    !slugError &&
    status.kind !== "submitting";

  function reset() {
    setStep(0);
    setName("");
    setSlug("");
    setCreationPath("business_intent");
    setTemplateId(APPROVED_TEMPLATES[0]!.id);
    setContract({
      ...EMPTY_COMMITMENT_BODY,
      channels: ["web"],
      languages: ["en"],
    });
    setCapabilities(["Answer from knowledge"]);
    setArtifact({ name: "", kind: "transcript", text: "", source_ref: "" });
    setStatus({ kind: "idle" });
  }

  function updateContract<K extends keyof CommitmentBody>(
    field: K,
    value: CommitmentBody[K],
  ) {
    setContract((current) => ({ ...current, [field]: value }));
  }

  function toggleCapability(capability: string) {
    setCapabilities((current) =>
      current.includes(capability)
        ? current.filter((item) => item !== capability)
        : [...current, capability],
    );
  }

  function applyTemplate(nextTemplateId: string) {
    const template =
      APPROVED_TEMPLATES.find((item) => item.id === nextTemplateId) ??
      APPROVED_TEMPLATES[0]!;
    setTemplateId(template.id);
    setContract((current) => ({
      ...current,
      ...template.contract,
      owner_user_id: current.owner_user_id,
      backup_owner_user_id: current.backup_owner_user_id,
    }));
    setCapabilities(template.capabilities);
    setArtifact(template.artifact);
  }

  function chooseCreationPath(path: AgentIntakePath) {
    setCreationPath(path);
    if (path === "enterprise_template") {
      applyTemplate(templateId);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) return;
    setStatus({ kind: "submitting" });
    try {
      const artifacts =
        artifact.name.trim() ||
        artifact.text.trim() ||
        artifact.source_ref.trim()
          ? [
              {
                ...artifact,
                name: artifact.name.trim() || "intake-notes",
              },
            ]
          : [];
      const intakeInput: AgentIntakeCreateInput = {
        agent_name: trimmedName,
        slug: trimmedSlug,
        creation_path: creationPath,
        contract,
        capabilities,
        artifacts,
      };
      if (creationPath === "enterprise_template") {
        intakeInput.template_id = templateId;
      }
      const result = await createAgentIntake(effectiveWorkspaceId, intakeInput);
      setOpen(false);
      reset();
      router.push(`/agents/${result.agent.id}?intake=${result.id}`);
    } catch (err) {
      setStatus({
        kind: "error",
        message:
          err instanceof Error
            ? err.message
            : "Failed to create governed agent intake.",
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
            <DialogTitle>Create governed agent intake</DialogTitle>
            <DialogDescription>
              Start from business responsibility, artifacts, channels, and risk.
              Studio creates the draft agent, contract, sandbox channels, mock
              tool contracts, memory policy, and starter evals together.
            </DialogDescription>
          </DialogHeader>

          <ol
            className="grid gap-2 text-xs md:grid-cols-4"
            aria-label="Agent contract wizard steps"
          >
            {["Mission", "Boundaries", "Capabilities", "Readiness"].map(
              (label, index) => (
                <li key={label}>
                  <button
                    type="button"
                    onClick={() => setStep(index)}
                    aria-current={step === index ? "step" : undefined}
                    className={[
                      "w-full rounded-md border px-3 py-2 text-left transition-colors",
                      step === index
                        ? "border-primary bg-primary/10 text-foreground"
                        : "bg-background text-muted-foreground hover:bg-muted/50",
                    ].join(" ")}
                  >
                    <span className="block font-semibold">{label}</span>
                    <span>Step {index + 1}</span>
                  </button>
                </li>
              ),
            )}
          </ol>

          <fieldset className="grid gap-3 rounded-md border bg-muted/30 p-4">
            <legend className="px-1 text-sm font-medium">Creation path</legend>
            <div className="grid gap-2 md:grid-cols-3">
              {[
                {
                  value: "business_intent",
                  label: "Business intent",
                  detail: "Describe the job and seed a governed draft.",
                },
                {
                  value: "legacy_import",
                  label: "Legacy import",
                  detail:
                    "Use Botpress, Dialogflow, Rasa, or transcript input.",
                },
                {
                  value: "enterprise_template",
                  label: "Enterprise template",
                  detail: "Clone an approved internal pattern.",
                },
              ].map((option) => (
                <label
                  key={option.value}
                  className="flex cursor-pointer gap-2 rounded-md border bg-background p-3 text-sm"
                >
                  <input
                    type="radio"
                    name="creation-path"
                    value={option.value}
                    checked={creationPath === option.value}
                    onChange={(event) =>
                      chooseCreationPath(event.target.value as AgentIntakePath)
                    }
                  />
                  <span>
                    <span className="block font-medium">{option.label}</span>
                    <span className="text-muted-foreground">
                      {option.detail}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          {creationPath === "enterprise_template" ? (
            <fieldset className="grid gap-3 rounded-md border border-info/30 bg-info/5 p-4">
              <legend className="px-1 text-sm font-medium">
                Approved template
              </legend>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Template</span>
                <select
                  value={templateId}
                  onChange={(event) => applyTemplate(event.target.value)}
                  data-testid="new-agent-template"
                  className="rounded-md border bg-background px-2 py-1"
                >
                  {APPROVED_TEMPLATES.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.label}
                    </option>
                  ))}
                </select>
              </label>
              <p className="text-xs text-muted-foreground">
                {
                  APPROVED_TEMPLATES.find(
                    (template) => template.id === templateId,
                  )?.summary
                }
              </p>
            </fieldset>
          ) : null}

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
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Success metric</span>
                <input
                  value={contract.success_metric}
                  onChange={(e) =>
                    updateContract("success_metric", e.target.value)
                  }
                  data-testid="new-agent-success-metric"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Compliance domain</span>
                <input
                  value={contract.compliance_domain}
                  onChange={(e) =>
                    updateContract("compliance_domain", e.target.value)
                  }
                  data-testid="new-agent-compliance-domain"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Expected volume</span>
                <input
                  value={contract.expected_volume}
                  onChange={(e) =>
                    updateContract("expected_volume", e.target.value)
                  }
                  data-testid="new-agent-expected-volume"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Budget target</span>
                <input
                  value={contract.budget_target}
                  onChange={(e) =>
                    updateContract("budget_target", e.target.value)
                  }
                  data-testid="new-agent-budget-target"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm md:col-span-2">
                <span className="font-medium">Escalation policy</span>
                <textarea
                  value={contract.escalation_policy}
                  onChange={(e) =>
                    updateContract("escalation_policy", e.target.value)
                  }
                  rows={2}
                  data-testid="new-agent-escalation-policy"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
            </div>
          </div>

          <fieldset className="grid gap-3 rounded-md border bg-muted/30 p-4">
            <legend className="px-1 text-sm font-medium">
              Capabilities to seed
            </legend>
            <div className="grid gap-2 md:grid-cols-2">
              {[
                "Answer from knowledge",
                "Search customer/account data",
                "Create or update records",
                "Trigger workflows",
                "Handoff to human",
                "Send notifications",
                "Voice interaction",
                "Channel-specific messaging",
              ].map((capability) => (
                <label
                  key={capability}
                  className="flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={capabilities.includes(capability)}
                    onChange={() => toggleCapability(capability)}
                  />
                  <span>{capability}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="grid gap-3 rounded-md border bg-muted/30 p-4">
            <legend className="px-1 text-sm font-medium">
              Artifact intake
            </legend>
            <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_12rem]">
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Artifact name or URL</span>
                <input
                  value={artifact.name}
                  onChange={(e) =>
                    setArtifact((current) => ({
                      ...current,
                      name: e.target.value,
                    }))
                  }
                  placeholder="refund_policy.pdf, botpress-export.bpz, OpenAPI URL"
                  data-testid="new-agent-artifact-name"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Kind</span>
                <select
                  value={artifact.kind}
                  onChange={(e) =>
                    setArtifact((current) => ({
                      ...current,
                      kind: e.target.value as AgentIntakeArtifactInput["kind"],
                    }))
                  }
                  data-testid="new-agent-artifact-kind"
                  className="rounded-md border bg-background px-2 py-1"
                >
                  {[
                    "pdf",
                    "faq",
                    "runbook",
                    "transcript",
                    "botpress_export",
                    "dialogflow_export",
                    "rasa_export",
                    "openapi",
                    "postman",
                    "curl",
                    "devtools_fetch",
                    "other",
                  ].map((kind) => (
                    <option key={kind} value={kind}>
                      {kind.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm md:col-span-2">
                <span className="font-medium">Paste content or notes</span>
                <textarea
                  value={artifact.text}
                  onChange={(e) =>
                    setArtifact((current) => ({
                      ...current,
                      text: e.target.value,
                    }))
                  }
                  rows={4}
                  placeholder="Paste transcript excerpts, policy text, cURL, Copy as fetch, or migration notes. Credentials can stay mocked."
                  data-testid="new-agent-artifact-text"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
            </div>
          </fieldset>

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
          <div className="grid gap-2 rounded-md border bg-card p-3 text-xs text-muted-foreground md:grid-cols-3">
            <span>
              Creates <strong className="text-foreground">Commitment</strong> v1
              from this contract.
            </span>
            <span>
              Seeds <strong className="text-foreground">channels/tools</strong>{" "}
              in sandbox or mock mode.
            </span>
            <span>
              Adds <strong className="text-foreground">starter evals</strong>{" "}
              before any deploy action exists.
            </span>
          </div>
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
              {status.kind === "submitting"
                ? "Analyzing intake…"
                : "Create governed draft"}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
