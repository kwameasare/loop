/**
 * Design system token map — S655 ga-polish
 *
 * All hardcoded colour/spacing values must be imported from here.
 * Do NOT add raw hex codes, rgb(), or hsl() literals to feature components.
 *
 * CSS-variable tokens (Tailwind theme)
 * ─────────────────────────────────────
 * Use Tailwind utility classes (e.g. `bg-primary`, `text-muted-foreground`)
 * wherever possible. The values below are JavaScript mirrors of the
 * `theme.extend.colors` in tailwind.config.ts, provided for components that
 * must pass colour as a prop (SVG `fill`, `stroke`, Recharts, etc.).
 *
 * Semantic chart / trace tokens
 * ──────────────────────────────
 * These are fixed-palette colours used for data visualisation. They are
 * intentionally NOT CSS variables because they must remain legible across
 * both light and dark mode without re-mapping.
 */

// ─────────────────────────────────────────────────────────────────────────────
// CSS-variable mirrors (keep in sync with tailwind.config.ts)
// ─────────────────────────────────────────────────────────────────────────────

/** Border colour — `border` utility class */
export const COLOR_BORDER = "hsl(var(--border))";
/** Muted foreground — `text-muted-foreground` utility class */
export const COLOR_MUTED_FG = "hsl(var(--muted-foreground))";
/** Primary brand colour — `bg-primary` / `text-primary` utility class */
export const COLOR_PRIMARY = "hsl(var(--primary))";
/** Destructive / error colour — `bg-destructive` utility class */
export const COLOR_DESTRUCTIVE = "hsl(var(--destructive))";
/** Accent surface colour — `bg-accent` utility class */
export const COLOR_ACCENT = "hsl(var(--accent))";
/** Elevated surface colour — `bg-surface-elevated` utility class */
export const COLOR_SURFACE_ELEVATED = "hsl(var(--surface-elevated))";
/** Success colour — `bg-success` utility class */
export const COLOR_SUCCESS = "hsl(var(--success))";
/** Warning colour — `bg-warning` utility class */
export const COLOR_WARNING = "hsl(var(--warning))";
/** Info colour — `bg-info` utility class */
export const COLOR_INFO = "hsl(var(--info))";

// ─────────────────────────────────────────────────────────────────────────────
// Fixed-palette trace span-kind colours
// ─────────────────────────────────────────────────────────────────────────────

/** Sky-500 — server spans */
export const TRACE_SERVER = "#0ea5e9";
/** Violet-500 — client spans */
export const TRACE_CLIENT = "#8b5cf6";
/** Emerald-500 — internal spans */
export const TRACE_INTERNAL = "#10b981";
/** Amber-400 — producer spans */
export const TRACE_PRODUCER = "#f59e0b";
/** Rose-500 — consumer spans */
export const TRACE_CONSUMER = "#f43f5e";

// ─────────────────────────────────────────────────────────────────────────────
// Fixed-palette trace status colours
// ─────────────────────────────────────────────────────────────────────────────

/** Red-500 — error status stroke */
export const TRACE_STATUS_ERROR = "#ef4444";
/** Zinc-200 — unset status stroke */
export const TRACE_STATUS_UNSET = "#d4d4d8";

// ─────────────────────────────────────────────────────────────────────────────
// Fixed-palette chart colours (cost time-series)
// ─────────────────────────────────────────────────────────────────────────────

/** Gray-200 — baseline / grid lines */
export const CHART_GRID = "#e5e7eb";
/** Gray-500 — axis labels */
export const CHART_AXIS_LABEL = "#6b7280";
/** Blue-600 — primary data series */
export const CHART_PRIMARY_SERIES = "#2563eb";

// ─────────────────────────────────────────────────────────────────────────────
// Fixed-palette flow canvas colours
// ─────────────────────────────────────────────────────────────────────────────

/** Zinc-200 — dot-grid pattern fill */
export const FLOW_DOT_GRID = "#d4d4d8";
/** Zinc-700 — selected edge stroke */
export const FLOW_EDGE_SELECTED = "#3f3f46";

// ─────────────────────────────────────────────────────────────────────────────
// Spacing scale mirrors (Tailwind rem → px at 16 px/rem base)
// Use Tailwind utility classes (e.g. `p-4`, `gap-6`) instead of these
// in JSX. These exist only for components that need numeric pixel values
// (e.g. SVG layout calculations).
// ─────────────────────────────────────────────────────────────────────────────

/** 4 px — tw: p-1 */
export const SPACE_1 = 4;
/** 8 px — tw: p-2 */
export const SPACE_2 = 8;
/** 12 px — tw: p-3 */
export const SPACE_3 = 12;
/** 16 px — tw: p-4 */
export const SPACE_4 = 16;
/** 24 px — tw: p-6 */
export const SPACE_6 = 24;
/** 32 px — tw: p-8 */
export const SPACE_8 = 32;

// ─────────────────────────────────────────────────────────────────────────────
// Canonical target UX grammar
// ─────────────────────────────────────────────────────────────────────────────

export const OBJECT_STATES = [
  "draft",
  "saved",
  "staged",
  "canary",
  "production",
  "archived",
] as const;

export type ObjectState = (typeof OBJECT_STATES)[number];

export const OBJECT_STATE_TREATMENTS: Record<
  ObjectState,
  {
    label: string;
    shape: "dash" | "dot" | "ring" | "triangle" | "square" | "archive";
    className: string;
    textClassName: string;
  }
> = {
  draft: {
    label: "Draft",
    shape: "dash",
    className: "border-border bg-state-draft text-foreground",
    textClassName: "text-muted-foreground",
  },
  saved: {
    label: "Saved",
    shape: "square",
    className: "border-border bg-state-saved text-foreground",
    textClassName: "text-foreground",
  },
  staged: {
    label: "Staged",
    shape: "dot",
    className: "border-info bg-info/10 text-info",
    textClassName: "text-info",
  },
  canary: {
    label: "Canary",
    shape: "triangle",
    className: "border-warning bg-warning/10 text-warning",
    textClassName: "text-warning",
  },
  production: {
    label: "Production",
    shape: "ring",
    className: "border-success bg-success/10 text-success",
    textClassName: "text-success",
  },
  archived: {
    label: "Archived",
    shape: "archive",
    className: "border-border bg-muted text-muted-foreground",
    textClassName: "text-muted-foreground",
  },
};

export const TRUST_STATES = [
  "healthy",
  "watching",
  "drifting",
  "degraded",
  "blocked",
] as const;

export type TrustState = (typeof TRUST_STATES)[number];

export const TRUST_STATE_TREATMENTS: Record<
  TrustState,
  {
    label: string;
    shape: "check" | "eye" | "tilt" | "pulse" | "stop";
    className: string;
  }
> = {
  healthy: {
    label: "Healthy",
    shape: "check",
    className: "border-success bg-success/10 text-success",
  },
  watching: {
    label: "Watching",
    shape: "eye",
    className: "border-info bg-info/10 text-info",
  },
  drifting: {
    label: "Drifting",
    shape: "tilt",
    className: "border-warning bg-warning/10 text-warning",
  },
  degraded: {
    label: "Degraded",
    shape: "pulse",
    className: "border-warning bg-warning/15 text-warning",
  },
  blocked: {
    label: "Blocked",
    shape: "stop",
    className: "border-destructive bg-destructive/10 text-destructive",
  },
};

export const CONFIDENCE_LEVELS = ["high", "medium", "low", "unsupported"] as const;

export type ConfidenceLevel = (typeof CONFIDENCE_LEVELS)[number];

export const CONFIDENCE_TREATMENTS: Record<
  ConfidenceLevel,
  { label: string; barClassName: string; textClassName: string }
> = {
  high: {
    label: "High confidence",
    barClassName: "bg-success",
    textClassName: "text-success",
  },
  medium: {
    label: "Medium confidence",
    barClassName: "bg-info",
    textClassName: "text-info",
  },
  low: {
    label: "Low confidence",
    barClassName: "bg-warning",
    textClassName: "text-warning",
  },
  unsupported: {
    label: "Unsupported",
    barClassName: "bg-destructive",
    textClassName: "text-destructive",
  },
};

export const TRACE_SPAN_SHAPES = {
  server: "rounded",
  client: "notched",
  internal: "solid",
  producer: "triangle",
  consumer: "split",
} as const;

export const MOTION_TOKENS = {
  flash: "var(--duration-flash)",
  swift: "var(--duration-swift)",
  standard: "var(--duration-standard)",
  gentle: "var(--duration-gentle)",
  standardEase: "var(--ease-standard)",
  emphasizedEase: "var(--ease-emphasized)",
} as const;

export const DENSITY_TOKENS = {
  compact: {
    rowClassName: "min-h-8 gap-2 px-2 py-1 text-sm",
    controlClassName: "h-8 rounded-md px-2 text-sm",
  },
  comfortable: {
    rowClassName: "min-h-10 gap-3 px-3 py-2 text-sm",
    controlClassName: "h-10 rounded-md px-3 text-sm",
  },
  presentation: {
    rowClassName: "min-h-12 gap-4 px-4 py-3 text-base",
    controlClassName: "h-11 rounded-md px-4 text-base",
  },
} as const;
