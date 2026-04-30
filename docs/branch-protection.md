# Branch protection — operator runbook

Branch protection cannot be enforced from inside the repo. The settings
below MUST be applied on GitHub by a repo admin **before** opening the
repository for outside contribution.

This file is the canonical record of those settings; every change to
branch protection MUST land here in the same PR that changes the GitHub
configuration.

## `main` — protection settings

Apply via **Settings → Branches → Branch protection rules** for the
pattern `main`:

- [x] **Require a pull request before merging.**
  - [x] Required approvals: **1** (during Sprint 0; raise to **2** at GA).
  - [x] Dismiss stale pull request approvals when new commits are pushed.
  - [x] Require review from Code Owners.
  - [x] Require approval of the most recent reviewable push.
- [x] **Require status checks to pass before merging.**
  - [x] Require branches to be up to date before merging.
  - Required checks (must match the job names in `.github/workflows/ci.yml`):
    - `CI / lint`
    - `CI / unit`
    - `CI / tracker-clean`
    - `CI / security`
  - **Conditionally required** (added once the corresponding code lands):
    - `CI / integration` — once `infra/docker-compose.yml` carries the full stack (S003).
    - `CI / studio` — once `apps/studio` exists (S005).
    - `CI / cli` — once `cli/` exists (later milestone).
    - `CI / evals` — once `tests/evals/runtime` exists (S021).
- [x] **Require conversation resolution before merging.**
- [x] **Require signed commits.**
- [x] **Require linear history.** (Aligned with squash-merge policy in `engineering/HANDBOOK.md` §3.)
- [x] **Require deployments to succeed before merging.** *(disabled until staging
      deploys exist; revisit at M2.)*
- [x] **Lock branch.** OFF (must remain pushable for releases).
- [x] **Do not allow bypassing the above settings.** ON. (Admins included.)
- [x] **Restrict who can push to matching branches.** ON. Allow only the
      `loop-ai/release-bot` GitHub App for tags; humans cannot push directly
      — they MUST go through PR.
- [x] **Allow force pushes.** OFF.
- [x] **Allow deletions.** OFF.

## Repository-level settings (Settings → General)

- **Pull Requests:**
  - [x] Allow squash merging — DEFAULT.
  - [ ] Allow merge commits — OFF.
  - [ ] Allow rebase merging — OFF.
  - [x] Always suggest updating pull request branches.
  - [x] Automatically delete head branches.
  - **Default commit message for squash:** "Pull request title and description".
- **Pushes:**
  - [x] Limit how many branches and tags can be updated in a single push: 5.

## Required CODEOWNERS teams

Branch protection's "Require review from Code Owners" only works if the
teams referenced in `.github/CODEOWNERS` exist in the `loop-ai` GitHub
org. Create these teams (with at least one member each) before turning
the rule on:

- `@loop-ai/cto`
- `@loop-ai/infra`
- `@loop-ai/runtime`
- `@loop-ai/security`
- `@loop-ai/observability`
- `@loop-ai/studio`
- `@loop-ai/channels`
- `@loop-ai/voice`
- `@loop-ai/devrel`

## Verification

After applying the rules, an admin should:

1. Open a draft PR from a fork.
2. Confirm CI status checks appear as required.
3. Confirm `Code Owners review required` appears under the merge box.
4. Confirm "Squash and merge" is the only merge button shown.
5. Confirm force-push is rejected on the protected branch.

Record the verification date here: `____-__-__` (initial: pending).

## Change log

| Date | Change | Author |
|------|--------|--------|
| 2026-04-29 | Initial settings drafted (S001). Awaiting GitHub admin to apply. | GitHub Copilot |
