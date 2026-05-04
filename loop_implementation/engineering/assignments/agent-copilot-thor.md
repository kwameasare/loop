# Agent: copilot-thor — studio cross-cutting + a11y + bundle

**Theme**: studio quality outside the in-flight P0.3 fixture-replacement
task. Owns auth-flow polish, cross-section UX states, security headers,
modal a11y, bundle hygiene, web-channel widget demo.

**Branch convention**: `agent/copilot-thor/<slug>`.

**DO NOT** rewrite `/inbox`, `/billing`, `/costs`, `/traces`, `/voice`,
`/enterprise`, `/agents/[id]/tools`, `/agents/[id]/inspector` — those
are owned by the in-flight P0.3 task. Coordinate via the chat thread.

---

## Item 1 — 401 / token-expiry interceptor (P0.3 cross-cut)

**File**: `apps/studio/src/lib/cp-api.ts`.

**Audit finding**:
> No 401 / token-expired handling. No interceptor. Mid-session expiry
> dumps users into a generic "Something broke" toast instead of re-auth.

**Acceptance**:
1. Wrap every cp-api call (`createCpApi(...)` factory) with a
   middleware that on 401 calls `/v1/auth/refresh` (shipped in #184)
   with the stored refresh token and retries the original request
   exactly once.
2. If refresh also 401s → clear `sessionStorage` keys, redirect to
   `/login` with `returnTo=<current>`.
3. Tests via vitest + msw: stub cp returning 401, then 200 on retry,
   assert two outbound calls and the second succeeds.

**Effort**: ~0.5 day, 1 PR.

---

## Item 2 — `AuthProvider` production hard-fail

**File**: `apps/studio/src/components/auth/auth-provider.tsx:48-50`.

**Audit finding**:
> When `LOOP_AUTH0_DOMAIN`/`LOOP_AUTH0_CLIENT_ID` are unset, the
> provider silently degrades to no-auth. In a misconfigured prod
> deploy the studio will boot wide-open instead of failing loudly.

**Acceptance**:
1. If `process.env.NODE_ENV === "production"` AND Auth0 env unset,
   `throw new Error("Auth0 config required in production")`. Vitest
   test for this.
2. Dev mode keeps the silent-degrade path (lets the studio render
   without Auth0 in local).

**Effort**: ~0.25 day, 1 PR.

---

## Item 3 — Per-section `loading.tsx` + `error.tsx`

**Audit finding**:
> No `loading.tsx` / `error.tsx` for inbox, billing, costs, evals,
> traces, voice, enterprise, workspaces. Only `/agents` has them.

**Acceptance**:
1. For each of the 7 sections, create
   `apps/studio/src/app/<section>/loading.tsx` and `error.tsx` that
   match the look-and-feel of `agents/loading.tsx` /
   `agents/error.tsx`.
2. Each `error.tsx` exposes a "Retry" button calling
   `reset()` and a "Report" link with the request_id.
3. Snapshot tests via vitest + react-testing-library.

**Effort**: ~0.5 day, 1 PR (one per section ⇒ batch as one PR).

---

## Item 4 — Modal a11y (focus-trap, escape, autofocus)

**Files**:
- `apps/studio/src/components/agents/new-agent-modal.tsx:101-194`
- `apps/studio/src/components/agents/agent-overview.tsx`'s edit modal

**Audit finding**:
> Modal has `role="dialog"` but no escape-to-close, no focus-trap, no
> autofocus, no first-element focus on open. Keyboard users can't
> dismiss.

**Acceptance**:
1. Wrap each modal in a generic `<Dialog>` primitive built on Radix
   UI's `Dialog.Root` (already a dep via shadcn's pattern). Replace
   custom open/close logic.
2. First-element autofocus on open; escape closes; focus returns to
   the trigger on close.
3. Vitest + jest-dom tests asserting keyboard navigation.

**Effort**: ~0.5 day, 1 PR.

---

## Item 5 — Member-management UI (P0.3 cross-cut, depends on #185 routes)

**Audit finding**:
> No member-management UI at all. cp-api has the routes (now wired
> in #185), but nothing in `apps/studio/src/components/workspaces/`
> lists/invites members.

**Acceptance**:
1. New page `apps/studio/src/app/workspaces/[id]/members/page.tsx`
   with: list (calls `/v1/workspaces/{id}/members`), add-member modal
   (calls `POST /members`), per-row remove + role-change controls.
2. Add to the studio top-nav (added in #166) under the workspace
   switcher.
3. Vitest tests for the page + each user-action component.

**Effort**: ~1 day, 1 PR.

---

## Item 6 — Eval-suite create form

**File**: `apps/studio/src/app/evals/page.tsx`.

**Audit finding**:
> No "New suite" button, no form. You can read but never create.

**Acceptance**:
1. "New suite" CTA on `/evals`, opens a modal posting to
   `/v1/workspaces/{id}/eval-suites` (shipped in #194).
2. Form fields: name, dataset_ref, metrics (multi-select).
3. After successful create, navigate to the suite detail page +
   show a "Run now" button that posts to `/v1/eval-suites/{id}/runs`.
4. Tests for the form + the run-trigger flow.

**Effort**: ~0.5 day, 1 PR.

---

## Item 7 — Studio security headers (CSP, HSTS, X-Frame, etc.)

**File**: `apps/studio/next.config.js`.

**Audit finding**:
> No `headers()` for CSP / X-Frame-Options / HSTS / Referrer-Policy.
> Studio is an admin app; default Next.js shipping with no security
> headers is a P1.

**Acceptance**:
1. Add a `headers()` config returning:
   - `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Content-Security-Policy: default-src 'self'; …` — full CSP
     string covering Auth0, the cp-api origin, and the dp SSE origin.
2. Add `noindex` `<meta>` to root layout (studio is internal).
3. Test: e2e Playwright spec asserts every response has these
   headers.

**Effort**: ~0.5 day, 1 PR.

---

## Item 8 — Studio bundle hygiene

**Files**:
- `apps/studio/package.json` — `i18next` + `react-i18next` (~80 KB
  combined gz)
- `apps/studio/src/lib/i18n.ts`

**Audit finding**:
> `package.json` deps include i18next + react-i18next. `i18n.ts`
> imports five locale JSONs eagerly even though English is the only
> language anyone hits.

**Acceptance**:
1. Lazy-load locale JSONs via dynamic `import()`. Default English
   stays in the main bundle.
2. Add a bundle-size CI gate using `next-bundle-analyzer` + a budget
   file. Fail the build on >5% growth without justification.
3. Drop or move to a separate route segment any non-English locale
   that's never used in production.

**Effort**: ~0.5 day, 1 PR.

---

## Item 9 — Web-channel widget demo page

**Audit finding**:
> No demo / playground for the embeddable widget. The
> `widget.stories.tsx` exists but no Storybook in package.json.

**Acceptance**:
1. New `examples/web_widget_demo/index.html` that imports the built
   widget (from `packages/channels/web-js/dist/`) and points it at
   a configurable cp + dp URL.
2. README in the same folder explaining how to bring up cp + dp +
   the widget locally.
3. CI: a tiny smoke that loads the page in headless Chromium and
   asserts the widget renders. Use Playwright since it's already a
   dep.

**Effort**: ~0.5 day, 1 PR.

---

## Item 10 — `tsconfig.json` strict tightening (P2)

**File**: `apps/studio/tsconfig.json`.

**Audit finding**:
> `strict:true` good, but no `noUncheckedIndexedAccess`, no
> `exactOptionalPropertyTypes`. Studio's array indexing
> (`STEPS[i]` in inspector) is unguarded.

**Acceptance**:
1. Flip both flags to `true`.
2. Fix every type error that surfaces (estimated ~30 small fixes
   across the codebase).
3. Vitest still green.

**Effort**: ~1 day, 1 PR.

---

## Item 11 — Playwright retries + cross-browser

**File**: `apps/studio/playwright.config.ts:13`.

**Audit finding**:
> `retries:0`, single chromium project. No webkit/firefox/mobile.

**Acceptance**:
1. `retries: 2` in CI (`process.env.CI` gate).
2. Add `webkit` + `firefox` + `Mobile Chrome` projects.
3. Smoke spec exists for: login redirect, agents list,
   member-add modal, eval-suite create form.

**Effort**: ~0.5 day, 1 PR.

---

## Item 12 — Workspace-pinning cross-tab sync (P2)

**File**: `apps/studio/src/lib/use-active-workspace.ts:54-63`.

**Audit finding**:
> Workspace pinning lives in localStorage only. Not synced across
> tabs.

**Acceptance**:
1. Use the `storage` event to broadcast workspace changes to other
   tabs. Update the active workspace state on receipt.
2. Vitest covering: tab A switches workspace; tab B's
   `useActiveWorkspace()` returns the new value within one tick.

**Effort**: ~0.25 day, 1 PR.

---

## Acceptance summary for copilot-thor

12 items, ~7-8 PRs, ~5-6 days. After your work:

- [x] 401 mid-session triggers refresh-and-retry, falls back to /login.
- [x] AuthProvider hard-fails on missing prod config.
- [x] Every section has loading + error states.
- [x] All modals are keyboard-accessible.
- [x] Member-admin UI ships and works against #185 routes.
- [x] Eval-suite create form posts to #194 routes.
- [x] CSP + HSTS + X-Frame-Options on every response.
- [x] Bundle is locale-lazy; size budget gate in CI.
- [x] Web-channel widget has a working demo page + smoke.
- [x] tsconfig stricter; cross-browser e2e on retry.
- [x] Workspace-pinning syncs across tabs.
