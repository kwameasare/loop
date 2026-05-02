# Changelog

All notable changes to Loop are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

Releases are cut automatically by [release-please](https://github.com/googleapis/release-please)
on every merge to `main`. Each version section below is generated from
Conventional Commits (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`,
`security:`); manual edits are preserved between releases.

<!-- release-please-start -->
<!-- release-please-end -->

## [Unreleased]

### Added

- _Nothing yet — open a PR with a Conventional Commit title to land here._

## [1.0.0] — 2025-09-30

The first generally-available release of Loop. Stable APIs, SOC 2 Type 2
controls, and a published [docs site](https://docs.loop.example).

### Added

- **Studio**: workspaces, agents, channels, evals, traces, cost dashboard,
  audit-log viewer, BYO-Vault config UI, enterprise-SSO setup form.
- **Gateway**: OpenAI-compatible inference gateway with multi-provider
  routing, retries with budgets, per-tenant rate limits, and offline-eval
  hooks.
- **Eval harness**: golden tests, regression budgets, Pareto-front
  comparisons, JUnit reporters, CI-friendly canary deploy.
- **Memory**: short-term, episodic, and long-term tiers with vector and
  scalar indexes; pluggable KB engine.
- **Tool host**: sandboxed tool execution with PII redaction and audit
  events.
- **Voice + phone**: provisioned numbers, low-latency voice agents.
- **Channels**: Slack, web chat, SMS, voice, email adapters.
- **Control plane**: workspaces, members, roles, SSO (SAML, OIDC), SCIM,
  audit-log export, data-deletion (GDPR Art. 17), BYO-Vault, regional
  deploys, DR runbooks.
- **Docs site**: docs.loop.example v1 with quickstart and three tutorials,
  reviewed by three design partners (S659).
- **Accessibility**: WCAG 2.1 AA gate on the top-10 studio pages (S656).

### Security

- SOC 2 Type 2 controls (S606–S618).
- Audit events for every workspace mutation; INSERT-only RLS on the
  `audit_events` table (S630, S632).
- BYO-Vault credential rotation runbook (S637, RB-024).

### Documentation

- Full architecture corpus under `loop_implementation/` (ADRs, API spec,
  data schema, security, runbooks, performance benchmarks).
- Public docs at <https://docs.loop.example>.

[Unreleased]: https://github.com/kwameasare/loop/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/kwameasare/loop/releases/tag/v1.0.0
