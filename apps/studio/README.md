# @loop/studio

Loop's agent control plane UI — Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui primitives.

## Scripts

| Command | What it does |
|---|---|
| `pnpm dev` | Run the dev server on http://localhost:3001 |
| `pnpm build` | Production build (used by CI) |
| `pnpm lint` | next lint |
| `pnpm test` | Vitest run (jsdom + Testing Library) |
| `pnpm format` | Prettier write |

## Layout

```
src/
  app/                  # App Router routes
    layout.tsx          # Root layout (font + globals)
    page.tsx            # Home placeholder
    globals.css         # Tailwind + design tokens
  components/
    ui/                 # shadcn-style primitives (button, …)
  lib/
    utils.ts            # cn() class merger
```

The skeleton wires:

- shadcn-style design tokens (CSS variables in `globals.css`)
- Tailwind config consuming those tokens
- One reference primitive (`Button`) with `cva` variants
- Vitest + Testing Library + jsdom

Feature surfaces (agent list, conversation explorer, eval dashboard, …)
land in stories S025–S036 — see `loop_implementation/tracker/TRACKER.md`.
