# Dependency update policy

This policy defines how dependency updates are automated and reviewed across Python, Node, Go, Docker, and GitHub Actions.

## Automation

- Dependabot config: .github/dependabot.yml
- Schedule: weekly (Monday 04:00 UTC)
- Ecosystems covered:
  - pip (root and package-level pyproject manifests)
  - npm (apps/studio and packages/channels/web-js)
  - gomod
  - docker
  - github-actions

## Update classes

- Minor and patch updates are grouped per ecosystem for small, reviewable PRs.
- Major updates are ignored by Dependabot and must be handled by explicit, manually owned upgrade PRs.

## Merge policy

- No dependency PR auto-merges without CI green and code owner review.
- Security-related dependency updates take priority over routine updates.

## Review checklist

1. CI is green across lint, unit, security, and perf gates.
2. SBOM generation remains valid.
3. No new high/critical CVEs are introduced.
4. Breaking-change notes are reviewed for any major upgrade handled manually.

## Cadence and ownership

- Weekly triage owner: infra on-call rotation.
- Escalation: security on-call for critical advisories and emergency patch windows.
