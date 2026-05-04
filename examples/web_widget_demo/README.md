# Web Widget Demo

This page is a tiny playground for the web channel widget exported by `packages/channels/web-js`.

## Prerequisites

1. Start control plane (CP) locally.
2. Start data plane (DP) locally.
3. Build the web widget package so `dist/` exists:

```bash
pnpm -C packages/channels/web-js install --frozen-lockfile
pnpm -C packages/channels/web-js build
```

## Run the demo

Open the file directly in your browser:

```bash
open examples/web_widget_demo/index.html
```

Then set:

- `Control Plane URL` (for CP-hosted invoke)
- `Data Plane URL` (optional; when set, the demo points widget traffic directly at DP)
- `Agent ID`
- optional bearer token

Click `Render widget` to reload with the new config.

## CI smoke

A Playwright smoke test validates that this demo page loads and renders the widget shell:

- `apps/studio/e2e/web-widget-demo.spec.ts`
