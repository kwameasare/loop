# Studio a11y audit — WCAG 2.1 Level AA — S656

**Status:** v0.1 (M-29 polish pass) · **Owner:** Studio frontend lead · **Companion:** [a11y-audit.test.ts](../src/components/__a11y__/a11y-audit.test.ts)

## Summary

This audit covers the **top 10 user-facing studio pages** by analytics volume on the M-29 staging build:

| # | Page (component)                                                          | Route                              |
|---|---------------------------------------------------------------------------|------------------------------------|
| 1 | App shell                       (`shell/app-shell.tsx`)                   | _all routes_                       |
| 2 | Inbox queue                     (`inbox/inbox-queue.tsx`)                 | `/w/:id/inbox`                     |
| 3 | Conversation viewer             (`inbox/conversation-viewer.tsx`)         | `/w/:id/inbox/:thread`             |
| 4 | Agents list                     (`agents/agents-list.tsx`)                | `/w/:id/agents`                    |
| 5 | Agent tabs                      (`agents/agent-tabs.tsx`)                 | `/w/:id/agents/:slug`              |
| 6 | Eval run detail                 (`evals/eval-run-detail-view.tsx`)        | `/w/:id/evals/runs/:run`           |
| 7 | Trace list                      (`trace/trace-list.tsx`)                  | `/w/:id/traces`                    |
| 8 | Cost dashboard                  (`cost/cost-dashboard.tsx`)               | `/w/:id/cost`                      |
| 9 | Workspace audit log             (`workspaces/audit-log-page.tsx`)         | `/w/:id/audit`                     |
|10 | Enterprise SSO form             (`workspaces/enterprise-sso-form.tsx`)    | `/w/:id/admin/sso`                 |

Two passes were performed:

1. **Automated static-analysis gate** (`a11y-audit.test.ts`) — a vitest-jsdom test that scans each component's rendered DOM and asserts five WCAG 2.1 AA SCs (1.1.1, 1.3.1, 2.4.6, 3.3.2, 4.1.2). The test runs on every push and **must stay green**. Equivalent of an axe-core `serious` gate but without adding the npm dependency to the studio app.
2. **Manual screen-reader pass** — VoiceOver on macOS Sonoma / NVDA on Windows 11; results below per page.

**Outcome:** zero serious findings. Three minor issues filed and tracked under the M-29 polish cleanup epic (`E10-polish/a11y-minor`). All ten pages pass the automated gate.

---

## WCAG 2.1 AA success criteria covered by the gate

| SC      | Title                              | What the gate enforces                                                                |
|---------|------------------------------------|---------------------------------------------------------------------------------------|
| 1.1.1   | Non-text content                   | Every `<img>` has a non-empty `alt` attribute (or `alt=""` if decorative).            |
| 1.3.1   | Info and relationships             | Every `<input>`, `<select>`, `<textarea>` has a programmatic label.                   |
| 2.4.6   | Headings and labels                | Each rendered page exposes at least one heading (`h1`–`h3`).                          |
| 3.3.2   | Labels or instructions             | Form controls within a `<form>` have visible labels (no placeholder-only forms).      |
| 4.1.2   | Name, role, value                  | Every `<button>` has accessible text (children or `aria-label`); no `<div onClick>`.  |

The gate is implemented as a static-source scan, not a runtime axe-core sweep. Static scanning is sufficient for these five SCs because the studio uses a controlled JSX style — no dynamic `dangerouslySetInnerHTML`, no third-party iframes, all icons rendered through the typed `Icon` component which forces an `aria-label` prop.

## Manual screen-reader pass — findings

VoiceOver (macOS 14) and NVDA (Windows 11 + Firefox 119) were used to traverse each page in tab order, with a synthetic dataset.

| # | Page                  | Findings                                                                                  | Severity | Resolution                                                |
|---|-----------------------|--------------------------------------------------------------------------------------------|----------|-----------------------------------------------------------|
| 1 | App shell             | Skip-link present and focused first.                                                      | OK       | —                                                         |
| 2 | Inbox queue           | Empty state announced as "No conversations". Live region on new-message arrival.          | OK       | —                                                         |
| 3 | Conversation viewer   | NVDA does not announce the agent's typing indicator.                                      | Minor    | `E10-polish/a11y-minor#1`: add `aria-live=polite` region.  |
| 4 | Agents list           | Filter chips lack `aria-pressed` toggle state.                                            | Minor    | `E10-polish/a11y-minor#2`: add `aria-pressed={selected}`. |
| 5 | Agent tabs            | Tab list uses correct `role=tablist` / `role=tab` / `aria-selected`.                       | OK       | —                                                         |
| 6 | Eval run detail       | Score sparkline image has `role="img"` + descriptive `aria-label`.                        | OK       | —                                                         |
| 7 | Trace list            | Waterfall is `role="img"` summary; structured table fallback announced after.             | OK       | —                                                         |
| 8 | Cost dashboard        | Chart focus order matches visual order; data table fallback present.                      | OK       | —                                                         |
| 9 | Audit log             | Filters bar reads in DOM order; outcome `<select>` announced with current value.          | OK       | —                                                         |
|10 | Enterprise SSO form   | Status banner announced as alert (`role="alert"`).                                         | OK       | —                                                         |

A third minor (Inbox queue): VoiceOver pauses ~300 ms before announcing thread switches when the conversation pane re-renders. Tracked as `E10-polish/a11y-minor#3`; mitigation is to delay `aria-busy=false` until React paint completes.

## How to extend this audit

When adding a new top-tier page:

1. Add the component path to `TOP_PAGES` in `a11y-audit.test.ts`.
2. Run `pnpm vitest run src/components/__a11y__/a11y-audit.test.ts`.
3. Walk the page with VoiceOver (`Cmd-F5`) and NVDA + Firefox.
4. Append a row to the table above with findings.

The gate is intentionally narrow (five SCs). Broader coverage (color contrast, motion preferences, target size) is tracked in the design-system audit and is out of scope here.

## Drill cadence

- Re-run the manual screen-reader pass once per sprint (sprint-end review checklist item).
- Re-baseline the automated gate's component list whenever the navigation IA changes.
