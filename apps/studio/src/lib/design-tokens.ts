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
