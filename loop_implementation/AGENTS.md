# AGENTS.md — Entry point for AI agents working on this codebase

This file is for **AI coding agents** (Cursor, Claude Code, Aider, OpenAI Codex, custom agent teams) that will help build Loop. It tells you which files to read, in what order, and which formats are canonical.

If you are a human, start at `README.md` instead.

---

## TL;DR for an AI agent

- The product is **Loop** — an open-source, agent-first runtime for production AI agents.
- Strategic context: `../botpress_competitor_spec.md` (one folder up).
- Implementation context: this folder.
- **All canonical docs are Markdown.** Read those first. Other formats are exports.
- Cloud-agnostic by construction. Never assume AWS specifics. See `architecture/CLOUD_PORTABILITY.md`.
- **For every task, use a skill.** Read `skills/_base/SKILL_ROUTER.md` and pick the matching skill from the Task → Skill table. The skill tells you which docs to read and the steps to follow. End every task with `skills/meta/write-pr.md`.

---

## Canonical (AI-friendly) file map

Read in this order before doing any task:

1. `README.md` — folder index & status
2. `architecture/ARCHITECTURE.md` — system architecture (C4 layered)
3. `engineering/GLOSSARY.md` — canonical vocabulary; cite this when in doubt
4. `architecture/CLOUD_PORTABILITY.md` — cloud abstractions (read before any infra change)
5. `architecture/AUTH_FLOWS.md` — auth + tokens (read before any auth code)
6. `architecture/NETWORKING.md` — network topology, egress, DNS, certs
7. `adrs/README.md` — decisions and *why* (28 ADRs)
8. `data/SCHEMA.md` — data model
9. `api/openapi.yaml` — REST surface
10. `engineering/HANDBOOK.md` — coding conventions
11. `engineering/ENV_REFERENCE.md` — every env var (read before adding config)
12. `engineering/ERROR_CODES.md` — error namespace (read before adding errors)
13. `engineering/SECURITY.md` — security model
14. `engineering/TESTING.md` — test pyramid + eval harness
15. `engineering/PERFORMANCE.md` — perf budgets + gating
16. `engineering/DR.md` — disaster recovery
17. `engineering/RUNBOOKS.md` — operational procedures
18. `engineering/COPY_GUIDE.md` — voice + tone for any user-facing string
19. `ux/00_CANONICAL_TARGET_UX_STANDARD.md` — canonical Studio target UX/UI standard
20. `tracker/TRACKER.md` — current epics, stories, sprints, hiring, risks
21. `tracker/SPRINT_0.md` — week-by-week first six weeks
22. `engineering/templates/` — ADR_TEMPLATE, RFC_TEMPLATE, RUNBOOK_TEMPLATE, SKILL_TEMPLATE (use when creating those)
23. `skills/` — 40 task-specific skills + per-platform adapters (Claude, Codex, Copilot, Cursor, Aider, Windsurf, Continue.dev). Always start at `skills/_base/SKILL_ROUTER.md`.

---

## Format conventions (what is canonical, what is derived)

| Artifact | Canonical format | AI-friendly companion(s) | Human format |
|----------|------------------|--------------------------|---------------|
| Architecture | `architecture/ARCHITECTURE.md` | (already Markdown) | (already readable) |
| Data model | `data/SCHEMA.md` | (already Markdown, includes SQL DDL + Pydantic) | — |
| API spec | `api/openapi.yaml` | YAML is parsing-friendly; `.json` can be derived if needed | imported into Postman/Stoplight |
| ADRs | `adrs/README.md` (single file with all 28 ADRs) | (already Markdown) | — |
| Glossary | `engineering/GLOSSARY.md` | (already Markdown) | — |
| Env vars | `engineering/ENV_REFERENCE.md` | (already Markdown) | — |
| Error codes | `engineering/ERROR_CODES.md` | (already Markdown) | — |
| Auth flows | `architecture/AUTH_FLOWS.md` | (already Markdown with sequence diagrams) | — |
| Networking | `architecture/NETWORKING.md` | (already Markdown) | — |
| Performance | `engineering/PERFORMANCE.md` | (already Markdown) | — |
| Disaster recovery | `engineering/DR.md` | (already Markdown) | — |
| Runbooks | `engineering/RUNBOOKS.md` | (already Markdown) | — |
| Copy guide | `engineering/COPY_GUIDE.md` | (already Markdown) | — |
| Templates | `engineering/templates/*.md` | (already Markdown) | — |
| Skills (per-task playbooks) | `skills/<category>/<name>.md` | (already Markdown with Claude Skill frontmatter) | per-platform adapters in `skills/platforms/*` |
| Skill router | `skills/_base/SKILL_ROUTER.md` | (already Markdown) | — |
| UX design | `ux/00_CANONICAL_TARGET_UX_STANDARD.md` | (already Markdown with ASCII wireframes) | Figma later |
| Engineering docs | `engineering/*.md` | (already Markdown) | — |
| Tracker | `tracker/TRACKER.md` (canonical for AI agents) | `tracker/tracker.json` (full structured), `tracker/csv/*.csv` (per sheet) | `tracker/IMPLEMENTATION_TRACKER.xlsx` |
| Sprint 0 plan | `tracker/SPRINT_0.md` | (already Markdown) | — |
| Strategy spec (parent folder) | `../botpress_competitor_spec.md` | (already Markdown) | `../botpress_competitor_spec.docx` (export), `../botpress_competitor_pitch.pptx` (deck) |

**Rules for agents:**
- When asked to "update the tracker," update **both** `tracker/TRACKER.md` (the .md is the canonical view for AI tasks) **and** the underlying `tracker/IMPLEMENTATION_TRACKER.xlsx` (use `tools/tracker_to_machine.py` to regenerate the .md from .xlsx, or vice versa).
- Never edit `.docx` or `.pptx` directly — they are exports of the parent strategy spec, not source of truth.
- Always parse `api/openapi.yaml` rather than hand-coding REST shapes.

---

## Cloud-portability rules (mandatory reading)

Before writing or modifying any infra code:

1. Read `adrs/README.md` ADR-016.
2. Read `architecture/CLOUD_PORTABILITY.md` end-to-end.
3. Confirm your change goes through one of the internal interfaces (`ObjectStore`, `KMS`, `SecretsBackend`, `EmailSender`, `ManagedPostgres`, `ManagedRedis`, `EventBus`, `IdentityProvider`).
4. If you must add a new cloud-touching primitive, add at least two implementations (one cloud-native or OSS, one alternate) and matrix-test in CI.
5. Never import a cloud SDK directly from `packages/runtime/`, `packages/gateway/`, or `packages/sdk-py/`. Only `packages/observability/` and `apps/control-plane/` may, and only behind interfaces.

Forbidden services (without a successor ADR overriding ADR-016): see ADR-016 §"Forbidden services."

---

## What you can do without asking

- Fix typos and broken markdown links.
- Add tests where coverage is below 85%.
- Update an ADR's "Consequences" or "Open Questions" sections with new findings.
- Improve docstrings.
- Add examples to `examples/`.
- Refactor inside a single file without changing public interfaces.

## What you must propose first (then wait for approval)

- Any change to a Pydantic public type (it bumps the SDK major version).
- Any new ADR.
- Any change to `api/openapi.yaml` schemas.
- Any new cloud-touching code path.
- Any new dependency.
- Any change to CI gating thresholds.
- Any new package or app.

---

## Repository conventions (cheat sheet)

- **Branch:** `<author>/<short-slug>` (e.g., `agent-bot/cloud-portability-helm`).
- **Commit:** Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`).
- **PR title** = first commit message.
- **PR description** must explain *why*, not *what* (the diff shows what).
- **Required checks** before merge: lint, typecheck, unit tests, integration tests, security scans. Runtime PRs also require eval suite passing.
- **Squash-merge** into `main`. No merge commits.

---

## Per-task quickstart for AI agents

When given a task, do the following IN ORDER:

1. **Read `skills/_base/SKILL_ROUTER.md`.** Find your task in the Task → Skill table. Open the matched skill file.
2. **Tracker BEFORE — claim OR resume.** Find the story in `tracker/TRACKER.md`.
   - If status is `Not started`: claim it. Edit `tools/build_tracker.py` to set status `In progress` + Owner + the structured Notes block (Branch / Skill / Last step / Heartbeat / Open questions / Blockers / Commits). Regenerate companions. Commit as `chore(tracker): claim S0NN` — first commit on your branch. **Push immediately**, so a successor can resume if you get cut off.
   - If status is `In progress` and the existing Heartbeat is **stale** (> 4 h AI / > 7 d human) or you were handed off the task: apply **`skills/meta/resume-task.md`** instead — sync the branch, resume from the last checkpoint, do NOT fork a new claim.
   - If the existing Heartbeat is fresh: pick a different story; the Owner is still active.
3. **Read the matched skill end-to-end** plus every file in its `required_reading`.
4. **Check ADRs.** Search `adrs/README.md` for any decision that constrains your task. Don't violate; propose a new ADR if you must (apply `skills/architecture/propose-adr.md`).
5. **Follow the skill's Steps** in order. Don't skip the Definition of done.
6. **Tracker DURING — heartbeat checkpoints + status changes.**
   - For tasks > 1 h: after every numbered skill step / ~30 min, commit `chore(tracker): checkpoint S0NN step <N>/<M> — <one-liner>` and push. Update the Notes cell's `Last step:` and `Heartbeat:` lines so anyone can resume.
   - Never leave uncommitted work — `chore(tracker): wip S0NN — paused at <reason>` if you must stop mid-step.
   - If blocked: flip status to `Blocked`, populate `Blockers:` in structured Notes, push, hand back.
7. **Run the tests after every change.** `make test` in repo root.
8. **Update docs in the same PR.** Each skill specifies which docs change; never split into a follow-up PR.
9. **Tracker AFTER — close the story.** Edit `tools/build_tracker.py` to set status `Done` + structured "Done" notes (PR #, branch, final heartbeat). Regenerate companions. Commit as `chore(tracker): close S0NN` — last commit on your branch.
10. **End with `skills/meta/write-pr.md`** to open the PR correctly. The pre-merge checklist verifies the claim+close commits exist.

For multi-skill tasks, follow the order listed in `skills/_base/SKILL_ROUTER.md` "Multi-skill tasks": Decision → Data → API → Coding → Testing → Security/Observability → UX → Meta. The tracker claim happens once at the top and the close happens once at the bottom — not per skill.

---

## When you don't know something

- If a fact is missing from these docs, **say so explicitly**. Do not invent. Add a `TODO:` block in the doc with the specific question.
- If two docs disagree, the priority order is: **ADRs > ARCHITECTURE > SCHEMA > everything else**. Open a PR to fix the disagreement.
- If a task is underspecified, **ask for clarification before writing code**. Cite the ambiguity.

---

## Files agents should never touch

- `LICENSE` (legal).
- `.github/workflows/release.yml` (release surface — humans only).
- Anything under `tracker/IMPLEMENTATION_TRACKER.xlsx` directly — regenerate via `tools/tracker_to_machine.py`.
- The `.pptx` and `.docx` exports in the parent folder — they are derived from the master `.md`.

---

## Good PR examples for AI agents

### Example 1: Runtime feature (TurnExecutor)

**Title:** `feat: add graceful degrade on budget cap + toggle cheaper model alias`

**Body:**
```
## What & why
The runtime now checks for hard cost cap BEFORE calling the LLM (pre-flight). 
If the turn would exceed the hard cap, it:
1. Logs a budget_hit event
2. Swaps to the configured cheaper model alias (e.g., gpt-3.5-turbo instead of gpt-4o)
3. Truncates history to fit within cost budget
4. Yields a degrade event so the channel knows the response is degraded

This closes [S006](tracker/IMPLEMENTATION_TRACKER.xlsx) and resolves the "hard budget enforcement" requirement.

## Changes
- `dp-runtime`: TurnExecutor.execute() → added pre-flight budget check
- `data/SCHEMA.md`: budgets table now includes `degrade_model` column (optional)
- `engineering/TESTING.md`: added test case "budget_cap_triggers_degrade_scenario"

## Testing
- Unit: test_budget_precheck_under_cap + test_budget_precheck_hit
- Integration: test_e2e_degrade_on_budget_hit (live OpenAI call with $0.001 cap)
- Eval: support-agent suite still passes (0 regressions)

## Checklist
- [x] `make test` passes locally
- [x] Docs updated (SCHEMA, UX_DESIGN §3.7 cost tab)
- [x] ADR-012 (pricing model) + ADR-028 (meter precision) reviewed for consistency
- [x] No cloud-specific imports
```

**Key patterns:**
- What (feature), Why (closes story), How (code changes), Testing, Checklist.
- Commit message = PR title (Conventional Commits).
- Cross-reference tracker story ID (S006).

### Example 2: UX/Design (Studio screen)

**Title:** `feat(studio): add operator inbox MVP + HITL compose widget`

**Body:**
```
## What & why
Studio now has a dedicated Operator Inbox screen (left rail with queues, center
with conversation list, right with detail + compose). This closes Sprint 0 Demo
requirement: "operators can take over a conversation and draft/send messages."

## Changes
- `ux/00_CANONICAL_TARGET_UX_STANDARD.md` updated with the relevant target UX behavior
- `studio-web`: new component <HITLInbox /> + <OperatorCompose />
- `studio-web`: new route /app/inbox with WebSocket for real-time updates
- `cp-api`: new POST /conversations/{id}/takeover endpoint (creates hitl_queue entry)

## Testing
- E2E: test_operator_takeover_flow (Playwright)
- E2E: test_operator_compose_drafts_as_agent (LLM judgment scorer)
- Manual: 2 operators in the same conversation (cursor tracking)

## Checklist
- [x] Accessible (keyboard nav + ARIA labels)
- [x] Dark mode tested
- [x] Mobile responsive (minimal tablet support)
- [x] 00_CANONICAL_TARGET_UX_STANDARD.md remains the target UX source of truth
- [x] No console errors
```

### Example 3: Infra / DevOps (Cloud)

**Title:** `feat: add cloud-agnostic KMS interface + HashiCorp Vault + AWS Secrets Manager implementations`

**Body:**
```
## What & why
Secrets are now routed through a cloud-agnostic KMS interface (following ADR-016).
Two implementations ship: HashiCorp Vault (default, works on all clouds) and AWS
Secrets Manager (cloud-native alternate, AWS only). Workspaces can choose via
Helm value or environment variable.

This unblocks self-hosted deployments and keeps the runtime out of AWS SDK land.

## Changes
- `packages/runtime/loop/security/kms.py`: abstract SecretsBackend interface (3 methods: fetch, rotate, destroy)
- `packages/runtime/loop/security/vault.py`: HashiCorp Vault HTTP client impl
- `packages/runtime/loop/security/aws_secrets_mgr.py`: AWS Secrets Manager impl (behind feature flag)
- `infra/helm/values.yaml`: new `secrets_backend: vault|aws_secrets_manager`
- `architecture/CLOUD_PORTABILITY.md` §2.3 updated with interface + per-cloud mapping

## Testing
- Unit: test_vault_client_fetch_ok, test_vault_client_rotate_ok, test_aws_impl_...
- Integration: test_e2e_vault_on_k3d (local k3d + Vault in container)
- Integration: test_e2e_aws_impl (skipped by default, runs in CI on AWS only)

## Checklist
- [x] No direct AWS SDK imports in runtime package
- [x] CLOUD_PORTABILITY.md updated
- [x] Both implementations matrix-tested in CI
- [x] Helm chart defaults to cloud-agnostic (Vault)
- [x] Security.md §2 ("Secrets") reviewed + updated
```

---

## Hard list of files agents should never touch

- `LICENSE` (Apache 2.0; legal).
- `.github/workflows/release.yml` (release surface — humans + CI only).
- `tracker/IMPLEMENTATION_TRACKER.xlsx` (use `tools/tracker_to_machine.py` to sync; edit the .md instead).
- `botpress_competitor_spec.*` (parent folder; strategy doc — CTO only).
- Anything marked `[HUMAN-ONLY]` in a file header.
- `.pptx` and `.docx` files in parent folder (they're derived exports).

---

## Mandatory "before merging" checklist for AI agents

Before marking a PR ready for review:

1. **Tests pass locally:** `make test` completes in < 3 min, no failures.
2. **Type-checks pass:** `make lint` (mypy + ruff).
3. **Docs in sync:** If you changed architecture/schema/API/security, the relevant `.md` is updated in this PR.
4. **No ADR violations:** Search `adrs/README.md` for decisions affecting your change. If you must override, propose a new ADR in the PR.
5. **No cloud SDK imports:** Search for `import boto3`, `import azure.*`, `import google.cloud.*`. Only `architecture/CLOUD_PORTABILITY.md` §"Implementations" allows these (and only behind interface).
6. **Tracker story linked:** PR title or body references the story ID (S###) it closes.
7. **No secrets in code:** No hardcoded API keys, test tokens, or credentials. Use env vars or Vault.
8. **Eval suite passing:** If you touched the runtime, verify evals don't regress: `loop eval run support-agent --compare-baseline`.

---

## Concrete instructions for using the file tools

### When to Edit vs. Write

| Situation | Tool | Example |
|-----------|------|---------|
| Modify existing file (small change < 50 lines) | **Edit** | Add a note to 00_CANONICAL_TARGET_UX_STANDARD.md |
| Modify existing file (large change, multiple sections) | **Edit** | Still use Edit; just target multiple specific sections |
| Create new file from scratch | **Write** | New ADR, new package, new helper script |
| Refactor / rewrite entire file | **Write** | Complete rewrite of a doc or module |

### How to handle large files

- **Read in chunks:** For files >1000 lines, use `offset` and `limit` to read just the section you need (e.g., lines 600–700).
- **Search first:** Use Grep to find the exact line number before Read. Example: `grep -n "## 28. Visual Language" 00_CANONICAL_TARGET_UX_STANDARD.md` -> Edit targets that section.
- **One Edit per logical section:** Don't try to do 5 unrelated edits in one call; split them.
- **Validate your context:** Always read the surrounding lines before and after your target to understand nesting, indentation, and context.

### Example: editing the large ARCHITECTURE.md file

```
1. Grep for the section: grep -n "^## 3. Components" architecture/ARCHITECTURE.md
2. Read that section + 20 lines before/after to understand context
3. Edit only that section, preserving indentation and numbering
4. Verify your edit didn't break the table of contents (it likely references §3 by header)
```

---

## How to ask for clarification

When a task is underspecified:

1. **Stop before writing code.** Don't invent.
2. **Create a TODO in the relevant doc.** Example:
   ```markdown
   ### TODO: Clarify voice latency budget allocation
   
   Q: Should the 700ms p50 budget include network latency to the voice SIP gateway, 
   or is that assumed to be <50ms and not counted?
   
   Impact: determines whether we can afford Deepgram STT (150ms) + LLM (250ms) + 
   Cartesia TTS (150ms) or must cut one stage.
   
   Blocker for: ADR-010 (voice architecture).
   ```
3. **Open a draft PR with just the TODO.** Tag the relevant owner (e.g., Eng #3 for voice, CTO for arch decisions).
4. **Wait for reply.** Don't speculate in code.

---

## Context budget guideline

**Don't read everything every time.** Be surgical.

| Task | What to read | What NOT to read |
|------|-------|---|
| Fix a typo in SCHEMA.md | Just that file | Everything |
| Add a new LLM provider to the gateway | ARCHITECTURE.md §3 (gateway), SCHEMA.md (no schema change), openapi.yaml (if public) | Full TESTING, HANDBOOK |
| Add a new channel adapter | ARCHITECTURE.md §2.2, SCHEMA.md (channel_configs table), 00_CANONICAL_TARGET_UX_STANDARD.md (if new UI), api/openapi.yaml (webhook shape) | ADRs, SECURITY detail |
| Implement GDPR DSAR request export | SECURITY.md §6 (GDPR), SCHEMA.md (data_export_requests table), ARCHITECTURE.md (s3 layout) | Everything else |

**Good practice:** Search the code first. Find the relevant imports/dependencies. Then read only those docs.

---

## Self-test before marking complete

Before claiming a task done:

```bash
# 1. Tests pass
make test

# 2. Linting + type check
make lint

# 3. Evals pass (if runtime change)
loop eval run support-agent --compare-baseline

# 4. Docs in sync
grep -r "TODO:" . | grep -v ".git"  # no TODOs left?
git diff --name-only | grep "\.md$"  # did you update relevant docs?

# 5. No cloud SDK imports in runtime packages
grep -r "import boto3" packages/runtime/
grep -r "import azure" packages/runtime/
grep -r "from google.cloud" packages/runtime/

# 6. Tracker story referenced
# Check your branch name: is it <author>/<story-id>-<slug> ?
```

---

## Links to most-referenced files

- **Architecture & design decisions:** `architecture/ARCHITECTURE.md` (§0 glossary, §2 containers, §3 runtime components)
- **Data shapes:** `data/SCHEMA.md` (§2–3 Postgres tables, §10 Pydantic models)
- **Public API contract:** `api/openapi.yaml` (REST endpoints; parseable, not for humans)
- **Why decisions:** `adrs/README.md` (28 ADRs; read ADR-001, ADR-005, ADR-016, ADR-020 first)
- **Coding standards:** `engineering/HANDBOOK.md` (§1 local dev, §2 conventions, §3 code review bar)
- **Security baseline:** `engineering/SECURITY.md` (§1 threat model, §5 RLS, §6 compliance)
- **Testing pyramid:** `engineering/TESTING.md` (§1 unit/integration/e2e, §5 eval scorers)
- **UI/UX contracts:** `ux/00_CANONICAL_TARGET_UX_STANDARD.md` (§1 product promise, §3 principles, §5 IA, §28-32 visual/copy, §37 quality bar)
- **Sprint planning:** `tracker/SPRINT_0.md` (week-by-week milestones, dependencies)

---

## Commit message template for AI-authored PRs

Use Conventional Commits. Format: `<type>(<scope>): <subject>`

```
<type>(scope): brief imperative subject line (≤50 chars, no period)

<blank line>

More detailed explanation of what and why (wrap at 72 chars). If this PR
closes a story, reference it: Closes S001, Closes S023.

(Optional: list related changes or gotchas)

<blank line>

Type: feat | fix | refactor | docs | test | chore | perf
Scope: runtime | gateway | studio | infra | ux | etc.
```

**Examples:**
- `feat(runtime): add graceful degrade on budget cap`
- `fix(studio): trace waterfall now renders >100 spans without layout shift`
- `docs(schema): add comment to conversations table explaining RLS policy`
- `test(eval): add 5 new test cases for refund scenario`
- `refactor(gateway): extract cost accounting to separate module`

---

## If you find a gap in these docs

**This is expected.** Docs rot. Here's how to propose a fix:

1. **Note it:** Create a TODO comment in the relevant doc (see "How to ask for clarification" above).
2. **Open a PR:** Title: `docs: clarify <topic> in <filename>`. Body explains the gap and proposed fix.
3. **Wait for review:** This is a docs-only PR; faster turnaround.
4. **No need to implement:** As the AI agent, you're allowed to propose gaps; humans review + merge docs PRs.
5. **Tag it:** Add a `docs` label + tag the doc owner (usually CTO or relevant eng).

Example:
```
Title: docs: add concrete examples to AGENTS.md for "good PR structure"
Body: AGENTS.md currently says "PRs should explain why, not what" but has 
no examples. This PR adds 3 real examples from the codebase (runtime feature, 
UX change, infra change) so future AI agents have a model to follow.
```

---

## Glossary

See `architecture/ARCHITECTURE.md` §0 for the canonical glossary. Use the same vocabulary in code, docs, and commit messages.
