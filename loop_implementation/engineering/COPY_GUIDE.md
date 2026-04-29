# Loop — Copy & Voice Guide

**Status:** v0.1  •  **Owner:** Designer + Eng #5 (Studio)  •  **Companion:** `ux/UX_DESIGN.md` §5.5–5.7.

How Loop talks. Applies to product UI strings, error messages, docs, marketing, status page, and customer-support replies.

---

## 1. Voice in one paragraph

We sound like a senior engineer who's seen production go sideways and has stopped saying "no worries!" Concrete, minimal, never cute. We respect the reader's time and intelligence — explain the *why* in one sentence and the *fix* in one bullet. We don't apologize for things that aren't our fault, and we own things that are.

---

## 2. Six rules

1. **Lead with the verb.** "Open the trace." not "You can open the trace by clicking…"
2. **Concrete > abstract.** "200 ms p99" beats "fast." Numbers, units, exact thresholds.
3. **Say what failed and what to do.** Never an error without a next step.
4. **Use sentence case.** Buttons, labels, headlines. Title Case is for proper nouns.
5. **Don't anthropomorphize the platform.** "Loop did X" is OK; "Loop wants" is not. The agent is a *thing*, not a person.
6. **No marketing voice in the product.** Save adjectives for blog posts.

---

## 3. Words we use vs. don't

| Use | Avoid |
|-----|-------|
| agent | bot (when referring to a Loop agent — "bot" is a Botpress thing) |
| run / turn | invocation, execution |
| trace | log (logs are something else) |
| operator (HITL) | agent (overloaded) |
| budget cap | spend limit (less precise) |
| eval, scorer | benchmark, test (in this context) |
| workspace | tenant, account |
| deploy | publish, push (in this context) |
| MCP server / tool | function, plugin, integration (when MCP-specific) |
| degrade | downgrade |

Don't say:
- "Awesome!", "Whoops!", "Uh-oh!", "Oops!"
- "Easy!" or "It's that simple!"
- "Magic." Loop is the opposite of magic; it's transparent.
- "Synergy", "leverage", "frictionless" — anywhere ever.

---

## 4. Patterns

### 4.1 Buttons

- Verb + noun. "Deploy version", "Take over", "Run eval", "Add scorer".
- One word OK if obvious from context: "Save", "Cancel", "Run".
- Destructive: red. Phrase as the action ("Delete agent"), not the consequence ("Are you sure?").
- Confirmation modal for destructive: ask the user to type the resource name.

### 4.2 Status messages

- Past tense for completed: "Deployed v17. Live in 2 of 3 regions."
- Present continuous for in-flight: "Running eval suite (47 / 100 cases)…"
- Use durations, not percentages, when latency matters: "Estimated 30s remaining" not "60% complete."

### 4.3 Errors

Always: **what failed → why → what to do next**.

✅ **Good:**
> Hard cap reached at $50.00 today. New conversations are paused. Raise the cap in Settings → Budgets, or wait until 00:00 UTC.

❌ **Bad:**
> Error 429: Too Many Requests.

✅ **Good:**
> Eval regression blocked the deploy. The `refund_basic` case dropped from 0.92 → 0.71 (threshold 0.85). [View diff]

❌ **Bad:**
> Deployment failed. Please check your code.

### 4.4 Empty states

Lead with what the user can *do*, not what's missing.

✅ **Good:**
> No agents yet. Run `loop init my-agent` to scaffold one, then `loop deploy`. [Quickstart]

❌ **Bad:**
> Sorry, you don't have any agents.

### 4.5 Loading

- < 1 s — no message.
- 1–3 s — skeleton screen, no spinner.
- > 3 s — message: "Building image…" or "Querying KB (300 chunks)…"
- > 10 s — show progress + estimated remaining + a way to cancel.

### 4.6 Confirmations

Confirm only destructive or irreversible actions. Make the user type the resource slug for high-stakes:

> Type **support-en** to confirm deletion. This cannot be undone.

### 4.7 Marketing & docs

Allowed adjectives in marketing: precise, technical, factual.
Forbidden: revolutionary, game-changing, world-class, magical, seamless, effortless, blazingly fast.

When in doubt, replace the adjective with a number.

---

## 5. Notifications & toasts

Tone per variant:

| Variant | Tone | Example |
|---------|------|---------|
| Success | Plain. No exclamations. | "Deployed v17 to prod." |
| Info | Neutral, single sentence. | "Eval cassette regenerated." |
| Warning | Direct, with next-step option. | "KB ingestion is 2 docs behind. Retry?" |
| Error | What/why/next. | "Save failed: missing required field 'instructions'." |
| Critical | Same as error + page header banner. | "Region us-east is degraded. New conversations paused." |

Never animate toast in/out for > 200 ms. Never auto-dismiss errors.

---

## 6. Dates, numbers, units

- Dates: ISO 8601 in product UI for absolute (`2026-04-29 14:00 UTC`); relative for activity feeds (`2 min ago`).
- Numbers: thousands separator with locale; never use `K`/`M` in dashboards (use exact + tooltip rounded).
- Currency: `$0.0042` precision in product; `$4.20` in invoices. Always with currency code on first appearance: `USD $4.20`.
- Latency: `ms` for < 1000, `s` for ≥ 1000. Two significant figures in dashboards, full precision in trace detail.
- Token counts: integer, comma-separated.

---

## 7. Localization

- All product strings live in `apps/studio/locales/<lang>.json`. No string literals in components.
- Initial translations: en, es, fr, de, ja, zh-Hans (post-MVP).
- Dates and numbers locale-formatted via `Intl.DateTimeFormat` and `Intl.NumberFormat`.
- RTL: structure must work in RTL (we don't use English-only icons).

---

## 8. Accessibility (text)

- Never use color alone to convey meaning. Pair with text or icon.
- Plain language; don't gate comprehension on jargon. (Dev jargon is OK in dev tooling, not in operator-facing screens.)
- ALT text for every image, even decorative (use empty `alt=""` for decorative).
- Headings in order (no skipping h2 → h4).

---

## 9. Examples

### Trace empty state (Studio)

> No traces yet. Open a conversation in the list and click any turn to see its waterfall.

### Eval-gate fail (deploy controller)

> Promotion blocked. Eval suite `support-en` regressed: average score 0.81 → 0.74 (threshold 0.85, regression 8.6%). [Open diff] [Override]

### Voice channel down (status banner)

> Voice channel for agent `support-en` is degraded. Calls are being routed to web-chat fallback. Estimated recovery 5–15 min.

### CLI deploy success

```
Deployed support-en v18 to prod (canary 10%).
Promote: loop deploy promote --agent=support-en --version=18
Rollback: loop deploy rollback --agent=support-en
```

---

## 10. References

- `ux/UX_DESIGN.md` §5.5–5.7 — design tokens, error catalog, toast patterns.
- `engineering/ERROR_CODES.md` — every error has a canonical code + recommended copy.
