# Legacy Implementation UX Baseline - Loop Studio

**Status:** LEGACY IMPLEMENTATION BASELINE. Superseded as the target UX standard by [`00_CANONICAL_TARGET_UX_STANDARD.md`](00_CANONICAL_TARGET_UX_STANDARD.md).
**Owner:** Founding Eng #5 (Studio) + Designer
**Companion files:** `architecture/ARCHITECTURE.md` (system), `api/openapi.yaml` (data shapes)

**Canonical target:** [`00_CANONICAL_TARGET_UX_STANDARD.md`](00_CANONICAL_TARGET_UX_STANDARD.md) is the true UX/UI standard. This file remains useful only as a historical implementation baseline and near-term detail reference where it does not conflict with the canonical target.

This document defines the UX of Loop Studio — the web-based debugger and operator surface — and the design system that supports it. Studio is **not** a flow editor; it is a debugger first, operator console second, and (much later) optional flow visualizer.

---

## 1. Design principles

1. **Engineers first.** The primary user writes Python in their own editor. Studio reads, observes, and helps debug. It does not replace the editor.
2. **Trace-centric.** Every screen can lead the user to a trace. The trace view is the most important screen in the entire product.
3. **No drag-and-drop flow editor.** That ship has sailed.
4. **Show numbers, not vibes.** Every cost, latency, and quality metric is visible per turn, per agent, per workspace.
5. **Respect dense data.** Engineers tolerate density better than non-technical users; we lean dense over sparse.
6. **Keyboard-first.** Every screen has shortcuts. `?` shows them.
7. **Dark mode is default.** Light mode is fully supported.

---

## 2. Information architecture

```
Studio (workspace-scoped)
│
├── Home              — recent activity, alerts, what changed today
│
├── Agents
│   ├── List          — table of agents with health/cost/latency badges
│   └── Detail
│       ├── Overview        — current version, channels, KBs, tools
│       ├── Conversations   — paginated list of recent conversations
│       │   └── Conversation Detail → Trace
│       ├── Versions        — deploy history, eval status, rollback
│       ├── Evals           — suites, runs, regressions
│       ├── Cost            — per-agent rollup, models, channels
│       └── Settings        — channel configs, KB grants, MCP grants, budgets
│
├── Knowledge Bases
│   ├── List
│   └── Detail        — sources, ingestion status, search test, chunk inspector
│
├── MCP / Tools       — installed servers, manifest, install from Hub
│
├── Eval Registry     — public + internal suites
│
├── Operator Inbox    — HITL queue: escalations, agent-flagged, takeover history
│
├── Usage             — workspace-wide cost & limits dashboard
│
└── Settings
    ├── Members & roles
    ├── API keys
    ├── Secrets
    ├── Audit log
    ├── SSO (Enterprise)
    └── Billing
```

---

## 3. Screen-by-screen

### 3.1 Home (workspace dashboard)

**Purpose:** within 3 seconds the user knows what's healthy, what's broken, what's expensive.

**Layout (16-col grid, 1440px reference width):**
- Top row: 4 stat tiles (active conversations 24h · spend today · failed turns 24h · open escalations).
- Mid row: line chart "spend & turns over last 14 days" (left, 10 cols) + activity feed (right, 6 cols).
- Bottom row: deployments today + eval regressions + recent errors.

**States:**
- Empty (no agents): big CTA "Create your first agent" with `loop init` instructions.
- Healthy: green stat tiles, sparse activity.
- Alerts: red border on relevant tiles, top banner.

### 3.2 Agents — list

Table with: Name · Channels (icons) · Active version · Last 24h turns · p50 latency · Error rate · Today's spend · Status. Column header click sorts; filter chips for channel and status.

Row hover: quick actions (open detail, view conversations, replay last failed turn).

### 3.3 Agents — detail · Conversations tab

Two-pane layout:
- **Left (30%):** virtualized list of conversations. Columns: User · Channel · Last msg snippet · Status · Time. Filter chips: time range, channel, status (active/escalated/closed/error), confidence threshold, cost threshold. Search across content (server-side).
- **Right (70%):** when a row is selected, the conversation detail loads.

Conversation detail panel:
- Header: user ID, channel, started, total cost, total tokens, status, **Take over** button (HITL).
- Message stream: chronological. Each turn shows role badge (user/agent/tool/operator), content, and a toolbar:
  - **▶ Replay** (re-run with optional knob changes)
  - **🔍 Trace** (open trace drawer)
  - **🐛 Add to eval** (creates an eval case from this turn)
  - **💬 Comment** (operator/team annotation)
- Inline tool-call cards: collapsible, show args/result/latency/cost.
- Inline retrieval cards: list of cited chunks with byte ranges, confidence scores, link back to source.

### 3.4 Trace view (the most important screen)

Open as a drawer or full screen. Three regions:

**(a) Waterfall** (top, ~30% height): horizontal time bars per span. Color-coded by span kind:
- LLM (teal)
- Tool (coral)
- Retrieval (purple)
- Memory (slate)
- Channel (gray)

Click a span → focuses the detail pane.

**(b) Span detail** (middle, ~40% height): tabbed:
- **Inputs/Outputs** — full prompt, response (with token counts), tool args/result.
- **Attrs** — all OTel attrs as a key/value table.
- **Cost** — input tokens × in-rate + output tokens × out-rate + tool surcharges.
- **Logs** — structured log events from this span.

**(c) Replay** (bottom, ~30% height): inline form to re-run this turn with knobs:
- Model swap (dropdown of available model aliases)
- Temperature
- Tool subset (toggle individual tools off)
- Memory state (lock to historical, or use latest)

Result of replay opens a **side-by-side diff** with the original turn — token diff, response diff, cost diff, latency diff, eval scorer diff if applicable.

### 3.5 Agents — detail · Versions tab

Timeline (vertical) of versions. Each entry:
- Version number, deploy state (active/canary/inactive/rolled back), eval status badge, deployer, timestamp.
- Click to expand → diff to previous version (config + code hash; full code if attached), eval run summary, channel rollout %.
- Actions: **Promote** (canary → active), **Rollback** (active → previous version), **Re-run evals**.

Header: "Active: v17 (deployed 2h ago by @alice). Canary: v18 (10% traffic, eval passed)."

### 3.6 Agents — detail · Evals tab

Two views:
- **Suites:** list of suites attached. Click → suite detail (cases, last run, regression chart over time).
- **Runs:** chronological list of runs with pass/fail badge and per-scorer score deltas.

Suite detail:
- Cases table with last score per case.
- Regressed cases badged red.
- "Add case from production" button (drops user into the conversation list filtered to recent failures).

### 3.7 Agents — detail · Cost tab

- Header: today's spend, MTD spend, projected EOM, cap status (soft/hard).
- Stacked bar chart: 30 days, segmented by LLM provider, tools, compute.
- Drill-down table by model alias, by channel, by hour-of-day.
- Cost cap controls: edit soft / hard / degrade rules inline.

### 3.8 Knowledge Bases — detail

- Source list (URL, file, Notion, etc.) with ingestion status.
- "Add source" button opens a modal with type-specific forms.
- Search test panel: type a query, see top-k results with scores, highlighted matches, byte ranges, link to source.
- Chunk inspector: select a doc, browse its chunks, see embeddings (PCA preview), edit/delete chunks.
- Vision-indexed pages: thumbnail of page + extracted structured text side-by-side.

### 3.9 Operator Inbox (HITL)

The page operators (humans) live in.

- Left rail: queues — All · Escalated · Confidence-flagged · Tool-failed · Manual review.
- Center: table of active conversations needing attention. Columns: User · Agent · Channel · Why escalated · Time waiting · SLA badge.
- Right: when a conversation is selected, full detail with the same conversation+trace UI as 3.3, plus operator-mode message composer at the bottom. Operator can type as themselves or "draft as agent" (LLM drafts a response, operator approves/edits/sends).

### 3.10 Usage dashboard

- Workspace-wide spend over time.
- Stacked by agent, channel, model.
- Budget bars: daily, monthly, projected.
- Per-line-item drill: WhatsApp message cost, Twilio voice minutes, OpenAI tokens, etc.

### 3.11 Settings — Audit log

Append-only log of admin actions:
- Member invited / removed / role changed.
- API key created / revoked / used.
- Secret created / rotated / accessed.
- Agent deployed / promoted / rolled back.
- Budget changed.
- Eval gating overridden.

Each entry: actor, action, target, timestamp, IP, user agent. Exportable as CSV; SOC2 evidence.

---

## 4. Component library

We use **shadcn/ui** (Radix + Tailwind) as the base. Custom components on top:

| Component | Purpose |
|-----------|---------|
| `<TraceWaterfall />` | The waterfall in §3.4(a) |
| `<SpanCard />` | Compact span representation in lists |
| `<ConversationStream />` | Threaded message+tool+retrieval card list |
| `<ToolCallCard />` | Collapsible tool args/result/latency/cost |
| `<RetrievalCard />` | Cited chunks with byte ranges and source links |
| `<CostBadge cost />` | $0.0042 with hover tooltip showing token math |
| `<LatencyBadge ms />` | p50 indicator with color thresholds |
| `<ConfidenceBar value />` | 0–1 retrieval confidence |
| `<DiffPane left right />` | Side-by-side replay diff |
| `<EvalScoreCell />` | Score with sparkline of last 10 runs |
| `<ReplayForm />` | Inline knobs for re-running a turn |
| `<ChannelIcon type />` | Brand-correct icon for each channel |
| `<HITLEscalateBanner />` | Top-of-conversation banner when an operator takes over |

---

## 5. Design tokens

Colors and tokens are exposed as CSS variables in the Studio app and as a JSON token file for any external partners who skin Loop.

### 5.1 Dark mode (primary) & light mode (secondary)

#### Dark tokens (the default)

| Role | CSS variable | Hex | Usage |
|------|--------------|-----|-------|
| `--color-bg-primary` | `#0F1E3A` | Deep navy | Page chrome, headers (dark mode) |
| `--color-bg-secondary` | `#0A1428` | Navy deep | Sidebar, modals, cards (dark mode) |
| `--color-bg-tertiary` | `#1E293B` | Slate-dark | Hover states, selected rows |
| `--color-text-primary` | `#F1F5F9` | Off-white | Primary text on dark |
| `--color-text-secondary` | `#CBD5E1` | Slate-light | Muted text, metadata |
| `--color-border` | `#334155` | Slate-dk | Dividers, input borders |
| `--color-accent` | `#14B8A6` | Teal | Links, active states, primary CTAs |
| `--color-accent-soft` | `#5EEAD4` | Teal-light | Badge tints, hover states |
| `--color-pop` | `#F97316` | Orange | Errors, regressions, warnings |
| `--color-pop-soft` | `#FED7AA` | Orange-light | Alert backgrounds |
| `--color-success` | `#10B981` | Emerald | Success states, passed evals |

#### Light mode overrides

When `prefers-color-scheme: light` or `.light-mode` class is active:

| Variable | Light override | Usage |
|----------|---|---------|
| `--color-bg-primary` | `#FFFFFF` | Page bg |
| `--color-bg-secondary` | `#F8FAFC` | Paper | Sidebar, cards |
| `--color-text-primary` | `#1E293B` | Slate-dark | Readable on light |
| `--color-text-secondary` | `#64748B` | Slate | Muted text |
| `--color-border` | `#E2E8F0` | Slate-light | Subtle dividers |

### 5.2 Color palette (legacy)

Loop's identity is **deep navy + teal accent + warm coral pop** — the same palette as the pitch deck, deliberately. The product feels like the brand promised.

| Role | Hex | Usage |
|------|-----|-------|
| Brand primary | `#0F1E3A` | Page chrome, headers, primary buttons (dark mode bg) |
| Brand deep | `#0A1428` | Sidebar, modals (dark mode) |
| Accent | `#14B8A6` | Active state, links, success, primary CTAs |
| Accent soft | `#5EEAD4` | Subtle accent on dark, badge tints |
| Pop | `#F97316` | Errors, regressions, "needs attention" |
| Slate | `#64748B` | Muted text, disabled, dividers |
| Slate-DK | `#334155` | Body text on light bg |
| Paper | `#F8FAFC` | Light mode bg |
| White | `#FFFFFF` | Surfaces |

Span color codes for the trace waterfall:
- LLM → `#14B8A6` (accent)
- Tool → `#F97316` (pop)
- Retrieval → `#A78BFA`
- Memory → `#64748B`
- Channel → `#94A3B8`

### 5.2 Typography

- UI font: **Inter** (system fallback: -apple-system, system-ui, Segoe UI, Roboto).
- Mono font: **JetBrains Mono** (for code, JSON, traces, IDs).
- Sizes (rem):
  - 0.75 (xs): metadata, badges
  - 0.875 (sm): body small
  - 1.0 (base): body
  - 1.125 (lg): emphasized body
  - 1.25 (xl): section headings
  - 1.5 (2xl): page subtitles
  - 1.875 (3xl): page titles
  - 2.25 (4xl): hero stats

### 5.3 Spacing & layout

- 8-pt grid. Spacings: 4, 8, 12, 16, 24, 32, 48, 64.
- Page max-width: 1440px on standard screens; full-width on dashboard tables.
- Sidebar width: 240px collapsed-state 64px.
- Panel breakpoints: lg≥1024, xl≥1280, 2xl≥1536.

### 5.4 Radius & elevation

- Radius: 4 (subtle), 8 (default), 12 (cards), 16 (modals), 9999 (pills).
- Elevation (box-shadow): 0 (flat), 1 (hover), 2 (dropdown), 3 (modal), 4 (toast).

### 5.5 Copy & voice guide

**Tone:** Direct, confident, jargon-lite. Engineers are users; we don't patronize.

**Voice principles:**
- Action-oriented: "Promote to production" not "Would you like to consider promoting?"
- Specific: "Cost cap hit; agent switched to gpt-3.5-turbo" not "Something happened."
- Bilingual where possible: all UI labels in English; docs/API in English + one additional language (TBD).

**Dos & don'ts:**
- DO: use "agent", "turn", "trace", "workspace", "conversation" as defined in the glossary.
- DO: call errors by their names: "idempotency_key_reused" not "something went wrong."
- DON'T: use emoji in UI copy (we're a debugger, not Slack).
- DON'T: use "please" in error messages; say what broke and how to fix it.

**Examples:**
- Button: "Deploy v18" (not "Begin deployment process")
- Error: "Invalid OpenAI key: test mode but sandbox not configured" (not "Error")
- Success: "Promoted v18 to 100% production traffic" (not "Done!")

### 5.6 Error-state copy library

| Condition | Exact copy | Fallback action |
|-----------|-----------|-----------------|
| Conversation not found | "This conversation cannot be loaded. It may have expired or been deleted. Return to the [conversations list](#)." | Show list view |
| Trace not available | "Trace data not yet available. If the turn completed ≥5 seconds ago, check [OTLP pipeline status](settings/diagnostics)." | Check health dashboard |
| Workspace over hard budget | "Hard budget cap hit ($500.00 / month). New conversations return 'budget exhausted' error. [Increase budget or resolve immediately?](#)" | Link to budgets screen |
| Tool invocation timeout | "Tool 'lookup_order' did not respond within 60s. Agent received error and continued. [View logs](#)." | Link to diagnostics |
| Session memory over 16 MB | "Session memory (18.3 MB) exceeds hard cap. Oldest entries evicted. [Review memory policy](#)." | Settings link |
| LLM provider unavailable | "OpenAI is experiencing outages. Auto-failover to Anthropic engaged. Cost & latency may increase. [Status page](https://status.openai.com)." | External status link |

### 5.7 Notification / toast catalog

Rendered top-right, stacked; auto-dismiss per type except "critical" (manual).

| Type | Icon | Color | Duration | Actions | Example |
|------|------|-------|----------|---------|---------|
| **Success** | ✓ | Emerald | 4s | None | "Agent v42 deployed to 10% canary." |
| **Info** | ℹ | Teal | 6s | Learn more | "New eval suite available: support-v2." |
| **Warning** | ⚠ | Orange | 8s | Dismiss, Action | "Cost trending +120% vs. baseline. [View trend](#)?" |
| **Error** | ✕ | Red | 10s | Dismiss, Retry | "Trace ingestion lag >30s. [Retry](#)?" |
| **Critical** | ⚠ | Red + bold | ∞ | Acknowledge | "Workspace breach detected. Contact support." |

### 5.8 Empty state catalog (per major screen)

| Screen | Illustration | Copy | CTA |
|--------|--------------|------|-----|
| **Agents list (no agents)** | Logo + CLI | "No agents yet. Create your first agent: `loop init --workspace <id>`" | Copy command |
| **Conversations (agent selected, empty)** | Chat bubble outline | "No conversations yet. Send a message to your agent." | (none — wait for message) |
| **Traces (turn selected, no trace)** | Stopwatch outline | "Trace data not yet available. Traces appear 5+ seconds after a turn completes." | (none — refresh in 5s) |
| **KB documents (KB created, no docs)** | Document stack | "No documents yet. [Add a source](#): URL, file, or Notion workspace." | Add source |
| **Eval results (suite created, no runs)** | Checkmark outline | "No eval runs yet. Deploy an agent version to trigger evaluation." | (none — wait for deploy) |
| **Operator inbox (no escalations)** | Inbox zero | "All quiet. No escalated conversations." | (none — background) |
| **Usage / cost dashboard (no activity)** | Chart outline | "Cost data appears after your first conversation." | (none — wait) |

### 5.9 Loading state patterns

**Don't use generic spinners.** The hierarchy of loading:

1. **Skeleton screens** — for list views (conversations, agents, traces). Use 3–5 placeholder cards, same proportions as real content.
2. **Progressive disclosure** — for panels. Render text immediately (with light gray text-color), stream in data fields as they load.
3. **Waterfall animation** — for the trace waterfall view specifically. Show time axis immediately; bars animate in as they arrive.
4. **Placeholder text** — for single values: "Loading..." in same font size & color as the final value (ensures no layout shift).

**Never use a full-page spinner.** Always show partial content.

### 5.10 Icon usage policy

**Filled vs. outlined:**
- Outlined (24px default): navigation, actions, neutralitem selection (unchecked checkbox).
- Filled: active state indicators, selected items (checked, active nav).
- Brand icons only in specific contexts: Loop logo (top-left), channel icons (web/WhatsApp/Slack badges).

**Generic vs. domain-specific:**
- Use Heroicons (open-source) as the default system icon set.
- Domain icons (Trace waterfall colors, LLM provider logos) are custom SVGs.
- Tool-call icons sourced from tool manifests (MCP servers declare their icon URL).

| Icon | When | Example |
|------|------|---------|
| ChevronDown | Dropdown/expand | Agent name next to status |
| Plus | Add / create | "Add source" button in KB |
| Trash | Delete | Row action to remove conversation |
| Copy | Duplicate / copy to clipboard | Copy conversation ID |
| Eye / EyeOff | Show / hide | Reveal API key |
| Clock | History / time | Versions timeline |
| Zap | Active / performance | Latency badge |

### 5.11 Avatar & initial fallback

- Render user avatar from Auth0 / Kratos + initials fallback.
- Initials: first letter of first name + first letter of last name, capitalized. If only one name, use first two letters.
- Background color: hash(email) mod 12 colors from the palette (deterministic, rainbow-ish, no boring grays).
- Font: Inter, semibold, white text, 14px.
- Size: 32px default, 24px in tables, 40px in account menu.

### 5.12 Table density modes

**Three modes, selectable per-screen in the view menu:**

| Mode | Padding | Font size | Line height | Use when |
|------|---------|-----------|-------------|----------|
| **Compact** | 4px vertical | sm (0.875) | 1.25 | Many rows (50+), scanning for one item |
| **Normal** | 8px vertical | base (1.0) | 1.5 | Default; balanced readability + density |
| **Comfortable** | 12px vertical | base | 1.75 | Few rows (<20), emphasis on each item |

All modes sort by clicking headers; filter chips work identically.

### 5.13 Internationalization plan (I18n)

**MVP scope (month 6):** English only, with infrastructure for expansion.

| Component | Strategy | Notes |
|-----------|----------|-------|
| **UI text** | i18next + React library | JSON translation files per language; fallback to EN |
| **Numbers** | `Intl.NumberFormat` | Locale-aware grouping: 1,000 (EN) vs. 1.000 (DE) |
| **Currency** | `Intl.NumberFormat` + workspace locale | $0.0042 or €0,0042 based on workspace region setting |
| **Dates / times** | `Intl.DateTimeFormat` | 4/29/2026 (EN-US) vs. 29/4/2026 (EN-GB) vs. 2026-04-29 (ISO) |
| **RTL languages** | CSS logical properties (`inset-inline`, `padding-inline`) | Month 9 expansion (Arabic, Hebrew) |
| **Error messages** | String keys, not hardcoded | `i18n.t('error.idempotency_reused')` → error list mapped per language |

**Launch languages:** EN, ES (month 7), FR (month 8), DE (month 8), JA (month 9).

### 5.14 Accessibility checklist per component

| Component | WCAG target | Checklist |
|-----------|-----------|-----------|
| **Button** | 2.2 AA | Contrast ≥4.5:1 · Focus visible · ARIA label if icon-only · Min 44px tap target · Disabled state visually distinct |
| **Table** | 2.2 AA | `<th scope="col">` + `<caption>` · Keyboard navigation (arrow keys) · Sortable headers announced · Row hover not only visual |
| **Form** | 2.2 AA | Labels associated (`<label for>`) · Error inline + aria-describedby · Validation real-time post-blur · Submit button clear |
| **Modal** | 2.2 AA | Focus trap · Esc key closes · aria-modal=true · Backdrop click toggleable |
| **Badge** | 2.2 AA | If convey info, label with aria-label · Color not only differentiator (use icon + text) |
| **Trace waterfall** | 2.1 AA | Keyboard nav (Tab through spans) · Screen reader summary ("47 spans, 1.2s, $0.004") · Color contrast on span labels |

**Global:** Test NVDA (Windows) + VoiceOver (Mac) every release. Form autocomplete enabled for address, email, password fields.

### 5.15 Screen ownership matrix (MVP, week 6)

| Screen / feature | Primary eng (role) | Figma owner | Status |
|-----|-----|---|---|
| Home dashboard | Eng #5 (Studio) | Designer | ✓ Wireframes done |
| Agents list | Eng #5 | Designer | ✓ |
| Agents detail > Overview | Eng #5 | Designer | ✓ |
| Agents detail > Conversations + Trace | Eng #5 | Designer | ✓ |
| Agents detail > Versions | Eng #5 | Designer | In design |
| Agents detail > Evals | Eng #5 | Designer | In design |
| Agents detail > Cost | Eng #5 | Designer | Deferred to month 7 |
| Agents detail > Settings | Eng #5 | Designer | Deferred to month 7 |
| Knowledge Bases detail | Eng #5 | Designer | Deferred to month 7 |
| Operator Inbox | Eng #5 | Designer | Spec'd; build in week 6 |
| Studio Settings > Members & billing | Eng #5 | Designer | Deferred to month 7 |
| Studio Settings > Audit log | Eng #5 | Designer | Deferred to month 8 |

**Figma design system:** https://www.figma.com/file/{to_be_created} (shared with eng + design partners at week 3)

### 5.16 Role-specific entry points

| Role | First screen (post-login) | What they see / do |
|------|-----|---|
| **Builder** | Agents list | Deploys, traces, eval status. Quick action to "Create agent" if none. |
| **Operator** | Operator Inbox | Escalated conversations, SLA timers. Quick "take over" action. |
| **Admin** | Home dashboard | Cost trends, team member list, billing status. |
| **Viewer** (readonly) | Home dashboard | Read-only view of trends; no deploy / take-over buttons. |
| **First-time user** | Onboarding flow → agents list | See "no agents yet" CTA; guided 60-second agent creation. |

### 5.17 Onboarding flow (first-run post-signup)

**Post-OIDC login, before first workspace action:**

1. **Welcome screen** (5s read): "Loop is an agent runtime debugger. You write Python; we show the traces & costs. Let's create your first agent."
2. **Agent scaffold** (3 CTAs):
   - [Template] "Use the support-agent template" → downloads, `loop init --template support`
   - [Blank] "Start from scratch" → `loop init --workspace <id>`
   - [Docs] "Read the quickstart" → https://loop.local/docs/quickstart
3. **Workspace tour** (optional): Click [?] for a guided tour of the Home → Agents → Conversations → Trace flow.

**Metrics:** Track onboarding completion rate (time to first deploy). Target: 60% within 48 hours of signup.

### 5.18 Pricing surface (budget UI)

**Where budgets & caps appear in-product:**

| Screen | Display | Actions |
|--------|---------|---------|
| **Home dashboard** | "MTD spend: $142.50 / $500 soft · Hard cap: $600" as stat tile | Click to edit budgets |
| **Agent detail > Cost tab** | Budget bars: soft (yellow), hard (red). Linear indicator of daily burn rate. | Inline edit: "edit soft cap", "edit hard cap" |
| **Operator Inbox** | Badge on escalation reason: "budget_hit" | Quick action: "Increase cap" (modal) |
| **Gateway pre-flight** | (internal) Pre-check before accepting request: if hard cap hit, return 429 + "budget_exhausted" error | (no UI; caught by agent code) |

**Budget scope selector:** Workspace · Agent · Conversation · Day. Each has soft (email alert) and hard (reject requests) thresholds.

### 5.19 Brand customization plans

**MVP (month 6):** Fixed Loop branding.  
**Month 7:** Workspace-level logo + primary color customization.

| Customization | Example | Scope | Implementation |
|---|---|---|---|
| **Workspace logo** | Upload PNG/SVG, max 200x100px | Top-left sidebar | S3 upload + image cache, fallback to Loop logo |
| **Primary color** | Swap teal (#14B8A6) for brand color | Links, active buttons, accents | CSS variable override per workspace |
| **Favicon** | Brand ico/png | Browser tab | Workspace-specific favicon served via `/workspace/{id}/favicon.ico` |
| **Email template** | Custom signature, brand color in email borders | Operator inbox emails | Liquid template per workspace |

**Future (month 10):** Custom domain, SSO branding, whitelabel Studio.

### 5.20 Keyboard shortcut catalog completeness check

| Shortcut | Scope | Action | Implemented? |
|----------|-------|--------|--------------|
| `?` | Global | Show shortcuts modal | ✓ |
| `cmd+k` / `ctrl+k` | Global | Command palette (jump to agent / conversation / eval) | ✓ |
| `g h` | Global | Go to Home | ✓ |
| `g a` | Global | Go to Agents | ✓ |
| `g c` | Global | Go to Conversations (active agent) | ✓ |
| `g e` | Global | Go to Evals | ✓ |
| `g i` | Global | Go to Inbox | ✓ |
| `g u` | Global | Go to Usage / Cost | ✓ |
| `j` | Conv/Trace | Next conversation | ✓ |
| `k` | Conv/Trace | Prev conversation | ✓ |
| `r` | Trace | Replay turn | ✓ |
| `t` | Conv | Open trace (drawer) | ✓ |
| `e` | Conv | Add to eval | ✓ |
| `c` | Conv | Comment | ✓ |
| `o` | Conv | Take over (HITL) | ✓ |
| `Esc` | Drawer/Modal | Close | ✓ |
| `cmd+s` / `ctrl+s` | Modal (e.g., cost edit) | Save changes | ✓ |
| `cmd+enter` / `ctrl+enter` | Operator composer | Send message | ✓ |

**Discoverability:** Inline button tooltips include shortcuts (e.g., "Replay (r)" on the button label).

### 5.21 Print / export view conventions

| Format | Use case | What's included | Notes |
|--------|----------|---|---|
| **PDF (conversation + trace)** | Handoff to stakeholder / audit | Conversation thread · Trace waterfall · Cost breakdown · Eval score delta | A4 portrait; 2-col layout for waterfall; logos stripped |
| **JSON (full trace)** | Data analysis / external tools | Complete OTLP-style trace + conversation + memory snapshot | Gzip optional; 5 MB limit per trace |
| **CSV (cost rollup)** | Finance team, expense reports | Date · Agent · Channel · Turns · Tokens · USD | One row per agent-per-day |
| **HTML (conversation replay)** | Shareable link, no auth | Threaded conversation (read-only) · Public link 7-day expiry · No trace data | Logo + workspace name in header |

**Print CSS:** Media queries hide the sidebar, show full-width content, monospace text in fixed-width code blocks.

### 5.22 Additional wireframes (critical screens)

#### 7.4 Agent detail > Evals tab

```
┌─Sidebar─┐ ┌──────────────────────────────────────────────────────┐
│ Agents  │ │ agent: support-en                              [⚙ settings]
│  ├─ ... │ │ Evals · Versions · Cost · Settings
│  └─ ✓ se│ ├─────────────────────────────────────────────────────────┤
│         │ │ Suites (3 attached)  ├──────────┤  [+ Add suite]
│         │ │                      │ Filter:  │
│         │ │                      │ [Name ↓] │
│         │ │                      ├──────────┤
│         │ │ support-v2           [show]
│         │ │  Last run: 2026-04-29 14:22  PASSED ✓
│         │ │  Cases: 12  Avg score: 0.87  ⚡ trending +3% vs baseline
│         │ │  [View results] [Re-run] [Add case from production]
│         │ │
│         │ │ support-v1 (deprecated)
│         │ │  Last run: 2026-04-27 09:15  PASSED ✓
│         │ │
│         │ │ evals/onboarding  (custom, 5 cases)
│         │ │  Last run: 2026-04-22 16:45  FAILED ✗ (2 regressions)
│         │ │  [Troubleshoot]
│         │ │
│         │ │ Recent runs
│         │ │ 2026-04-29 14:22  support-v2  12/12 PASSED
│         │ │ 2026-04-29 14:10  evals/onbo  3/5   FAILED (regression: case 4)
│         │ │ 2026-04-27 09:15  support-v1  12/12 PASSED
└─────────┘ └──────────────────────────────────────────────────────┘
```

#### 7.5 Agent detail > Cost tab

```
┌─Sidebar─┐ ┌───────────────────────────────────────────────────────────────┐
│ Agents  │ │ agent: support-en                                    [⚙ settings]
│  ├─ ... │ │ Conversations · Versions · Evals · Cost · Settings
│  └─ ✓ se│ ├───────────────────────────────────────────────────────────────┤
│         │ │ Today:  $12.34    MTD: $287.50    Projected EOM: $1,240
│         │ │                   Soft cap: $500  |███████░░░░░| Hard cap: $600
│         │ │
│         │ │ [30-day spend by model]  [Drill down by channel / hour]
│         │ │ ███████░░░░░░░░░░░░░░░░ Apr 1-30, 2026
│         │ │  █ gpt-4o-mini (68%)      $195
│         │ │  █ gpt-4o (22%)           $63
│         │ │  █ claude-3-opus (10%)    $29
│         │ │
│         │ │ [Edit soft cap: $500] [Edit hard cap: $600] [Set degrade rule]
│         │ │
│         │ │ Per-channel breakdown (last 7 days)
│         │ │ web       $24.50  (1,240 turns)  ■■■■■■
│         │ │ whatsapp  $18.20  (920 turns)    ■■■■
│         │ │ slack     $5.30   (180 turns)    ■
└─────────┘ └───────────────────────────────────────────────────────────────┘
```

#### 7.6 Home dashboard (empty state + populated)

```
EMPTY STATE (no agents):
┌───────────────────────────────────────────────────────────┐
│ 🎉 Welcome to Loop, Alice                                 │
│ You write Python agents. We show the traces & costs.       │
│                                                            │
│                        [Create your first agent]           │
│                                                            │
│ Quick start: loop init --workspace {your-id}              │
│ Docs: https://loop.local/docs/quickstart                  │
│                                                            │
│ Questions? Open the [?] menu for a guided tour.           │
└───────────────────────────────────────────────────────────┘

POPULATED STATE (with agents):
┌─Sidebar─┐ ┌───────────────────────────────────────────────────────┐
│ Loop    │ │ Workspace: acme-support    [🔧 settings]
│ 🏠 Home │ │ ────────────────────────────────────────────────────
│ Agents  │ │ Active conv     Spend       Failed turns   Escalations
│ KB      │ │ 23              $12.34/day  2              3
│ MCP     │ │ (24h)           (MTD)       (24h)          (open)
│ Evals   │ │
│ Inbox   │ │ ─── 14-day spend & turn volume ───────────────────────
│ Usage   │ │
│ ⚙ Settn │ │  ┌──────────────────────────────────────────────────┐
│         │ │  │ $800 ┤                                            │
│         │ │  │      │   Turn volume (right axis)                 │
│         │ │  │ $600 ├─╱╲──╱─────────╲──╱─────────────────────   │
│         │ │  │      │╱   ╲╱         ╲╱                          │
│         │ │  │ $400 ├────────────────────────────────────────   │
│         │ │  │      │   Spend (teal) by LLM provider             │
│         │ │  │ $200 ├──╭╭─────────────────────────────────────  │
│         │ │  │    0 └──────────────────────────────────────────  │
│         │ │  │        OpenAI  Anthropic  BedRock  (click to toggle)
│         │ │  └──────────────────────────────────────────────────┘
│         │ │
│         │ │ Recent activity
│         │ │ 2026-04-29 14:32  Deploy  v18 → production (alice)
│         │ │ 2026-04-29 14:10  Eval    support-v2 PASSED ✓
│         │ │ 2026-04-29 13:05  Eval    evals/onboarding FAILED ✗
│         │ │ 2026-04-29 12:00  Escalation  user_91 (confidence flag)
└─────────┘ └───────────────────────────────────────────────────────┘
```

---

## 6. Interaction patterns

### 6.1 Keyboard shortcuts

Global:
- `?` — show shortcuts
- `cmd-k` — command palette (jump to anything)
- `g a` — go to agents
- `g c` — go to conversations (active agent)
- `g e` — go to evals
- `g i` — go to inbox

Conversation/trace:
- `j / k` — next/prev conversation
- `r` — replay
- `t` — open trace
- `e` — add to eval
- `c` — comment
- `o` — take over (HITL)

### 6.2 Live data

Studio uses WebSockets for live updates on these screens:
- Operator inbox (new escalations).
- Active conversation detail (turn-by-turn streaming).
- Live trace tail (`loop tail` CLI mirror).
- Cost dashboard (every 5s).

Other screens use 30s polling.

### 6.3 Empty / loading / error

- Empty: illustrated, with a copy-pastable CLI command to create the missing thing.
- Loading: skeleton screens, never spinners on full pages.
- Error: inline, with retry, and a `cmd-shift-c` shortcut to copy a debug bundle (request ID, trace ID, console logs).

### 6.4 Forms

- Validation inline, real-time, after first blur.
- Submit buttons disabled with explainer tooltip when invalid.
- Destructive actions (delete agent, rollback prod) require typing the resource name to confirm.

---

## 7. Wireframe references

ASCII-only wireframes for the most critical screens. (Designer will produce Figma; these are the committed structure.)

### 7.1 Conversation detail with trace drawer

```
┌─Sidebar─┐ ┌── Conversations ──┐ ┌────────── Conversation #c8f… ────────────┐
│ Home    │ │ user_42  💬 web   │ │ ← back   Take over   Replay   Add eval   │
│ Agents  │ │ 12s ago · $0.012  │ ├──────────────────────────────────────────┤
│ KB      │ │ Status: active    │ │  user_42 (web)   2026-04-29 14:00:12     │
│ MCP     │ ├───────────────────┤ │  > "where is my order"                   │
│ Evals   │ │ user_91  📞 voice │ │                                           │
│ Inbox   │ │ 2m ago · $0.041   │ │  agent (gpt-4o-mini)  ↳ trace            │
│ Usage   │ │ Status: ESCALATED │ │  ⚙ tool: lookup_order(id=4172)           │
│ ...     │ │                   │ │     args, result, 142ms, $0.0008         │
│         │ │                   │ │                                           │
│         │ │ [...]             │ │  > "Your order is on the way…" (320 tk)  │
│         │ │                   │ │     latency 412ms · cost $0.0011          │
│         │ │                   │ │                                           │
│         │ │                   │ │  user_42                                  │
│         │ │                   │ │  > "thanks"                               │
│         │ │                   │ │                                           │
│         │ │                   │ │  agent ✓ resolved                         │
│         │ │                   │ │                                           │
│         │ │                   │ ├──────────────────────────────────────────┤
│         │ │                   │ │  Operator compose ▾  draft-as-agent      │
│         │ │                   │ │  [ ____________________________________ ] │
│         │ │                   │ │  Send  •  cmd+enter                       │
└─────────┘ └───────────────────┘ └──────────────────────────────────────────┘
```

### 7.2 Trace waterfall

```
Trace: turn #t-9b…  total 1.42s · $0.0019                              ✕
─────────────────────────────────────────────────────────────────────────
0ms ─────── 200 ─────── 400 ─────── 600 ─────── 800 ─────── 1000 ─── 1200 ─── 1400
│      memory_load (24ms)                                                          │
│       │ retrieval (180ms) ███████████                                            │
│                          │ llm.gpt-4o-mini (412ms) ████████████████              │
│                                              │ tool.lookup_order (142ms) █████   │
│                                                            │ llm (320ms) ██████  │
│                                                                          memory_persist (12ms)
─────────────────────────────────────────────────────────────────────────
[ Inputs/Outputs | Attrs | Cost | Logs ]
  Selected span: llm.gpt-4o-mini (412ms · $0.0011)
  Prompt: 1,420 tokens  •  Completion: 87 tokens
  ┌─Prompt─────────────────────────────────────────────────────────────┐
  │ system: You are a support agent…                                   │
  │ tools: [lookup_order, escalate_to_human, …]                        │
  │ history: <user> where is my order                                  │
  └────────────────────────────────────────────────────────────────────┘
─────────────────────────────────────────────────────────────────────────
Replay  Model: [gpt-4o-mini ▼]   Temp: [0.2]   Tools: [▣ all]   Memory: [▣ live]
        [ Run replay → Diff ]
```

### 7.3 Operator inbox

```
┌─Queues─┐ ┌──────────── Inbox ────────────────────────┐
│ All 12 │ │ User       Agent       Why         Wait    │
│ Esc 4  │ │ user_91   support-en   confidence  2m   ▶  │
│ Conf 5 │ │ user_03   billing-en   tool fail   45s     │
│ Tool 2 │ │ user_77   billing-en   manual rev  3m      │
│ Manual │ │ user_44   support-en   keyword     7m      │
└────────┘ └────────────────────────────────────────────┘
```

---

## 8. Accessibility

- WCAG 2.2 AA target.
- Color contrast ≥ 4.5:1 for text on all surfaces. Audit on every release.
- Keyboard navigation everywhere; visible focus rings.
- ARIA labels on all icon-only buttons.
- Screen-reader-friendly tables with proper `<th scope>` and captions.
- Reduced-motion respect via `prefers-reduced-motion`.

---

## 9. Open UX questions (track in Linear)

1. Trace waterfall over deeply nested spans (e.g. multi-agent with 100+ spans) — collapse strategy.
2. Cost dashboard breakdown: by hour, by user, by intent? Need user research.
3. Eval suite authoring UI in Studio vs. code-only. (Likely code-only at MVP, Studio surface at month 9.)
4. Mobile vs desktop. Studio is desktop-first; minimal mobile for inbox-on-call.
5. Multi-workspace switcher placement: top-left vs top-right vs cmd-k.

---

## 10. Roadmap

| Milestone | Studio scope |
|-----------|--------------|
| MVP (M6) | Home · Agents list+detail · Conversations · Trace view · Cost · Settings basics |
| M7 | Operator Inbox · KB detail · MCP installer |
| M8 | Replay & time-travel · Eval dashboards |
| M9 | Eval suite authoring · Multi-agent visualization |
| M10 | Audit log · Member roles UI · SSO config UI |
| M12 | Enterprise: data residency, BYO key UI, advanced budgets |
