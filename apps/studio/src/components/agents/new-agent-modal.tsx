"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { useRouter } from "next/navigation";

import {
  EMPTY_COMMITMENT_BODY,
  type CommitmentBody,
  commitmentFieldLabel,
  missingCommitmentFields,
  parseList,
} from "@/lib/agent-commitment";
import {
  LOCAL_AGENT_INTAKE_TEMPLATES,
  continueAgentIntakeManually as defaultContinueAgentIntakeManually,
  createAgentIntake as defaultCreateAgentIntake,
  listAgentIntakeTemplates as defaultListAgentIntakeTemplates,
  retryAgentIntakeGeneration as defaultRetryAgentIntakeGeneration,
  type AgentIntakeArtifactInput,
  type AgentIntakeCreateInput,
  type AgentIntakeCreateResult,
  type AgentIntakePath,
  type AgentIntakeRecoveryResult,
  type AgentIntakeTemplate,
  type AgentIntakeTemplateList,
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

const WIZARD_STEPS = [
  {
    id: "mission",
    label: "Mission",
    caption: "Responsibility, users, and ownership",
  },
  {
    id: "boundaries",
    label: "Boundaries",
    caption: "Risk, escalation, and operating limits",
  },
  {
    id: "capabilities",
    label: "Capabilities",
    caption: "What the agent may do",
  },
  {
    id: "knowledge_tools",
    label: "Knowledge & tools",
    caption: "Sources, systems, mocks, and imports",
  },
  {
    id: "channels",
    label: "Channels",
    caption: "Where it will run",
  },
  {
    id: "generated_tests",
    label: "Generated tests",
    caption: "Initial proof obligations",
  },
  {
    id: "readiness",
    label: "Readiness",
    caption: "What will be created",
  },
] as const;

const CREATION_PATHS: Array<{
  value: AgentIntakePath;
  label: string;
  detail: string;
}> = [
  {
    value: "business_intent",
    label: "Business intent",
    detail: "Describe the job and seed a governed draft.",
  },
  {
    value: "legacy_import",
    label: "Legacy import",
    detail: "Use Botpress, Dialogflow, Rasa, transcripts, or API artifacts.",
  },
  {
    value: "enterprise_template",
    label: "Enterprise template",
    detail: "Clone an approved internal pattern.",
  },
];

const CAPABILITY_OPTIONS = [
  "Answer from knowledge",
  "Create or update records",
  "Search customer/account data",
  "Trigger workflows",
  "Handoff to human",
  "Send notifications",
  "Voice interaction",
  "Channel-specific messaging",
];

const CHANNEL_OPTIONS = [
  { id: "web", label: "Web chat", detail: "Initial sandbox channel" },
  { id: "whatsapp", label: "WhatsApp", detail: "Template + opt-in ready" },
  { id: "telegram", label: "Telegram", detail: "Bot token binding" },
  { id: "slack", label: "Slack", detail: "Workspace app binding" },
  { id: "teams", label: "Teams", detail: "Tenant app binding" },
  { id: "sms", label: "SMS", detail: "Carrier-safe text channel" },
  { id: "email", label: "Email", detail: "Async inbox channel" },
  { id: "voice", label: "Voice", detail: "Telephony, ASR, and TTS" },
  { id: "webhook", label: "Webhook/API", detail: "Programmatic channel" },
];

const ARTIFACT_KIND_OPTIONS: AgentIntakeArtifactInput["kind"][] = [
  "pdf",
  "faq",
  "runbook",
  "transcript",
  "botpress_export",
  "dialogflow_export",
  "rasa_export",
  "zendesk_export",
  "intercom_export",
  "openapi",
  "postman",
  "curl",
  "devtools_fetch",
  "other",
];

const INTAKE_JOBS = [
  "parse_artifacts",
  "extract_intents",
  "cluster_transcripts",
  "detect_contradictions",
  "detect_sensitive_data",
  "infer_tools",
  "infer_channels",
  "draft_commitment_document",
  "draft_agent_plan",
];

const DRAFT_STORAGE_VERSION = 1;

type WorkspaceRole = "owner" | "admin" | "member" | "viewer";
type WizardStepId = (typeof WIZARD_STEPS)[number]["id"];

type NewAgentDraft = {
  version: typeof DRAFT_STORAGE_VERSION;
  step: number;
  name: string;
  slug: string;
  creationPath: AgentIntakePath;
  templateId: string;
  contract: CommitmentBody;
  capabilities: string[];
  artifact: AgentIntakeArtifactInput;
  savedAt: string;
};

type ContractListField =
  | "channels"
  | "systems_touched"
  | "regions"
  | "languages";

export interface NewAgentModalProps {
  /** Slugs already used in this workspace; submit is blocked if name collides. */
  existingSlugs: string[];
  /** Active workspace receiving the governed intake. */
  workspaceId?: string | null | undefined;
  /** Workspace display name for clearer degraded/permission copy. */
  workspaceName?: string | null | undefined;
  /** Caller role in the active workspace. Owners/admins can create agents. */
  workspaceRole?: WorkspaceRole | null | undefined;
  /** Override for tests so the wizard doesn't hit the real cp-api. */
  createAgentIntake?: (
    workspaceId: string,
    input: AgentIntakeCreateInput,
  ) => Promise<AgentIntakeCreateResult>;
  /** Retry draft generation after the backend has persisted a failed intake. */
  retryAgentIntakeGeneration?: (
    workspaceId: string,
    intakeId: string,
  ) => Promise<AgentIntakeRecoveryResult>;
  /** Continue into the Workbench with the agent + Commitment only. */
  continueAgentIntakeManually?: (
    workspaceId: string,
    intakeId: string,
    notes?: string,
  ) => Promise<AgentIntakeRecoveryResult>;
  /** Override for tests so template catalog loading can stay deterministic. */
  listAgentIntakeTemplates?: (
    workspaceId: string,
  ) => Promise<AgentIntakeTemplateList>;
}

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "recoverable_failure"; intake: AgentIntakeRecoveryResult }
  | { kind: "recovering"; action: "retry" | "manual" }
  | { kind: "error"; message: string };

function canCreateWithRole(role: WorkspaceRole | null | undefined): boolean {
  return (
    role === undefined || role === null || role === "owner" || role === "admin"
  );
}

function panelClass(active: boolean): string {
  return active ? "grid gap-5" : "hidden";
}

function draftKeyForWorkspace(workspaceId: string): string {
  return `loop:new-agent-draft:v${DRAFT_STORAGE_VERSION}:${workspaceId}`;
}

function isDraftRecord(value: unknown): value is NewAgentDraft {
  if (!value || typeof value !== "object") return false;
  const record = value as Partial<NewAgentDraft>;
  return (
    record.version === DRAFT_STORAGE_VERSION &&
    typeof record.name === "string" &&
    typeof record.slug === "string" &&
    typeof record.creationPath === "string" &&
    typeof record.templateId === "string" &&
    record.contract !== undefined &&
    Array.isArray(record.capabilities) &&
    record.artifact !== undefined
  );
}

function createErrorMessage(error: unknown): string {
  const message =
    error instanceof Error
      ? error.message
      : "Failed to create governed agent intake.";
  const status = message.match(/->\s*(\d{3})/)?.[1];
  if (status === "401" || status === "403") {
    return "You do not have permission to create agents in this workspace. Ask a workspace owner or admin for builder access.";
  }
  if (status === "404") {
    return "Workspace unavailable. Studio could not find the selected workspace, so no agent was created. Choose or create a workspace, then try again.";
  }
  if (status === "409") {
    return "An agent with this identity already exists. Change the slug or open the existing agent.";
  }
  if (status) {
    return `Control plane rejected the intake (${status}). The draft was not created; retry after the workspace service is healthy.`;
  }
  return message;
}

function hasArtifact(artifact: AgentIntakeArtifactInput): boolean {
  return Boolean(
    artifact.name.trim() || artifact.text.trim() || artifact.source_ref.trim(),
  );
}

function generatedTestNames(
  contract: CommitmentBody,
  capabilities: string[],
): string[] {
  const channelLabel =
    contract.channels.length > 0
      ? `Channel format holds for ${contract.channels.join(", ")}`
      : "Channel format is validated once a channel is selected";
  const toolLabel =
    contract.systems_touched.length > 0
      ? `Tool-use path covers ${contract.systems_touched.join(", ")}`
      : "Tool-use path waits for the first system or mock";
  return [
    "Happy path follows the mission",
    contract.escalation_policy.trim()
      ? "Escalation path follows the policy"
      : "Escalation path is generated after policy review",
    contract.worst_case_failure.trim()
      ? "Worst-case failure is refused or escalated"
      : "Refusal path waits for worst-case failure",
    toolLabel,
    capabilities.includes("Answer from knowledge")
      ? "Knowledge-grounding path requires citations"
      : "Knowledge-grounding path waits for knowledge capability",
    channelLabel,
  ];
}

function readinessItems(args: {
  name: string;
  slug: string;
  contract: CommitmentBody;
  capabilities: string[];
  artifact: AgentIntakeArtifactInput;
  slugError: string | null;
}) {
  const missing = missingCommitmentFields(args.contract);
  return [
    {
      label: "Agent identity named",
      ready: args.name.trim().length > 0 && args.slug.trim().length > 0,
    },
    { label: "Mission and owner defined", ready: missing.length === 0 },
    {
      label: "At least one capability selected",
      ready: args.capabilities.length > 0,
    },
    {
      label: "At least one sandbox channel selected",
      ready: args.contract.channels.length > 0,
    },
    {
      label: "Mock or live system placeholders identified",
      ready: args.contract.systems_touched.length > 0,
    },
    {
      label: "Starter evals can be generated",
      ready:
        args.contract.worst_case_failure.trim().length > 0 &&
        args.capabilities.length > 0,
    },
    { label: "Slug is available", ready: args.slugError === null },
    {
      label: "Optional artifacts attached",
      ready: hasArtifact(args.artifact),
      optional: true,
    },
  ];
}

/**
 * Creation starts with an Agent Contract, not an empty shell. The wizard
 * captures mission, boundaries, capabilities, knowledge, tools, channels, and
 * generated proof obligations before the backend creates the draft agent.
 */
export function NewAgentModal({
  existingSlugs,
  workspaceId,
  workspaceName,
  workspaceRole,
  createAgentIntake = defaultCreateAgentIntake,
  retryAgentIntakeGeneration = defaultRetryAgentIntakeGeneration,
  continueAgentIntakeManually = defaultContinueAgentIntakeManually,
  listAgentIntakeTemplates = defaultListAgentIntakeTemplates,
}: NewAgentModalProps) {
  const router = useRouter();
  const titleRef = useRef<HTMLHeadingElement>(null);
  const restoringDraftRef = useRef(false);
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [creationPath, setCreationPath] =
    useState<AgentIntakePath>("business_intent");
  const [templates, setTemplates] = useState<AgentIntakeTemplate[]>(
    LOCAL_AGENT_INTAKE_TEMPLATES,
  );
  const [templateCatalogState, setTemplateCatalogState] = useState<
    "approved" | "loading" | "example" | "unavailable"
  >("example");
  const [templateId, setTemplateId] = useState(
    LOCAL_AGENT_INTAKE_TEMPLATES[0]!.id,
  );
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
  const [draftRestored, setDraftRestored] = useState(false);
  const [draftSavedAt, setDraftSavedAt] = useState<string | null>(null);
  const slugErrorId = useId();
  const formErrorId = useId();

  const trimmedName = name.trim();
  const trimmedSlug = slug.trim();
  const slugFormatBad = trimmedSlug.length > 0 && !SLUG_RE.test(trimmedSlug);
  const slugTaken =
    trimmedSlug.length > 0 && existingSlugs.includes(trimmedSlug);
  const slugError = slugFormatBad
    ? "Use 1-40 lowercase letters, numbers, or hyphens."
    : slugTaken
      ? "An agent with this slug already exists in the workspace."
      : null;
  const missingContract = missingCommitmentFields(contract);
  const effectiveWorkspaceId = workspaceId?.trim() ?? "";
  const workspaceMissing = effectiveWorkspaceId.length === 0;
  const permissionBlocked =
    !workspaceMissing && !canCreateWithRole(workspaceRole);
  const canSubmit =
    !workspaceMissing &&
    !permissionBlocked &&
    (creationPath !== "enterprise_template" ||
      templateCatalogState === "approved") &&
    trimmedName.length > 0 &&
    trimmedSlug.length > 0 &&
    missingContract.length === 0 &&
    !slugError &&
    status.kind !== "submitting" &&
    status.kind !== "recovering";
  const shouldLoadTemplateCatalog =
    !workspaceMissing &&
    (listAgentIntakeTemplates !== defaultListAgentIntakeTemplates ||
      Boolean(
        process.env.NEXT_PUBLIC_LOOP_API_URL ||
          process.env.LOOP_CP_API_BASE_URL,
      ));
  const activeTemplate =
    templates.find((template) => template.id === templateId) ?? templates[0];
  const activeStep = WIZARD_STEPS[step] ?? WIZARD_STEPS[0]!;
  const generatedTests = useMemo(
    () => generatedTestNames(contract, capabilities),
    [contract, capabilities],
  );
  const readiness = readinessItems({
    name,
    slug,
    contract,
    capabilities,
    artifact,
    slugError,
  });
  const requiredReadiness = readiness.filter((item) => !item.optional);
  const readyCount = requiredReadiness.filter((item) => item.ready).length;
  const readinessScore = Math.round(
    (readyCount / Math.max(requiredReadiness.length, 1)) * 100,
  );
  const draftKey = effectiveWorkspaceId
    ? draftKeyForWorkspace(effectiveWorkspaceId)
    : null;
  const draftHasContent = useMemo(
    () =>
      Boolean(
        trimmedName ||
          trimmedSlug ||
          creationPath !== "business_intent" ||
          capabilities.join("|") !== "Answer from knowledge" ||
          artifact.name.trim() ||
          artifact.text.trim() ||
          artifact.source_ref.trim() ||
          contract.business_responsibility.trim() ||
          contract.target_users.trim() ||
          contract.owner_user_id.trim() ||
          contract.backup_owner_user_id.trim() ||
          contract.worst_case_failure.trim() ||
          contract.systems_touched.length > 0 ||
          contract.regions.length > 0 ||
          contract.channels.join("|") !== "web" ||
          contract.languages.join("|") !== "en" ||
          contract.success_metric.trim() ||
          contract.compliance_domain.trim() ||
          contract.expected_volume.trim() ||
          contract.launch_date.trim() ||
          contract.budget_target.trim() ||
          contract.out_of_scope.trim() ||
          contract.escalation_policy.trim(),
      ),
    [
      artifact.name,
      artifact.source_ref,
      artifact.text,
      capabilities,
      contract,
      creationPath,
      trimmedName,
      trimmedSlug,
    ],
  );
  const draftSnapshot = useMemo<NewAgentDraft>(
    () => ({
      version: DRAFT_STORAGE_VERSION,
      step,
      name,
      slug,
      creationPath,
      templateId,
      contract,
      capabilities,
      artifact,
      savedAt: new Date().toISOString(),
    }),
    [
      artifact,
      capabilities,
      contract,
      creationPath,
      name,
      slug,
      step,
      templateId,
    ],
  );

  useEffect(() => {
    if (!open) return;
    if (!shouldLoadTemplateCatalog) {
      setTemplates(LOCAL_AGENT_INTAKE_TEMPLATES);
      setTemplateId(LOCAL_AGENT_INTAKE_TEMPLATES[0]!.id);
      setTemplateCatalogState("example");
      return;
    }
    let cancelled = false;
    setTemplateCatalogState("loading");
    listAgentIntakeTemplates(effectiveWorkspaceId)
      .then((catalog) => {
        if (cancelled) return;
        const nextTemplates =
          catalog.items.length > 0
            ? catalog.items
            : LOCAL_AGENT_INTAKE_TEMPLATES;
        setTemplates(nextTemplates);
        setTemplateId((currentId) =>
          nextTemplates.some((template) => template.id === currentId)
            ? currentId
            : nextTemplates[0]!.id,
        );
        setTemplateCatalogState(
          catalog.items.length > 0 ? "approved" : "unavailable",
        );
      })
      .catch(() => {
        if (cancelled) return;
        setTemplates(LOCAL_AGENT_INTAKE_TEMPLATES);
        setTemplateId(LOCAL_AGENT_INTAKE_TEMPLATES[0]!.id);
        setTemplateCatalogState("example");
      });
    return () => {
      cancelled = true;
    };
  }, [
    effectiveWorkspaceId,
    listAgentIntakeTemplates,
    open,
    shouldLoadTemplateCatalog,
  ]);

  useEffect(() => {
    if (!open || !draftKey || typeof window === "undefined") return;
    const raw = window.localStorage.getItem(draftKey);
    if (!raw) {
      setDraftRestored(false);
      setDraftSavedAt(null);
      return;
    }
    try {
      const parsed = JSON.parse(raw) as unknown;
      if (!isDraftRecord(parsed)) return;
      restoringDraftRef.current = true;
      setStep(Math.min(Math.max(parsed.step, 0), WIZARD_STEPS.length - 1));
      setName(parsed.name);
      setSlug(parsed.slug);
      setCreationPath(parsed.creationPath);
      setTemplateId(parsed.templateId);
      setContract(parsed.contract);
      setCapabilities(parsed.capabilities);
      setArtifact(parsed.artifact);
      setDraftRestored(true);
      setDraftSavedAt(parsed.savedAt);
      if (parsed.creationPath !== "enterprise_template") {
        restoringDraftRef.current = false;
      }
    } catch {
      window.localStorage.removeItem(draftKey);
      setDraftRestored(false);
      setDraftSavedAt(null);
    }
  }, [draftKey, open]);

  useEffect(() => {
    if (!open || !draftKey || typeof window === "undefined") return;
    if (!draftHasContent) {
      window.localStorage.removeItem(draftKey);
      setDraftSavedAt(null);
      return;
    }
    const nextDraft = { ...draftSnapshot, savedAt: new Date().toISOString() };
    window.localStorage.setItem(draftKey, JSON.stringify(nextDraft));
    setDraftSavedAt(nextDraft.savedAt);
  }, [draftHasContent, draftKey, draftSnapshot, open]);

  function clearStoredDraft() {
    if (draftKey && typeof window !== "undefined") {
      window.localStorage.removeItem(draftKey);
    }
    setDraftRestored(false);
    setDraftSavedAt(null);
  }

  function reset({ clearDraft = false }: { clearDraft?: boolean } = {}) {
    setStep(0);
    setName("");
    setSlug("");
    setCreationPath("business_intent");
    setTemplateId(templates[0]?.id ?? LOCAL_AGENT_INTAKE_TEMPLATES[0]!.id);
    setContract({
      ...EMPTY_COMMITMENT_BODY,
      channels: ["web"],
      languages: ["en"],
    });
    setCapabilities(["Answer from knowledge"]);
    setArtifact({ name: "", kind: "transcript", text: "", source_ref: "" });
    setStatus({ kind: "idle" });
    setDraftRestored(false);
    setDraftSavedAt(null);
    if (clearDraft) clearStoredDraft();
  }

  function updateContract<K extends keyof CommitmentBody>(
    field: K,
    value: CommitmentBody[K],
  ) {
    setContract((current) => ({ ...current, [field]: value }));
  }

  function toggleContractList(field: ContractListField, value: string) {
    setContract((current) => {
      const existing = current[field];
      const next = existing.includes(value)
        ? existing.filter((item) => item !== value)
        : [...existing, value];
      return { ...current, [field]: next };
    });
  }

  function toggleCapability(capability: string) {
    setCapabilities((current) =>
      current.includes(capability)
        ? current.filter((item) => item !== capability)
        : [...current, capability],
    );
  }

  function applyTemplateDefaults(template: AgentIntakeTemplate) {
    const templateArtifact = template.artifacts[0];
    setContract((current) => ({
      ...current,
      ...template.contract,
      owner_user_id: current.owner_user_id,
      backup_owner_user_id: current.backup_owner_user_id,
    }));
    setCapabilities(template.capabilities);
    if (templateArtifact) {
      setArtifact(templateArtifact);
    }
  }

  useEffect(() => {
    if (creationPath !== "enterprise_template" || !activeTemplate) return;
    if (restoringDraftRef.current) {
      restoringDraftRef.current = false;
      return;
    }
    applyTemplateDefaults(activeTemplate);
  }, [activeTemplate, creationPath]);

  function applyTemplate(nextTemplateId: string) {
    const template =
      templates.find((item) => item.id === nextTemplateId) ??
      LOCAL_AGENT_INTAKE_TEMPLATES[0]!;
    setTemplateId(template.id);
    applyTemplateDefaults(template);
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
      const artifacts = hasArtifact(artifact)
        ? [
            {
              ...artifact,
              name: artifact.name.trim() || "intake-artifact",
              source_ref: artifact.source_ref.trim(),
              text: artifact.text.trim(),
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
      if (result.state === "failed") {
        setStatus({ kind: "recoverable_failure", intake: result });
        return;
      }
      setOpen(false);
      reset({ clearDraft: true });
      router.push(`/agents/${result.agent.id}?intake=${result.id}`);
    } catch (err) {
      setStatus({
        kind: "error",
        message: createErrorMessage(err),
      });
    }
  }

  async function handleRetryGeneration() {
    if (status.kind !== "recoverable_failure") return;
    const intake = status.intake;
    setStatus({ kind: "recovering", action: "retry" });
    try {
      const result = await retryAgentIntakeGeneration(
        effectiveWorkspaceId,
        intake.id,
      );
      if (result.state === "failed") {
        setStatus({ kind: "recoverable_failure", intake: result });
        return;
      }
      const agentId = result.agent?.id ?? result.agent_id;
      setOpen(false);
      reset({ clearDraft: true });
      router.push(`/agents/${agentId}?intake=${result.id}`);
    } catch (err) {
      setStatus({
        kind: "recoverable_failure",
        intake: {
          ...intake,
          readiness: {
            ...intake.readiness,
            needs_attention: [
              err instanceof Error ? err.message : "Retry failed.",
              ...intake.readiness.needs_attention,
            ],
          },
        },
      });
    }
  }

  async function handleContinueManually() {
    if (status.kind !== "recoverable_failure") return;
    const intake = status.intake;
    setStatus({ kind: "recovering", action: "manual" });
    try {
      const result = await continueAgentIntakeManually(
        effectiveWorkspaceId,
        intake.id,
        "Builder chose manual setup from the creation wizard.",
      );
      const agentId = result.agent?.id ?? result.agent_id;
      setOpen(false);
      reset({ clearDraft: true });
      router.push(`/agents/${agentId}?intake=${result.id}&manual=1`);
    } catch (err) {
      setStatus({
        kind: "recoverable_failure",
        intake: {
          ...intake,
          readiness: {
            ...intake.readiness,
            needs_attention: [
              err instanceof Error
                ? err.message
                : "Manual continuation failed.",
              ...intake.readiness.needs_attention,
            ],
          },
        },
      });
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (
          !nextOpen &&
          status.kind !== "submitting" &&
          status.kind !== "recovering"
        ) {
          reset();
        }
      }}
    >
      <DialogTrigger asChild>
        <button
          type="button"
          className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          data-testid="new-agent-button"
        >
          New agent
        </button>
      </DialogTrigger>
      <DialogContent
        aria-label="Create agent"
        data-testid="new-agent-modal"
        className="max-h-[92vh] max-w-5xl overflow-y-auto"
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          const focusTitle = () => titleRef.current?.focus();
          if (typeof window.requestAnimationFrame === "function") {
            window.requestAnimationFrame(focusTitle);
          } else {
            focusTitle();
          }
        }}
      >
        <form
          onSubmit={handleSubmit}
          className="flex w-full flex-col gap-5"
          noValidate
        >
          <DialogHeader>
            <DialogTitle ref={titleRef} tabIndex={-1}>
              Agent Contract Wizard
            </DialogTitle>
            <DialogDescription>
              What agent are you building, for whom, and what must it never get
              wrong?
            </DialogDescription>
          </DialogHeader>

          {workspaceMissing ? (
            <p
              className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
              data-testid="new-agent-workspace-required"
              role="status"
            >
              Select or create a real workspace before starting governed agent
              intake. Studio will not create agents inside a local placeholder
              workspace.{" "}
              <a className="font-medium underline" href="/workspaces/new">
                Create workspace
              </a>
              .
            </p>
          ) : null}

          {permissionBlocked ? (
            <p
              className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
              data-testid="new-agent-permission-required"
              role="status"
            >
              You are a {workspaceRole} in {workspaceName ?? "this workspace"}.
              Creating governed agents requires owner or admin access. Ask an
              admin to grant builder permissions or create the draft for you.
            </p>
          ) : null}

          {draftRestored || draftSavedAt ? (
            <div
              className="flex flex-col gap-2 rounded-md border border-info/30 bg-info/5 p-3 text-sm text-info sm:flex-row sm:items-center sm:justify-between"
              data-testid="new-agent-draft-status"
              role="status"
            >
              <span>
                {draftRestored
                  ? "Restored your saved local intake draft."
                  : "Local intake draft saved."}
              </span>
              <button
                type="button"
                className="w-fit rounded-md border border-info/40 px-2 py-1 text-xs font-medium"
                data-testid="new-agent-discard-draft"
                onClick={() => reset({ clearDraft: true })}
              >
                Discard draft
              </button>
            </div>
          ) : null}

          <ol
            className="grid gap-2 text-xs md:grid-cols-4 xl:grid-cols-7"
            aria-label="Agent contract wizard steps"
          >
            {WIZARD_STEPS.map((item, index) => {
              const current = step === index;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => setStep(index)}
                    aria-current={current ? "step" : undefined}
                    data-testid={`new-agent-step-${item.id}`}
                    className={[
                      "h-full w-full rounded-md border px-3 py-2 text-left transition-colors",
                      current
                        ? "border-primary bg-primary/10 text-foreground shadow-sm"
                        : "bg-background text-muted-foreground hover:bg-muted/50",
                    ].join(" ")}
                  >
                    <span className="block font-semibold">{item.label}</span>
                    <span className="block text-[0.68rem] leading-4">
                      {item.caption}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>

          <div className="rounded-md border bg-muted/25 p-4">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Step {step + 1} of {WIZARD_STEPS.length}
                </p>
                <h3 className="text-lg font-semibold">{activeStep.label}</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Readiness {readinessScore}%
              </p>
            </div>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${readinessScore}%` }}
              />
            </div>
          </div>

          <section
            hidden={activeStep.id !== "mission"}
            className={panelClass(activeStep.id === "mission")}
            data-testid="new-agent-step-panel-mission"
          >
            <fieldset className="grid gap-3 instrument-panel rounded-2xl p-4">
              <legend className="px-1 text-sm font-medium">
                Creation path
              </legend>
              <div className="grid gap-2 md:grid-cols-3">
                {CREATION_PATHS.map((option) => (
                  <label
                    key={option.value}
                    className={[
                      "flex cursor-pointer gap-2 rounded-md border p-3 text-sm transition-colors",
                      creationPath === option.value
                        ? "border-primary bg-primary/10"
                        : "bg-background hover:bg-muted/50",
                    ].join(" ")}
                  >
                    <input
                      type="radio"
                      name="creation-path"
                      value={option.value}
                      checked={creationPath === option.value}
                      onChange={(event) =>
                        chooseCreationPath(
                          event.target.value as AgentIntakePath,
                        )
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
                    {templates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    ))}
                  </select>
                </label>
                <p className="text-xs text-muted-foreground">
                  {activeTemplate?.summary}
                </p>
                {templateCatalogState !== "approved" ? (
                  <p
                    className="text-xs text-warning"
                    data-testid="new-agent-template-catalog-unapproved"
                  >
                    {templateCatalogState === "loading"
                      ? "Loading approved workspace templates from cp-api."
                      : templateCatalogState === "unavailable"
                        ? "No approved workspace templates loaded. These examples cannot be cloned as enterprise templates."
                        : "Offline examples only. Connect the workspace template catalog before cloning an approved enterprise template."}
                  </p>
                ) : null}
              </fieldset>
            ) : null}

            <div className="grid gap-4 instrument-panel rounded-2xl p-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Agent name</span>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  data-testid="new-agent-name"
                  placeholder="Billing Support Agent"
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
                  placeholder="billing-support"
                  className="rounded-md border bg-background px-2 py-1 font-mono"
                />
                {slugError ? (
                  <span
                    id={slugErrorId}
                    role="alert"
                    data-testid="new-agent-slug-error"
                    className="text-xs text-destructive"
                  >
                    {slugError}
                  </span>
                ) : null}
              </label>
              <label className="flex flex-col gap-1 text-sm md:col-span-2">
                <span className="font-medium">Business responsibility</span>
                <textarea
                  value={contract.business_responsibility}
                  onChange={(e) =>
                    updateContract("business_responsibility", e.target.value)
                  }
                  rows={3}
                  data-testid="new-agent-business-responsibility"
                  placeholder="Resolve billing cancellations safely using approved policy, CRM context, and human escalation."
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
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
                <span className="font-medium">Success metric</span>
                <textarea
                  value={contract.success_metric}
                  onChange={(e) =>
                    updateContract("success_metric", e.target.value)
                  }
                  rows={3}
                  data-testid="new-agent-success-metric"
                  placeholder="95% regression pass rate before canary."
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
            </div>
          </section>

          <section
            hidden={activeStep.id !== "boundaries"}
            className={panelClass(activeStep.id === "boundaries")}
            data-testid="new-agent-step-panel-boundaries"
          >
            <div className="grid gap-4 instrument-panel rounded-2xl p-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm md:col-span-2">
                <span className="font-medium">Worst-case failure</span>
                <textarea
                  value={contract.worst_case_failure}
                  onChange={(e) =>
                    updateContract("worst_case_failure", e.target.value)
                  }
                  rows={3}
                  data-testid="new-agent-worst-case-failure"
                  placeholder="Promises a refund, legal position, or account action outside approved policy."
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
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
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Compliance domain</span>
                <input
                  value={contract.compliance_domain}
                  onChange={(e) =>
                    updateContract("compliance_domain", e.target.value)
                  }
                  data-testid="new-agent-compliance-domain"
                  placeholder="SOC2 support operations"
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
                  placeholder="10k turns per month"
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
                  placeholder="$0.08 per resolved turn"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Launch date</span>
                <input
                  type="date"
                  value={contract.launch_date}
                  onChange={(e) =>
                    updateContract("launch_date", e.target.value)
                  }
                  data-testid="new-agent-launch-date"
                  className="rounded-md border bg-background px-2 py-1"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm md:col-span-2">
                <span className="font-medium">Out-of-scope tasks</span>
                <textarea
                  value={contract.out_of_scope}
                  onChange={(e) =>
                    updateContract("out_of_scope", e.target.value)
                  }
                  rows={2}
                  data-testid="new-agent-out-of-scope"
                  placeholder="Legal advice, high-value refunds, regulated claims without source evidence."
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
          </section>

          <section
            hidden={activeStep.id !== "capabilities"}
            className={panelClass(activeStep.id === "capabilities")}
            data-testid="new-agent-step-panel-capabilities"
          >
            <fieldset className="grid gap-3 instrument-panel rounded-2xl p-4">
              <legend className="px-1 text-sm font-medium">
                Capabilities to seed
              </legend>
              <p className="text-sm text-muted-foreground">
                Each selected capability creates placeholders for behavior,
                tools, knowledge, evals, and policies. Credentials can stay in
                mock mode during creation.
              </p>
              <div className="grid gap-2 md:grid-cols-2">
                {CAPABILITY_OPTIONS.map((capability) => (
                  <label
                    key={capability}
                    className={[
                      "flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors",
                      capabilities.includes(capability)
                        ? "border-primary bg-primary/10"
                        : "bg-background hover:bg-muted/50",
                    ].join(" ")}
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
          </section>

          <section
            hidden={activeStep.id !== "knowledge_tools"}
            className={panelClass(activeStep.id === "knowledge_tools")}
            data-testid="new-agent-step-panel-knowledge-tools"
          >
            <fieldset className="grid gap-3 instrument-panel rounded-2xl p-4">
              <legend className="px-1 text-sm font-medium">
                Knowledge and tool artifacts
              </legend>
              <p className="text-sm text-muted-foreground">
                Upload or paste source material. Intake accepts docs,
                transcripts, legacy exports, OpenAPI/Postman artifacts, cURL,
                and browser DevTools fetch exports.
              </p>
              <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_13rem]">
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
                        kind: e.target
                          .value as AgentIntakeArtifactInput["kind"],
                      }))
                    }
                    data-testid="new-agent-artifact-kind"
                    className="rounded-md border bg-background px-2 py-1"
                  >
                    {ARTIFACT_KIND_OPTIONS.map((kind) => (
                      <option key={kind} value={kind}>
                        {kind.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1 text-sm md:col-span-2">
                  <span className="font-medium">Source reference</span>
                  <input
                    value={artifact.source_ref}
                    onChange={(e) =>
                      setArtifact((current) => ({
                        ...current,
                        source_ref: e.target.value,
                      }))
                    }
                    placeholder="drive://billing/refund-policy, botpress://export/v3, postman://collection"
                    data-testid="new-agent-artifact-source-ref"
                    className="rounded-md border bg-background px-2 py-1"
                  />
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
                    rows={5}
                    placeholder="Paste transcript excerpts, policy text, cURL, Copy as fetch, or migration notes. Secrets should remain out of pasted content."
                    data-testid="new-agent-artifact-text"
                    className="rounded-md border bg-background px-2 py-1"
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm md:col-span-2">
                  <span className="font-medium">Systems touched</span>
                  <textarea
                    value={contract.systems_touched.join(", ")}
                    onChange={(e) =>
                      updateContract(
                        "systems_touched",
                        parseList(e.target.value),
                      )
                    }
                    rows={2}
                    data-testid="new-agent-systems"
                    placeholder="billing api, crm, ticketing"
                    className="rounded-md border bg-background px-2 py-1"
                  />
                </label>
              </div>
              <div className="rounded-md border border-dashed bg-muted/25 p-3 text-xs text-muted-foreground">
                If credentials are not available yet, Studio creates mock tool
                contracts and keeps production deployment blocked until the real
                tool test passes.
              </div>
            </fieldset>
          </section>

          <section
            hidden={activeStep.id !== "channels"}
            className={panelClass(activeStep.id === "channels")}
            data-testid="new-agent-step-panel-channels"
          >
            <fieldset className="grid gap-3 instrument-panel rounded-2xl p-4">
              <legend className="px-1 text-sm font-medium">Channels</legend>
              <p className="text-sm text-muted-foreground">
                Voice is one channel, not the category. Select every channel the
                agent may eventually support; only one sandbox channel is
                required for the first draft.
              </p>
              <div className="grid gap-2 md:grid-cols-3">
                {CHANNEL_OPTIONS.map((channel) => {
                  const selected = contract.channels.includes(channel.id);
                  return (
                    <button
                      key={channel.id}
                      type="button"
                      onClick={() => toggleContractList("channels", channel.id)}
                      aria-pressed={selected}
                      className={[
                        "rounded-md border p-3 text-left text-sm transition-colors",
                        selected
                          ? "border-primary bg-primary/10"
                          : "bg-background hover:bg-muted/50",
                      ].join(" ")}
                    >
                      <span className="block font-medium">{channel.label}</span>
                      <span className="text-xs text-muted-foreground">
                        {channel.detail}
                      </span>
                    </button>
                  );
                })}
              </div>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium">Selected channels</span>
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
            </fieldset>
          </section>

          <section
            hidden={activeStep.id !== "generated_tests"}
            className={panelClass(activeStep.id === "generated_tests")}
            data-testid="new-agent-step-panel-generated-tests"
          >
            <div className="instrument-panel rounded-2xl p-4">
              <h4 className="text-sm font-semibold">Starter eval suite</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                These tests are generated from the contract and attached to the
                draft before any production action exists.
              </p>
              <div
                className="mt-4 grid gap-2"
                data-testid="new-agent-generated-tests"
              >
                {generatedTests.map((testName, index) => (
                  <div
                    key={testName}
                    className="rounded-md border bg-background px-3 py-2 text-sm"
                  >
                    <span className="font-medium">E{index + 1}</span>
                    <span className="ml-2">{testName}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-md border border-dashed bg-muted/25 p-3 text-xs text-muted-foreground">
                Bad simulator turns, operator resolutions, and migration parity
                misses can extend this suite after the draft is created.
              </div>
            </div>
          </section>

          <section
            hidden={activeStep.id !== "readiness"}
            className={panelClass(activeStep.id === "readiness")}
            data-testid="new-agent-step-panel-readiness"
          >
            <div className="grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
              <div className="instrument-panel rounded-2xl p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Draft readiness
                </p>
                <p className="mt-2 text-3xl font-semibold">{readinessScore}%</p>
                <p className="mt-2 text-sm text-muted-foreground">
                  The draft can be created when required contract fields are
                  complete. Production remains blocked until proof gates pass.
                </p>
              </div>
              <div className="instrument-panel rounded-2xl p-4">
                <h4 className="text-sm font-semibold">Readiness landing</h4>
                <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                  {readiness.map((item) => (
                    <div
                      key={item.label}
                      className={[
                        "rounded-md border px-3 py-2",
                        item.ready
                          ? "border-success/30 bg-success/10"
                          : "border-warning/40 bg-warning/10",
                      ].join(" ")}
                    >
                      <span className="font-medium">
                        {item.ready ? "Ready" : "Needs attention"}
                      </span>
                      <span className="ml-2 text-muted-foreground">
                        {item.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid gap-3 instrument-panel rounded-2xl p-4 text-sm md:grid-cols-3">
              <div>
                <h4 className="font-semibold">Created objects</h4>
                <p className="mt-1 text-muted-foreground">
                  Agent, draft branch, Commitment Document, behavior config,
                  channel bindings, tool contracts, memory policy, and starter
                  eval suite.
                </p>
              </div>
              <div>
                <h4 className="font-semibold">Async jobs</h4>
                <p className="mt-1 text-muted-foreground">
                  {INTAKE_JOBS.join(", ")}.
                </p>
              </div>
              <div>
                <h4 className="font-semibold">Landing</h4>
                <p className="mt-1 text-muted-foreground">
                  Agent Workbench readiness view with blockers deep-linked to
                  the right section.
                </p>
              </div>
            </div>
          </section>

          {missingContract.length > 0 ? (
            <p
              className="rounded-md border border-warning/50 bg-warning/10 px-3 py-2 text-xs text-muted-foreground"
              data-testid="new-agent-contract-gaps"
            >
              Missing contract fields:{" "}
              {missingContract.map(commitmentFieldLabel).join(", ")}
            </p>
          ) : null}
          {status.kind === "recoverable_failure" ? (
            <div
              className="grid gap-3 rounded-md border border-warning/50 bg-warning/10 p-3 text-sm"
              data-testid="new-agent-recoverable-failure"
              role="status"
            >
              <div>
                <p className="font-medium text-foreground">
                  Draft generation needs recovery
                </p>
                <p className="mt-1 text-muted-foreground">
                  The agent and Commitment Document were saved, but automatic
                  draft generation did not complete. Retry the generator or
                  continue into the Workbench with manual setup.
                </p>
              </div>
              {status.intake.readiness.needs_attention.length > 0 ? (
                <ul
                  className="grid gap-1 text-xs text-muted-foreground"
                  data-testid="new-agent-recovery-details"
                >
                  {status.intake.readiness.needs_attention
                    .slice(0, 3)
                    .map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                </ul>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground"
                  data-testid="new-agent-retry-generation"
                  onClick={() => void handleRetryGeneration()}
                >
                  Retry generation
                </button>
                <button
                  type="button"
                  className="rounded-md border bg-background px-3 py-1.5 text-xs font-medium"
                  data-testid="new-agent-continue-manually"
                  onClick={() => void handleContinueManually()}
                >
                  Continue manually
                </button>
              </div>
            </div>
          ) : null}
          {status.kind === "error" ? (
            <p
              id={formErrorId}
              role="alert"
              data-testid="new-agent-error"
              className="text-sm text-destructive"
            >
              {status.message}
            </p>
          ) : null}
          {workspaceMissing ? (
            <p
              className="text-xs text-muted-foreground"
              data-testid="new-agent-submit-blocked"
            >
              Creation is blocked until workspace context is loaded from the
              control plane.
            </p>
          ) : null}
          {permissionBlocked ? (
            <p
              className="text-xs text-muted-foreground"
              data-testid="new-agent-permission-submit-blocked"
            >
              Creation is blocked because your workspace role cannot create
              governed agents.
            </p>
          ) : null}
          {creationPath === "enterprise_template" &&
          templateCatalogState !== "approved" ? (
            <p
              className="text-xs text-muted-foreground"
              data-testid="new-agent-template-submit-blocked"
            >
              Enterprise-template creation is blocked until the selected
              template is loaded from the workspace-approved catalog.
            </p>
          ) : null}

          <div className="grid gap-2 instrument-panel rounded-2xl p-3 text-xs text-muted-foreground md:grid-cols-3">
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
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between">
            <button
              type="button"
              className="rounded-md border px-3 py-1.5 text-sm"
              data-testid="new-agent-cancel"
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-50"
                data-testid="new-agent-back"
                disabled={
                  step === 0 ||
                  status.kind === "submitting" ||
                  status.kind === "recovering"
                }
                onClick={() => setStep((current) => Math.max(current - 1, 0))}
              >
                Back
              </button>
              <button
                type="button"
                className="rounded-md border px-3 py-1.5 text-sm disabled:opacity-50"
                data-testid="new-agent-next"
                disabled={
                  step === WIZARD_STEPS.length - 1 ||
                  status.kind === "submitting" ||
                  status.kind === "recovering"
                }
                onClick={() =>
                  setStep((current) =>
                    Math.min(current + 1, WIZARD_STEPS.length - 1),
                  )
                }
              >
                Next
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                data-testid="new-agent-submit"
                className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                {status.kind === "submitting"
                  ? "Analyzing intake..."
                  : status.kind === "recovering"
                    ? status.action === "retry"
                      ? "Retrying..."
                      : "Opening Workbench..."
                    : "Create governed draft"}
              </button>
            </div>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
