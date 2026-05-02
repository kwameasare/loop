# Studio Design System

> Version: **1.0** (S655 ga-polish)  
> Owner: Frontend Platform  
> Tailwind config: `apps/studio/tailwind.config.ts`  
> Token source: `apps/studio/src/lib/design-tokens.ts`

---

## Overview

The Studio design system is built on [shadcn/ui](https://ui.shadcn.com/) conventions
with Tailwind CSS for utility-first styling. All colours and spacings are expressed via
one of three mechanisms, in order of preference:

1. **Tailwind utility classes** — use for all layout, typography, and colour work in JSX.
2. **CSS-variable tokens** — available in JavaScript as `hsl(var(--token))` strings,
   mirrored in `design-tokens.ts` for components that need to pass colour as a prop.
3. **Fixed-palette tokens** — for data-visualisation components (charts, trace waterfall)
   where colours must be stable across themes. Also defined in `design-tokens.ts`.

---

## Token Map

### CSS-variable tokens (`tailwind.config.ts → theme.extend.colors`)

| Token name         | CSS variable              | Tailwind utility               |
| ------------------ | ------------------------- | ------------------------------ |
| `background`       | `--background`            | `bg-background`                |
| `foreground`       | `--foreground`            | `text-foreground`              |
| `muted`            | `--muted`                 | `bg-muted`                     |
| `muted-foreground` | `--muted-foreground`      | `text-muted-foreground`        |
| `primary`          | `--primary`               | `bg-primary` / `text-primary`  |
| `primary-foreground` | `--primary-foreground`  | `text-primary-foreground`      |
| `border`           | `--border`                | `border-border`                |

Border-radius tokens: `--radius` → `rounded-lg`, `rounded-md`, `rounded-sm`.

---

### Fixed-palette tokens (`src/lib/design-tokens.ts`)

#### Trace span-kind colours

| Export               | Value     | Meaning              |
| -------------------- | --------- | -------------------- |
| `TRACE_SERVER`       | `#0ea5e9` | Server spans (sky-500) |
| `TRACE_CLIENT`       | `#8b5cf6` | Client spans (violet-500) |
| `TRACE_INTERNAL`     | `#10b981` | Internal spans (emerald-500) |
| `TRACE_PRODUCER`     | `#f59e0b` | Producer spans (amber-400) |
| `TRACE_CONSUMER`     | `#f43f5e` | Consumer spans (rose-500) |

#### Trace status colours

| Export                | Value     | Meaning                  |
| --------------------- | --------- | ------------------------ |
| `TRACE_STATUS_ERROR`  | `#ef4444` | Error status stroke (red-500) |
| `TRACE_STATUS_UNSET`  | `#d4d4d8` | Unset status stroke (zinc-200) |

#### Chart colours (cost time-series)

| Export                | Value     | Meaning                    |
| --------------------- | --------- | -------------------------- |
| `CHART_GRID`          | `#e5e7eb` | Grid / baseline lines (gray-200) |
| `CHART_AXIS_LABEL`    | `#6b7280` | Axis label text (gray-500) |
| `CHART_PRIMARY_SERIES`| `#2563eb` | Primary data series (blue-600) |

#### Flow canvas colours

| Export              | Value     | Meaning                       |
| ------------------- | --------- | ----------------------------- |
| `FLOW_DOT_GRID`     | `#d4d4d8` | Dot-grid background (zinc-200) |
| `FLOW_EDGE_SELECTED`| `#3f3f46` | Selected edge stroke (zinc-700) |

---

## Spacing Scale

Use Tailwind spacing utilities (`p-4`, `gap-6`, etc.) in JSX. For SVG
layout calculations that need numeric pixel values, import from `design-tokens.ts`:

| Export    | Value  | Tailwind equivalent |
| --------- | ------ | ------------------- |
| `SPACE_1` | 4 px   | `p-1` / `gap-1`     |
| `SPACE_2` | 8 px   | `p-2` / `gap-2`     |
| `SPACE_3` | 12 px  | `p-3` / `gap-3`     |
| `SPACE_4` | 16 px  | `p-4` / `gap-4`     |
| `SPACE_6` | 24 px  | `p-6` / `gap-6`     |
| `SPACE_8` | 32 px  | `p-8` / `gap-8`     |

---

## Compliance Rule

The CI `design-system audit` test (`src/lib/design-tokens.test.ts`) asserts
that **fewer than 5 raw hex literals** (`#rrggbb`) appear outside of
`design-tokens.ts` itself. This keeps the token surface small and trackable.

---

## Adding a New Token

1. Add the export to `src/lib/design-tokens.ts` with a JSDoc comment explaining
   the semantic meaning and its Tailwind nearest-equivalent.
2. Update the table in this document.
3. Use the token in your component — never inline the hex value.

---

## References

- [tailwind.config.ts](../apps/studio/tailwind.config.ts)
- [src/lib/design-tokens.ts](../apps/studio/src/lib/design-tokens.ts)
