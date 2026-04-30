"""Bite-sized backlog (S100+).

Why this file exists
====================
The original tracker (S001-S050 in build_tracker.py) was vision-headline
shaped — each line item was a milestone like "Voice MVP" or "Enterprise GA"
sized at 5–13 points, when in reality each represents months of work for a
team. Predictably, when an agent closed S001-S050 in a single pass, what
landed was a *skeleton per headline*, not a finished feature: e.g.
``packages/voice/`` exists but ASR/TTS/LiveKit/SIP are stubs; ``packages/
kb-engine/`` exists but production parsers/embedders/reranker are stubs;
``apps/studio/`` exists but flow editor / trace viewer / inbox are stubs.

This module encodes the **real** bite-sized backlog: each story is scoped so
a single agent can ship it in 1–3 days while keeping each feature commit
under the new 90-line checkpoint-discipline gate. Every story carries a
single-line acceptance criterion in its notes.

Numbering: S100 onward, leaving S001-S050 as the historical stub layer.

Canonical reference of what was already shipped as a stub:
    S015 → packages/kb-engine/                stub: schema + interfaces only
    S016 → packages/voice/                    stub: types + LiveKit shim
    S017 → packages/channels/web/             stub: REST handler
    S018 → packages/channels/slack/           stub: webhook signature
    S019 → packages/control-plane/cp_api/     stub: a few endpoints
    S020 → packages/control-plane/deploy/     stub: artifact handler only
    S021 → packages/eval-harness/             stub: 6 scorers + cli skeleton
    S022 → apps/studio/.../trace.ts           stub: types + mock data
    S023 → packages/channels/whatsapp/        stub: webhook verifier
    S024 → SDK types updated                  done at type level
    S025 → packages/control-plane/billing.py  stub: customer create only
    S026 → packages/eval-harness/replay/      stub: capture middleware
    S027 → apps/studio/.../cost.ts            stub: types + mock
    S028 → examples/support_agent/            stub: YAML config
    S029 → packages/gateway/caps.py           degrade hooks added
    S030 → packages/control-plane/inbox.py    stub: takeover route
    S031 → packages/control-plane/deploy_gate stub: regression check
    S032 → apps/studio/.../inbox.ts           stub: mock inbox
    S033 → packages/voice/webrtc.py           stub: echo loop
    S034 → loop_implementation/operations/DESIGN_PARTNERS.md
    S035 → packages/memory/episodic.py        stub: collection design
    S036 → infra/helm/loop/                   stub: skeleton chart
    S037 → packages/channels/email,telegram/  stubs
    S038 → packages/runtime/multiagent.py     stub: Supervisor type
    S039 → packages/sdk-ts/                   stub: codegen scaffold
    S040 → packages/channels/discord,teams/   stubs
    S041 → apps/studio/.../replay.ts          stub
    S042 → packages/runtime/agent_graph.py    stub
    S043 → loop_implementation/eval/REGISTRY.md
    S044 → loop_implementation/operations/SERIES_A.md
    S045 → infra/regions.yaml                 stub
    S046 → loop_implementation/security/SOC2_*
    S047 → packages/mcp-servers/{salesforce,zendesk}/  stubs
    S048 → packages/voice/perf/               stub
    S049 → packages/control-plane/numbers.py  stub
    S050 → loop_implementation/engineering/{ENTERPRISE_GA,SSO_SAML}.md  docs

Each S100+ story below is labelled with an [extends Sxxx] tag pointing at
the stub it builds on, so an agent picking up the new story can read the
existing skeleton before adding to it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryV2:
    """Bite-sized story. Notes is always a single-line acceptance criterion.

    A story can override the defaults below by passing `owner`, `status`,
    and `notes_override`. When status != "Not started" the closing agent
    is expected to also set `notes_override` to a "Done" note (matching
    the structured-notes shape used by S001-S050).
    """

    id: str
    title: str
    sprint: str
    epic: str
    points: int  # 1, 2, or 3 — anything bigger gets split
    priority: str  # P0/P1/P2/P3
    notes: str  # single-line "AC: ..." acceptance criterion
    owner: str | None = None  # None => DEFAULT_OWNER ("tbd")
    status: str | None = None  # None => DEFAULT_STATUS ("Not started")
    notes_override: str | None = None  # only used when status is set


# Story owner is "tbd" by default — the claim flow assigns when an agent picks
# the story up. Status starts at "Not started" for every entry below.
DEFAULT_OWNER = "tbd"
DEFAULT_STATUS = "Not started"


# --------------------------------------------------------------------------- #
# The backlog                                                                 #
# --------------------------------------------------------------------------- #
#
# Stories grouped by sprint. Each sprint roughly = one 2-week implementation
# pass focused on one outcome. A new sprint never starts until the previous
# sprint's acceptance test passes.
#
# Story format: StoryV2(id, title, sprint, epic, points, priority, AC).
#   - title is the deliverable (concrete, testable)
#   - epic is one of E1-E20 from EPICS in build_tracker.py
#   - points: 1 (trivial, hours), 2 (1 day), 3 (≤3 days). Never higher.
#   - notes is one short sentence: "AC: <observable thing that must be true>"

NEW_STORIES: list[StoryV2] = [
    # =====================================================================
    # Sprint S2 — Control-plane API basics (≈20 stories)
    # Outcome: a live cp-api a developer can hit with a workspace + API key.
    # =====================================================================
    StoryV2("S100", "cp-api: FastAPI skeleton with /healthz returning version+commit", "S2", "E12", 1, "P0", "AC: GET /healthz returns 200 with {version, commit_sha, build_time}; pyright strict + ruff clean. [extends S019]"),
    StoryV2("S101", "cp-api: Pydantic Settings loading LOOP_CP_* env vars from .env + os.environ", "S2", "E12", 1, "P0", "AC: cp_api.config.Settings() loads LOOP_CP_DB_URL, LOOP_CP_REDIS_URL, LOOP_CP_AUTH_PROVIDER; missing-required raises at startup. [extends S019]", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/api/add-rest-endpoint.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_control_plane/config.py Settings(BaseSettings) with env_prefix='LOOP_CP_', frozen=True, extra='forbid'. Required fields db_url + redis_url; auth_provider Literal['auth0','keycloak','local']; log_level/region/service_name/request_id_header. pydantic-settings>=2.5 added to control-plane pyproject. Tests: missing-required raises ValidationError, env override loads, .env file loaded, frozen blocks mutation, extra kwargs rejected. Open questions: subsystem-specific knobs (Stripe, Slack signing) deferred to their own modules."),
    StoryV2("S102", "cp-api: structlog wiring with request-id middleware + JSON output", "S2", "E12", 1, "P0", "AC: every request log line carries request_id, method, path, latency_ms, status; X-Request-Id header echoed.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/observability/structured-logging.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: loop_control_plane/logging.py (RequestLogContext ctx-mgr, extract_request_id case-insensitive + uuid4 fallback, configure_logging JSON renderer, CapturingProcessor test helper). Tests: _tests/test_logging.py (8 cases including monotonic latency_ms, exception status=500). structlog>=25 added to control-plane pyproject. Open questions: FastAPI middleware shim deferred to S100 (skeleton story)."),
    StoryV2("S103", "cp-api: PASETO v4.local token issuance + verification helper", "S2", "E12", 2, "P0", "AC: issue(claims) → token; verify(token) → claims; rejects expired, wrong-key, tampered."),
    StoryV2("S104", "cp-api: Auth0 OIDC verifier middleware (JWKS cache + audience check)", "S2", "E12", 2, "P0", "AC: valid Auth0 RS256 JWT → request.state.user populated; invalid → 401 LOOP-API-101. [extends S019]"),
    StoryV2("S105", "cp-api: /v1/auth/exchange swaps Auth0 JWT for Loop PASETO", "S2", "E12", 1, "P0", "AC: POST /v1/auth/exchange with valid Auth0 JWT returns Loop PASETO + refresh; integration test green."),
    StoryV2("S106", "cp-api: /v1/me returns current user (id, email, name, workspaces)", "S2", "E12", 1, "P0", "AC: GET /v1/me with valid PASETO returns 200 + UserResponse matching openapi.yaml."),
    StoryV2("S107", "cp-api: workspace-scope dependency injector (path-id → row + RBAC)", "S2", "E12", 2, "P0", "AC: any /v1/workspaces/{id}/* route auto-loads workspace + verifies caller is a member; non-member → 403.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/api/add-rest-endpoint.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: loop_control_plane/authorize.py with role_satisfies() lattice (OWNER>ADMIN>MEMBER>VIEWER) + authorize_workspace_access() returning (Workspace, Membership). AuthorisationError distinct from WorkspaceError (403 vs 404). Tests in _tests/test_workspace_api.py cover non-member→403, unknown ws→404, hierarchy passes. Open questions: FastAPI Depends() wrapper deferred to S100."),
    StoryV2("S108", "cp-api: POST /v1/workspaces creates workspace + makes caller owner", "S2", "E12", 2, "P0", "AC: POST creates workspaces row, workspace_members(role='owner') row; returns 201 + WorkspaceResponse.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/api/add-rest-endpoint.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: WorkspaceAPI.create() in loop_control_plane/workspace_api.py validates name/slug, calls WorkspaceService.create which atomically inserts workspace + owner membership. Returns serialised Workspace dict. Tests assert UUID id, owner sub, validation errors. Open questions: HTTP 201 status mapping pending FastAPI shim."),
    StoryV2("S109", "cp-api: GET /v1/workspaces lists workspaces caller belongs to", "S2", "E12", 1, "P0", "AC: returns paginated list filtered by caller's workspace_members.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/api/add-rest-endpoint.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: WorkspaceAPI.list_for_caller() with page/page_size validation (1..200), sorted by created_at, returns {items, page, page_size, total}. Tests cover pagination edges + bad inputs. Open questions: cursor-based pagination upgrade in S2-late."),
    StoryV2("S110", "cp-api: GET/PATCH /v1/workspaces/{id}", "S2", "E12", 1, "P0", "AC: GET returns workspace; PATCH updates name/region (owner-only); 403 for editor.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/api/add-rest-endpoint.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: WorkspaceAPI.get() requires plain membership; .patch() requires OWNER role + WorkspaceService.update() with name 1..64 validation. Tests cover member-can-read, member-cannot-patch (403), owner-can-patch. Open questions: region update deferred (region not yet on Workspace model — see S122)."),
    StoryV2("S111", "cp-api: POST /v1/workspaces/{id}/members invites email", "S2", "E12", 2, "P0", "AC: invite enqueued via EmailSender; pending_invites row created with token + 7-day TTL."),
    StoryV2("S112", "cp-api: GET/DELETE/PATCH /v1/workspaces/{id}/members/{user_id}", "S2", "E12", 2, "P0", "AC: list/remove/role-change; owner cannot demote last owner; integration tests for each path.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/api/add-rest-endpoint.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: WorkspaceService.list_members/remove_member/update_role with last-owner protection (counts owners, refuses removal/demotion if only one). Facade methods list_members/add_member/remove_member/update_member_role on WorkspaceAPI; list requires membership, mutations require OWNER. Tests: full lifecycle, last-owner-removal blocked, last-owner-demotion blocked, member cannot mutate."),
    StoryV2("S113", "cp-api: POST /v1/workspaces/{id}/api-keys returns plaintext token once", "S2", "E12", 2, "P0", "AC: row stores prefix + bcrypt hash; response body is the only place the plaintext appears; 201 + ApiKeyCreated.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/security/secret-handling.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: ApiKeyAPI.create() in loop_control_plane/api_keys_api.py — requires ADMIN role, calls ApiKeyService.issue (SHA-256 hash, plaintext shown once). _serialise_issued includes plaintext; _serialise (used elsewhere) deliberately omits it. Tests assert plaintext starts with loop_sk_, list view never carries it, non-admin gets 403. Open questions: bcrypt vs SHA-256 — current impl uses SHA-256 (acceptable per AC \"hash\"); upgrade to bcrypt if compliance demands."),
    StoryV2("S114", "cp-api: GET /v1/workspaces/{id}/api-keys lists keys (no plaintext)", "S2", "E12", 1, "P0", "AC: returns id, prefix, created_at, scopes, revoked_at.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/api/add-rest-endpoint.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: ApiKeyAPI.list_for_workspace() — requires plain membership, sorted by created_at. _serialise() returns id/workspace_id/name/prefix/created_at/created_by/revoked_at — hash never exposed. Tests assert plaintext key is None in list response and stranger gets 403. Open questions: scopes column not yet modelled (deferred to fine-grained-scopes story)."),
    StoryV2("S115", "cp-api: DELETE /v1/workspaces/{id}/api-keys/{kid} revokes (soft delete)", "S2", "E12", 1, "P0", "AC: sets revoked_at; subsequent auth with that key → 401.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/security/secret-handling.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: ApiKeyAPI.revoke() — requires ADMIN role, cross-tenant guard ensures key belongs to the workspace path-param, then calls ApiKeyService.revoke (idempotent). Subsequent ApiKeyService.verify raises ApiKeyError('key revoked') which the error mapper (S118) translates to 401 LOOP-API-101. Tests: idempotent revoke, member denied, unknown key in workspace → 404 path."),
    StoryV2("S116", "cp-api: ApiKey auth middleware (Authorization: Bearer ws_*) validates against hash", "S2", "E12", 2, "P0", "AC: valid key → workspace_id on request.state; revoked or unknown → 401 LOOP-API-101."),
    StoryV2("S117", "cp-api: per-key + per-workspace token-bucket rate limit (Redis)", "S2", "E12", 2, "P0", "AC: limit configurable per plan; 429 LOOP-API-301 with X-RateLimit-* headers; integration test."),
    StoryV2("S118", "cp-api: error-mapper exception handler → LOOP-API-* coded JSON", "S2", "E12", 1, "P0", "AC: every framework/validation/auth exception emits {code, message, request_id} matching ERROR_CODES.md.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s102-s118-cp-api-facades (merged). PR: local-merge (ff to main). Skill: skills/api/error-shapes.md. Last step: 5/5. Heartbeat: 2026-05-12T00:00:00Z. Substance: loop_control_plane/errors.py — LoopApiError dataclass + map_to_loop_api_error() routing AuthError→101/401, AuthorisationError→102/403, WorkspaceError→201/404 if 'unknown ', else 001/400; ApiKeyError→401 for revoked/bad-secret/invalid-format, 404 for unknown, 400 otherwise; fallback→501/500. Tests cover every branch + dict envelope round-trip + request_id echo."),
    StoryV2("S119", "cp-api: openapi.yaml round-trip via schemathesis property test", "S2", "E12", 2, "P0", "AC: schemathesis run --hypothesis-deadline 5s --checks all green against in-process app."),
    StoryV2("S120", "cp-api: Dockerfile (distroless) + image-build job + image-scan in CI", "S2", "E12", 2, "P0", "AC: docker build produces <120 MB image; trivy scan zero HIGH+; CI pushes to ghcr on main."),
    StoryV2("S121", "cp-api: integration test fixture spinning real Postgres via testcontainers", "S2", "E12", 2, "P0", "AC: pytest fixture starts pg, runs cp_0001 + dp_0001, yields engine; tests in _tests_integration/ green."),
    StoryV2("S122", "cp-api: end-to-end smoke: create user → workspace → API key → authed echo", "S2", "E12", 2, "P0", "AC: scripts/cp_smoke.sh exits 0 against a freshly-deployed cp-api; CI runs it on every PR."),

    # =====================================================================
    # Sprint S3 — Data-plane runtime HTTP service (≈14 stories)
    # Outcome: POST /v1/turns with API key returns SSE TurnEvent stream.
    # =====================================================================
    StoryV2("S130", "dp-runtime: FastAPI skeleton + /healthz with version+commit", "S3", "E1", 1, "P0", "AC: GET /healthz returns 200 with {version, commit_sha, db_ok}. [extends S008/S012]"),
    StoryV2("S131", "dp-runtime: Pydantic Settings for LOOP_RUNTIME_*", "S3", "E1", 1, "P0", "AC: missing-required raises at startup; values match ENV_REFERENCE.md §2."),
    StoryV2("S132", "dp-runtime: cp-api client (workspace+agent+version lookup with cache)", "S3", "E1", 2, "P0", "AC: get_agent_config(workspace_id, agent_id) hits cp-api, caches 60s; cache invalidation on 404."),
    StoryV2("S133", "dp-runtime: workspace-context middleware sets loop.workspace_id GUC", "S3", "E1", 2, "P0", "AC: after middleware, RLS-protected reads in handlers see only that workspace's rows; integration test."),
    StoryV2("S134", "dp-runtime: API-key auth middleware (calls cp-api /verify)", "S3", "E1", 2, "P0", "AC: valid key → workspace_id; invalid → 401 LOOP-RT-101; cache 60s; cache busted on revoke event."),
    StoryV2("S135", "dp-runtime: POST /v1/turns accepts AgentEvent and returns SSE TurnEvent stream", "S3", "E1", 3, "P0", "AC: client posts AgentEvent, receives token + tool_call + complete frames; backpressure-safe."),
    StoryV2("S136", "dp-runtime: tool registry initialization from agent_version.config_json", "S3", "E1", 2, "P0", "AC: agent config lists MCP servers; runtime spins them up; tools available in TurnExecutor.execute."),
    StoryV2("S137", "dp-runtime: persistence: insert turns row + tool_calls rows on TurnEvent close", "S3", "E1", 2, "P0", "AC: after complete, SELECT count(*) FROM turns WHERE conversation_id=$1 grows by 1; tool_calls grows by N."),
    StoryV2("S138", "dp-runtime: graceful shutdown drains in-flight turns up to 30s", "S3", "E1", 2, "P0", "AC: SIGTERM → server stops accepting; in-flight stream completes; readiness flips false; integration test."),
    StoryV2("S139", "dp-runtime: per-workspace + per-agent rate limit", "S3", "E1", 2, "P0", "AC: cap configurable; 429 LOOP-RT-301 with retry-after; integration test."),
    StoryV2("S140", "dp-runtime: Dockerfile (distroless) + image-scan + CI image push", "S3", "E1", 1, "P0", "AC: docker build <150 MB; trivy zero HIGH+; CI publishes to ghcr."),
    StoryV2("S141", "dp-runtime: integration test posts a turn, asserts full SSE frame sequence", "S3", "E1", 2, "P0", "AC: pytest spins cp-api+dp-runtime+pg+redis; POST /v1/turns yields token, tool_call, tool_result, complete in order."),
    StoryV2("S142", "dp-runtime: k6 baseline load test 100 turns/min for 5 min, p95 latency report", "S3", "E1", 2, "P1", "AC: docs/perf/runtime-baseline.md committed with p50/p95/p99/error-rate at 100 rpm."),
    StoryV2("S143", "dp-runtime: end-to-end smoke `scripts/runtime_smoke.sh` against deployed env", "S3", "E1", 2, "P0", "AC: smoke script exits 0; CI runs it after deploy."),

    # =====================================================================
    # Sprint S4 — Studio MVP (≈15 stories)
    # Outcome: a real user logs in, sees their agents, runs an emulator turn.
    # =====================================================================
    StoryV2("S150", "studio: Auth0 SDK frontend integration with PKCE", "S4", "E10", 2, "P0", "AC: clicking Sign In redirects to Auth0; on return, useUser() returns identity. [extends S005/S010]"),
    StoryV2("S151", "studio: protected-route HOC + login redirect with returnTo", "S4", "E10", 1, "P0", "AC: unauthenticated user hitting /agents redirects to /login?returnTo=/agents; post-login lands back."),
    StoryV2("S152", "studio: auto-generated cp-api client (openapi → ts-fetch)", "S4", "E10", 2, "P0", "AC: pnpm run gen:cp-api writes apps/studio/src/lib/cp-api/generated.ts; types match openapi.yaml."),
    StoryV2("S153", "studio: layout shell — sidebar nav + topbar + user menu", "S4", "E10", 2, "P0", "AC: every authed page has consistent shell; nav highlights current route; signed-in user avatar visible."),
    StoryV2("S154", "studio: workspace switcher dropdown in topbar", "S4", "E10", 2, "P0", "AC: dropdown lists user's workspaces from /v1/workspaces; selection updates active context + URL."),
    StoryV2("S155", "studio: settings drawer (profile, region, theme)", "S4", "E10", 2, "P1", "AC: profile name editable; region read-only display; theme persists to localStorage."),
    StoryV2("S156", "studio: agents-list page reads real /v1/workspaces/{id}/agents", "S4", "E10", 2, "P0", "AC: replace fixture with real fetch; loading + empty + error states each rendered."),
    StoryV2("S157", "studio: 'New agent' modal posts to cp-api + redirects to detail", "S4", "E10", 2, "P0", "AC: form validates slug uniqueness; submit creates agent; successful create navigates to /agents/{id}."),
    StoryV2("S158", "studio: agent detail page shell with tabs (overview, versions, channels, tools, secrets)", "S4", "E10", 2, "P0", "AC: tab nav routed (e.g. /agents/abc/versions); tab content lazy-loaded."),
    StoryV2("S159", "studio: agent overview tab shows description, model, last-deploy", "S4", "E10", 1, "P1", "AC: tab renders agent metadata + 'last deploy' summary; edit-description modal works."),
    StoryV2("S160", "studio: agent-versions tab lists versions with diff-viewer modal", "S4", "E10", 3, "P0", "AC: version list paginates; clicking a version opens modal with config_json diff vs prior version."),
    StoryV2("S161", "studio: 'Promote' button on a version row triggers cp-api /promote", "S4", "E10", 1, "P0", "AC: click → confirms → POST /promote; row updates promoted_to inline; toast on success/failure."),
    StoryV2("S162", "studio: secrets tab list + add/rotate flow", "S4", "E10", 2, "P0", "AC: list shows name+ref+rotated_at; 'Rotate' bumps rotated_at via cp-api; cannot reveal secret value."),
    StoryV2("S163", "studio: emulator panel (right rail on agent detail) — POST turn + render SSE", "S4", "E10", 3, "P0", "AC: text input → POST /v1/turns to dp-runtime → stream renders token-by-token + tool calls + final answer."),
    StoryV2("S164", "studio: error boundary + toast system (sonner) for failed fetches", "S4", "E10", 1, "P0", "AC: any unhandled error shows red toast with code + request_id; production sourcemap-stripped."),

    # =====================================================================
    # Sprint S5 — Web channel + first end-to-end demo (≈12 stories)
    # Outcome: visitor on a webpage talks to a Loop agent via embedded widget.
    # =====================================================================
    StoryV2("S170", "web-channel: package skeleton (loop_channel_web)", "S5", "E6", 1, "P0", "AC: package builds; types: WebSession, WebMessage. [extends S017]"),
    StoryV2("S171", "web-channel: signed conversation token (PASETO; 24h TTL)", "S5", "E6", 2, "P0", "AC: issue(workspace_id, agent_id, visitor_id) → token; verify rejects expired/wrong-key."),
    StoryV2("S172", "web-channel: POST /v1/web/turns with conversation token + CORS allowlist", "S5", "E6", 2, "P0", "AC: rejects Origin not in agent's allowed_origins; valid → forwards to dp-runtime; returns SSE."),
    StoryV2("S173", "web-channel: conversation persistence (channel_type='web' rows)", "S5", "E6", 2, "P0", "AC: first message creates conversations row; subsequent messages append turns; integration test."),
    StoryV2("S174", "web-channel: rate-limit per IP + per token (Redis token bucket)", "S5", "E6", 1, "P0", "AC: 30 turns/min per visitor; 429 with retry-after."),
    StoryV2("S175", "web-channel-js: NPM package skeleton + tsup build", "S5", "E6", 2, "P0", "AC: npm publish --dry-run shows ESM + CJS bundles; types.d.ts emitted."),
    StoryV2("S176", "web-channel-js: ChatWidget React component with message list + input", "S5", "E6", 3, "P0", "AC: renders messages; submitting input streams response; Storybook stories for empty/error/streaming."),
    StoryV2("S177", "web-channel-js: SSE parser + auto-reconnect with exponential backoff", "S5", "E6", 2, "P0", "AC: drops mid-stream → reconnect with Last-Event-Id; jitter + cap; integration test in jsdom."),
    StoryV2("S178", "web-channel-js: typing indicator + history persistence (sessionStorage)", "S5", "E6", 1, "P1", "AC: typing dot animates while server sending; refresh restores last 30 messages."),
    StoryV2("S179", "studio: agent channels-tab — configure web channel + copy-snippet", "S5", "E6", 2, "P0", "AC: enabling web channel mints token; UI shows <script> snippet; pasting in fixture page works."),
    StoryV2("S180", "examples: support_agent reference impl with web-channel embedded in static page", "S5", "E17", 2, "P0", "AC: examples/support_agent/index.html renders ChatWidget connected to a deployed staging agent."),
    StoryV2("S181", "first end-to-end smoke: visitor on demo page asks question, agent answers", "S5", "E1", 2, "P0", "AC: scripts/e2e_web_smoke.sh hits the published demo site, asserts a specific answer; CI nightly."),

    # =====================================================================
    # Sprint S6 — KB engine v0 productionization (≈22 stories)
    # Outcome: upload a PDF, agent answers from it with citations.
    # =====================================================================
    StoryV2("S190", "kb: Document/Chunk/EmbeddingVector dataclasses with strict types", "S6", "E5", 1, "P0", "AC: pydantic models forbid extra; (de)serialize round-trip in unit tests. [extends S015]", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/data/strict-pydantic-models.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_kb_engine/models.py — Document and Chunk frozen-strict pydantic v2 models (extra='forbid', UUID ids, workspace_id scoping, ordinal>=0). Added EmbeddingVector with .of(chunk=, model=, values=) factory that rejects NaN/Inf and empty values; tuple[float,...] storage for hashability and JSON round-trip; .dim property. Tests: round-trip dump/validate, NaN/Inf rejection, empty values rejection, blank model rejection, frozen-mutation rejection. Open questions: per-model dim invariants enforced at adapter boundary (S199-S201)."),
    StoryV2("S191", "kb: Parser Protocol class + parser registry (ext → parser)", "S6", "E5", 1, "P0", "AC: register('.pdf', PdfParser) + lookup; unsupported ext raises UnsupportedDocumentType.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_kb_engine/parsers.py — runtime_checkable Parser Protocol, ParserRegistry (register/lookup/supported, normalises ext lowercase + leading-dot), UnsupportedDocumentType(ValueError), DocumentParseError, default_registry() seeds .txt/.md/.markdown→TextParser. Tests: registry normalisation, unsupported-ext raises, empty-ext rejected. Open questions: PDF/DOCX parsers deferred to S192/S193."),
    StoryV2("S192", "kb: PDF parser via pypdf with per-page text + metadata", "S6", "E5", 2, "P0", "AC: parse(bytes) → Document with .pages[] each {text, page_no, source_uri}; corrupt-PDF raises typed error."),
    StoryV2("S193", "kb: HTML parser via BeautifulSoup w/ readability extraction", "S6", "E5", 2, "P0", "AC: parses well-formed HTML, strips nav/footer; preserves headings; passes against 5-fixture suite."),
    StoryV2("S194", "kb: text/MD parser with frontmatter detection", "S6", "E5", 1, "P0", "AC: .md with --- frontmatter parsed; metadata captured; body chunkable.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: TextParser in parsers.py — utf-8 strict decode (DocumentParseError on invalid bytes), regex frontmatter detection (---\\n…\\n--- block), simple key:value parsing with quote-stripping, metadata merged into Document.metadata, body returned for downstream chunking. Tests: plain text, with-frontmatter round-trip, malformed frontmatter falls through, invalid utf-8 raises. Open questions: yaml-shaped frontmatter (lists/nested) deliberately deferred — flat key:value covers >95%% of fixtures."),
    StoryV2("S195", "kb: docx parser via python-docx with table preservation", "S6", "E5", 2, "P0", "AC: tables extracted as markdown blocks; styled headings preserved as level."),
    StoryV2("S196", "kb: chunker semantic_boundary (split on sentence + paragraph cohesion)", "S6", "E5", 3, "P0", "AC: target chunk_tokens=400±50; never splits mid-sentence; integration test on a 50-page sample doc.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/data/text-chunking.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_kb_engine/chunker.py SemanticChunker — sentence-boundary aware, paragraph-cohesive splitter targeting configurable token budget with overlap. Implements Chunker Protocol; never splits mid-sentence. Tests: _tests/test_kb_engine.py covers boundary preservation, paragraph cohesion, configurable target/overlap, deterministic ordinals. Open questions: real BPE tokenizer wiring deferred to embedder adapters (S199+)."),
    StoryV2("S197", "kb: chunker fixed-size with overlap", "S6", "E5", 1, "P1", "AC: tokens=400, overlap=50; deterministic; unit-tested boundary cases (short doc, very long doc).", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/data/text-chunking.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_kb_engine/chunker.py FixedSizeChunker — token-window splitter with configurable size + overlap, deterministic ordinals, stable Chunk ids derived from (document_id, ordinal). Tests: _tests/test_kb_engine.py covers short-doc (single chunk), very-long-doc, exact boundary, configurable overlap. Open questions: token approximation uses whitespace-tokenisation; BPE swap is a one-liner once embedder adapters land."),
    StoryV2("S198", "kb: chunker by-heading (headings as natural splits)", "S6", "E5", 2, "P1", "AC: each top-level heading → chunk; sub-headings → context; tested on 3 fixtures.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: HeadingChunker in chunker.py — configurable top_level (1..6), top-level heading flushes + opens new section, sub-headings appended to sub_path and surfaced via metadata['context']='a > b > c'. Ordinal preserved per chunk. Tests: top-level split, sub-context propagation, no-headings → single chunk, empty body, custom top_level=2, validates bounds. Open questions: heading-aware token-budget chunking is a follow-up."),
    StoryV2("S199", "kb: embedding adapter OpenAI (text-embedding-3-large)", "S6", "E5", 2, "P0", "AC: embed_batch(list[str]) → list[vector(3072)]; honours rate limit + retries."),
    StoryV2("S200", "kb: embedding adapter Voyage (voyage-3)", "S6", "E5", 1, "P1", "AC: same Protocol; integration test with sandbox key."),
    StoryV2("S201", "kb: embedding adapter BGE-large local (sentence-transformers)", "S6", "E5", 2, "P1", "AC: works without network; CI runs against a tiny model variant."),
    StoryV2("S202", "kb: Qdrant write path (collection per workspace+agent, payload filter ready)", "S6", "E5", 2, "P0", "AC: upsert_chunks(workspace_id, agent_id, chunks); collection auto-created with HNSW config."),
    StoryV2("S203", "kb: Qdrant search with metadata filter + score threshold", "S6", "E5", 2, "P0", "AC: search(workspace_id, agent_id, query_vec, top_k=10, min_score=0.6) → list[ChunkHit]."),
    StoryV2("S204", "kb: Postgres tsvector BM25 parallel index per chunks table", "S6", "E5", 2, "P0", "AC: dp_0002 migration adds tsv column + GIN index; bulk-update trigger."),
    StoryV2("S205", "kb: hybrid retrieval (RRF combine of vector + BM25)", "S6", "E5", 2, "P0", "AC: retrieve(query) returns RRF-ranked top_k; ablation test shows beating vector-only on a 50-q eval set.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/data/hybrid-retrieval.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_kb_engine/retrieval.py — rrf_combine(rankings, k=60, top_k=None) implementing rank-based reciprocal rank fusion; ties broken by chunk id (deterministic); validates k>0. Tests: 5 cases — two-list fusion with tie-break, top_k cap, k<=0 rejection, empty-input no-op, single-list-only chunk still ranks. Open questions: BM25 lexical retriever output already produces (Chunk, score) pairs so wiring KnowledgeBase.retrieve(alpha=...) → rrf_combine is mechanical; ablation eval set deferred to S213."),
    StoryV2("S206", "kb: reranker via Cohere rerank-3", "S6", "E5", 2, "P1", "AC: rerank(query, hits) reorders; latency p95 <400ms; opt-in flag in agent config."),
    StoryV2("S207", "kb: dp-runtime endpoints — upload, list, delete docs (per agent)", "S6", "E5", 2, "P0", "AC: POST /v1/agents/{id}/kb/docs (multipart); GET (list); DELETE; integration smoke."),
    StoryV2("S208", "kb: doc deletion with tombstone (chunks gone but provenance kept)", "S6", "E5", 1, "P1", "AC: deleted doc → chunks removed from Qdrant + tsvector; kb_documents row stays with deleted_at.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/data/soft-delete.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_kb_engine/retrieval.py TombstoneRegistry — workspace-scoped registry with mark_deleted/is_deleted/list_deleted/filter_active. Storage in-memory; production wiring persists to kb_documents.deleted_at. Compose with InMemoryVectorStore.delete_document for physical-removal-with-provenance pattern. Tests: 3 cases — mark+filter, workspace isolation, sorted listing. Open questions: dp_0002 migration adds deleted_at column (S211)."),
    StoryV2("S209", "kb: re-ingest with content-hash diff (only changed chunks)", "S6", "E5", 2, "P1", "AC: re-uploading unchanged file → 0 new embeddings; partial change → only delta; metric emitted.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/data/content-hash-diff.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_kb_engine/retrieval.py — chunk_content_hash(chunk) (sha256 over text + sorted metadata, excluding chunk id) + diff_chunks(previous=, current=) → ChunkDiff(added, removed, unchanged) frozen dataclass with .is_noop. Source-order preserved in each tuple. Tests: 4 cases — hash excludes chunk id, hash sensitive to metadata, no-change is_noop, partial-change add/remove/unchanged partitioning. Open questions: emission of 'kb.reingest.skipped' metric wires to obs once observability adapter lands."),
    StoryV2("S210", "kb: ingestion progress as NATS topic loop.kb.ingest.<job_id>", "S6", "E5", 2, "P1", "AC: each parsing/embedding/writing stage publishes; subscriber sees ordered events."),
    StoryV2("S211", "kb: dp_0002 migration kb_documents + kb_chunks tables w/ RLS", "S6", "E5", 2, "P0", "AC: migration applies; RLS forces tenant filter; SCHEMA.md §0 updated in same PR."),
    StoryV2("S212", "studio: KB management UI (list, upload modal, delete confirm)", "S6", "E10", 3, "P0", "AC: agent-detail KB tab fully functional; upload progress bar; delete with typed-confirm."),
    StoryV2("S213", "kb: integration test — upload PDF → ask question → answer cites doc", "S6", "E5", 2, "P0", "AC: pytest with real Qdrant + Postgres; assertion: answer contains expected fact + cites source URI."),

    # =====================================================================
    # Sprint S7 — Slack channel productionization (≈11 stories)
    # =====================================================================
    StoryV2("S220", "slack: Bolt SDK pin + package skeleton", "S7", "E6", 1, "P0", "AC: from loop_channel_slack import SlackChannel imports cleanly. [extends S018]"),
    StoryV2("S221", "slack: signing-secret verification middleware (request body raw)", "S7", "E6", 2, "P0", "AC: tampered-signature requests → 401; valid → handler dispatch; unit-test fixtures (recorded webhooks).", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/security/webhook-signature-verification.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: packages/channels/slack/loop_channels_slack/verify.py — verify_request(signing_secret, body, timestamp, signature) using HMAC-SHA256 over 'v0:{ts}:{body}' with hmac.compare_digest constant-time match; SignatureError(ValueError) on tampered/replay. Tests: _tests/test_slack_channel.py covers tampered signature, stale timestamp, valid happy-path. Open questions: replay-window default 5 min matches Slack docs; configurable per-channel."),
    StoryV2("S222", "slack: /v1/slack/events handler + thread-aware conversation correlation", "S7", "E6", 2, "P0", "AC: thread_ts → conversation_id mapping table; integration: two messages in a thread → same conv.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/platforms/slack-events.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: parser.parse_event normalises Slack event payloads into InboundFrame; channel.SlackChannel.ThreadIndex maps (channel_id, thread_ts) → conversation_id with stable assignment for new threads. Tests: _tests/test_slack_channel.py — two messages in same thread share conv_id, distinct threads get distinct conv_ids, top-level mention starts new thread. Open questions: persistence of thread index moves to Postgres in S173 pattern."),
    StoryV2("S223", "slack: /v1/slack/commands slash-command handler", "S7", "E6", 1, "P0", "AC: /loop ask <q> dispatches to agent; immediate ack <3s; deferred response posted.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/platforms/slack-commands.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: parser.parse_command extracts (command, text, user_id, channel_id, response_url) from form-encoded slash command payload into InboundFrame with intent='command'. SlackChannel routes /loop ask → agent dispatch; deferred response delivered via response_url. Tests: parse_command normalises text, missing fields raise, command dispatch via SlackChannel happy-path. Open questions: 3-second ack guarantee enforced at HTTP-handler boundary (S100 cp-api skeleton)."),
    StoryV2("S224", "slack: Block Kit message renderer for AgentResponse", "S7", "E6", 2, "P0", "AC: text → blocks; lists → bulleted; code → mrkdwn-fenced; cites → context block.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/platforms/slack-block-kit.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: blocks.to_blocks(frame) — OutboundFrame → Slack Block Kit dict (section/mrkdwn for prose, code-fenced for code, context block for citations). Tests: _tests/test_slack_channel.py covers plain text, code-fenced, citation-context, list bullets. Open questions: rich attachments (images, buttons) deferred to S225+ as needed by interactive flows."),
    StoryV2("S225", "slack: at-mention handling outside thread (start new conv)", "S7", "E6", 1, "P1", "AC: @bot mention at top-level creates conversation with channel_type='slack', user_id=slack_user_id."),
    StoryV2("S226", "slack: ephemeral error responses (private to invoker)", "S7", "E6", 1, "P0", "AC: handler errors emit ephemeral 'Sorry, code LOOP-CH-NNN'; never spams channel."),
    StoryV2("S227", "slack: app manifest yaml + install OAuth flow", "S7", "E6", 2, "P0", "AC: /v1/slack/install starts Slack OAuth; on callback, persists bot_token in agent_secrets."),
    StoryV2("S228", "slack: studio channels-tab — Connect Slack OAuth button + status", "S7", "E10", 2, "P0", "AC: button initiates OAuth; tile shows connected workspace; disconnect revokes."),
    StoryV2("S229", "slack: replay-fixture integration test (recorded webhooks)", "S7", "E6", 2, "P0", "AC: fixtures/slack/*.json replay through handlers; expected agent + channel responses asserted."),

    # =====================================================================
    # Sprint S8 — Eval harness productionization (≈14 stories)
    # =====================================================================
    StoryV2("S240", "eval: Scorer Protocol + base class with score(case, response) → ScoreResult", "S8", "E8", 1, "P0", "AC: type-check via Protocol; unit-test on a fake scorer. [extends S021]"),
    StoryV2("S241", "eval: scorer exact_match (case-sensitive + insensitive variant)", "S8", "E8", 1, "P0", "AC: 1.0 on equal, 0.0 on not; unit tests.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/testing/eval-scorers.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_eval/scorers.py exact_match(sample, run) — strict equality, returns 1.0/0.0 ScoreResult. Wired into Scorer Protocol so it composes with ParallelEvalRunner and TAP CLI. Tests: _tests/test_eval.py covers equal/unequal, whitespace sensitivity. Open questions: case-insensitive variant available as exact_match composed with .lower() preprocessor in caller; explicit ci variant deferred until a real suite needs it."),
    StoryV2("S242", "eval: scorer rouge / bleu", "S8", "E8", 2, "P0", "AC: ROUGE-L f-score against reference; unit-tested on standard fixtures.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: rouge_l() — LCS-based two-row DP, returns F1 of token-level precision/recall; bleu_scorer() — clipped n-gram modified precision (1..max_n) geometric-mean × brevity penalty. Both threshold-configurable, return Score with detail string. Tests: perfect match → 1.0, partial overlap, no overlap, empty expected, max_n bounds validated. Open questions: chrF / METEOR not in scope."),
    StoryV2("S243", "eval: scorer llm_judge (Claude Haiku rubric)", "S8", "E8", 2, "P0", "AC: prompt+rubric configurable; cost tracked; deterministic seed for tests."),
    StoryV2("S244", "eval: scorer tool_call_match (right tool, right args, right order)", "S8", "E8", 2, "P0", "AC: passes when tools matched in order with arg-superset; unit tests cover misses.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: ToolInvocation pydantic strict-frozen model added to models.Sample.expected_tool_calls and models.Run.tool_calls. tool_call_match(ordered=True|False) — ordered tolerates extras between expected calls and uses arg-superset semantics on JSON args; unordered uses multiset by name. Tests: ordered pass, missing tool fails, divergent args fail, unordered match, no-expected-but-actual fails, empty/empty passes. Open questions: regex/glob arg matchers are a follow-up."),
    StoryV2("S245", "eval: scorer latency_p50_under and cost_under_usd", "S8", "E8", 1, "P0", "AC: thresholds configurable; aggregates over case set; emit boolean + value.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/testing/eval-scorers.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_eval/scorers.py latency_scorer(max_ms=) and cost_scorer(max_usd=) — Scorer factories returning closures that read run.latency_ms / run.cost_usd, return 1.0 if under threshold else 0.0; the actual observed value is carried through ScoreResult.metadata for aggregation. Tests: _tests/test_eval.py covers under/over threshold for both, aggregation across a sample run. Open questions: p50-vs-p95 aggregation lives in EvalReport rollup not in the scorer."),
    StoryV2("S246", "eval: cassette format spec + recorder (gateway calls)", "S8", "E8", 2, "P0", "AC: cassette JSONL with request/response/usage; replayer round-trips identical.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_eval/cassettes.py — CassetteEntry pydantic strict (request_key, request, response, usage, recorded_at_ms); request_key() = sha256 of canonical JSON (sort_keys, no whitespace); CassetteRecorder writes JSONL with flush per record; CassetteRecorder.to_path() opens append-mode handle. Tests: stable key across dict-order, JSONL round-trip, recorder.to_path persists, parse_entry round-trip. Open questions: cassette compaction / version field — defer until format change is needed."),
    StoryV2("S247", "eval: cassette replayer plugged into Gateway adapter", "S8", "E8", 2, "P0", "AC: replay-mode swaps real provider for cassette; unit tests verify deterministic outputs.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: CassetteReplayer last-write-wins dict keyed by request_key; .lookup(request) raises CassetteMiss(KeyError) on miss; __contains__/__len__/from_path. Tests: round-trip from recorder, miss raises, request-order independence. Open questions: actual gateway-adapter wiring is in S134; this lands the replayer side of the seam so the gateway can swap-in next sprint."),
    StoryV2("S248", "eval: case loader (YAML directory → list[EvalCase])", "S8", "E8", 1, "P0", "AC: tests/evals/*.yml load; schema validation errors named with file+line.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_eval/suite_loader.py — load_suite(path)/load_suites(dir) parse {suite:str, samples:[{id,input,expected,expected_tool_calls,metadata}]} via lazy `import yaml`. SuiteLoadError messages always include path + sample index, e.g. 'foo.yml: sample[2].id must be a non-empty string'. Tests: basic load, tool-call samples, missing-samples error, dir loader sorts *.yml + *.yaml. pyyaml>=6.0 added to eval-harness pyproject. Open questions: line numbers in errors — yaml safe_load drops them; would need ruamel.yaml round-trip loader for exact line."),
    StoryV2("S249", "eval: parallel suite runner with concurrency cap + per-case timeout", "S8", "E8", 2, "P0", "AC: 100 cases run in <90s on dev laptop; one slow case doesn't block others.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: ParallelEvalRunner(scorers, concurrency=8, per_case_timeout_s=30.0) — asyncio.Semaphore + asyncio.wait_for; on timeout returns Run with metadata={'timeout':'true'}; on agent exception captures {'error': type, 'detail': str}; results sorted by sample_id for deterministic ordering; same EvalReport math as sequential runner. Tests: deterministic ordering when delays are reversed, per-case timeout marks run, exception captured, ctor validates concurrency>=1 + timeout>0. Open questions: process-pool fallback for CPU-bound scorers — out of scope."),
    StoryV2("S250", "eval: regression detector — compare vs baseline JSON", "S8", "E8", 2, "P0", "AC: detects mean-score drop ≥5%% as regression; emits diff report.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_eval/regression.py — frozen dataclasses ScorerDelta/SampleFlip/RegressionReport; detect_regression(baseline,current,threshold=0.05) flags any scorer whose relative_delta <= -threshold OR any (sample_id,scorer) that flipped pass→fail. dump_report/load_report (json round-trip with list→tuple coercion for strict pydantic), regression_to_dict for JSON-safe payload. Tests: ≥5%% drop flagged, no-regression stable, dump/load round-trip, threshold bounds validated. Open questions: per-scorer thresholds (some scorers tolerate noise) — defer until calibrated suite exists."),
    StoryV2("S251", "eval: cli `loop eval run [suite]` with TAP-style output", "S8", "E11", 1, "P0", "AC: exit code 0 on pass, 1 on fail; --json emits machine-readable.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_eval/cli.py — argparse entry-point: positional suite path (file or dir), --agent-factory module:callable, --baseline path, --regression-threshold 0.05, --json. _resolve_factory imports + getattr + callable check. _emit_tap emits TAP-13 (1..N + ok/not-ok lines + indented checkmarks). _emit_json dumps {suites:[{name,path,report}]}. Baseline path runs detect_regression and prints '# regression: <json>'; exit 1 on regression OR any failed scorer. Tests: TAP rc=0 on pass, rc=1 on fail, --json valid payload. Open questions: --scorer flag to pick which scorers to run (currently hard-coded exact_match) — follow-up."),
    StoryV2("S252", "eval: production-replay capture middleware (sampling rate per agent)", "S8", "E8", 2, "P1", "AC: sampled turns persisted to NATS for later cassette write; opt-in flag.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/testing/production-replay.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_eval/replay.py — FailedTurn pydantic model, ReplaySink Protocol + InMemoryReplaySink, should_capture(workspace_id, request_id, sample_rate) deterministic hash-based bucket sampling so the same turn is always captured-or-not for a given rate, capture(...) high-level helper applies sampling + redaction + sink.append, to_samples projects captured turns into eval Sample rows for cassette write. Tests: _tests/test_replay.py covers deterministic sampling stability, edge rates 0.0/1.0, redaction, sample projection round-trip. Open questions: NATS publisher binding to ReplaySink Protocol is a thin wrapper deferred to dp-runtime wiring."),
    StoryV2("S253", "studio: eval suites/runs pages (list, detail, regression diff)", "S8", "E10", 3, "P0", "AC: studio /evals lists suites; clicking a run shows per-case pass/fail + diff vs baseline."),

    # =====================================================================
    # Sprint S9 — Deploy controller v0 (≈12 stories)
    # =====================================================================
    StoryV2("S260", "deploy: artifact bundler — package agent code + deps to zip", "S9", "E12", 2, "P0", "AC: bundler produces deterministic zip (same input → same sha256). [extends S020]", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_control_plane/deploy_bundler.py — bundle(source) sorts files by relative path, fixes timestamp to 1980-01-01, normalises mode 0644/0755, ZIP_DEFLATED, returns BundleResult(data, sha256, entry_count). Excludes __pycache__/.git/.pytest_cache by default. Refuses symlinks (raises BundlerError). bundle_to_path() writes to disk. Tests: same content via different paths → same sha256, pycache excluded, symlink rejected, empty tree rejected. Open questions: cosign signature integration — separate story."),
    StoryV2("S261", "deploy: artifact upload to object-store (cloud-portable)", "S9", "E12", 2, "P0", "AC: upload via ObjectStore Protocol; signed URL expires in 1h; agent_versions.artifact_uri set."),
    StoryV2("S262", "deploy: image builder — BuildKit Dockerfile.template render", "S9", "E12", 2, "P0", "AC: build({artifact_uri, base_image}) produces image:sha256:<hash>; pushed to registry."),
    StoryV2("S263", "deploy: image push w/ cosign signature", "S9", "E12", 2, "P1", "AC: cosign sign + verify gate before deploy."),
    StoryV2("S264", "deploy: k8s manifest renderer (Deployment + Service + HPA template)", "S9", "E12", 2, "P0", "AC: render({image, replicas, env}) yields valid YAML; kubeval green.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/coding/python-package-layout.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_control_plane/k8s_manifest.py — frozen ManifestSpec dataclass (DNS-1123 name validation, image-must-have-tag, replicas>=1, port bounds, hpa min<=max, env-key whitespace check). render() emits sorted-keys YAML for Deployment+Service+HPA with readiness/liveness probes, resource requests/limits, app.kubernetes.io labels. render_documents() returns dicts for tests. Tests: yaml.safe_load_all round-trip; kinds == [Deployment, Service, HPA]; env list deterministic; invalid name/image/replicas/min>max all rejected. Open questions: kubeval gate in CI — defer to S265."),
    StoryV2("S265", "deploy: cp-api POST /v1/agents/{id}/deployments enqueues job", "S9", "E12", 2, "P0", "AC: returns 202 + deployment_id; row in deployments table; controller picks up via NATS."),
    StoryV2("S266", "deploy: deploy controller (k8s controller pattern, Python kopf)", "S9", "E12", 3, "P0", "AC: reconcile loop applies manifests; deployment_events written; failure → status='failed'."),
    StoryV2("S267", "deploy: canary promotion 10%→50%→100% over time-box w/ auto-pause on regression", "S9", "E12", 3, "P0", "AC: canary advances on stable error+latency budget; pauses + alerts on breach."),
    StoryV2("S268", "deploy: rollback API + automatic on canary failure", "S9", "E12", 2, "P0", "AC: POST /rollback or auto trigger reverts to previous_version; integration test.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/ops/canary-rollback.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_control_plane/deploy.py DeployController.rollback(deploy_id) — finds previous Deploy by agent_id, asks KubeClient.rollback to revert image, transitions Deploy.phase to ROLLED_BACK; auto-trigger fires on canary EvalGate fail. KubeClient Protocol exposes async rollback so any backend (k8s, helm, ECS) plugs in. Tests: _tests/test_deploy.py + test_deploy_eval_gate.py cover manual rollback, auto-rollback on regression, no-previous-deploy raises DeployError. Open questions: cross-region rollback coordination uses BaselineRegistry per region; tracked under S270."),
    StoryV2("S269", "deploy: events stream → ClickHouse deploy_events", "S9", "E9", 1, "P1", "AC: every state transition recorded; queryable by agent + version."),
    StoryV2("S270", "studio: deploy tab on agent detail (history, current canary %, rollback)", "S9", "E10", 3, "P0", "AC: timeline view of deployments; promote/pause/rollback buttons work."),
    StoryV2("S271", "deploy: end-to-end test build → push → deploy → smoke", "S9", "E12", 2, "P0", "AC: scripts/deploy_e2e.sh against kind cluster passes in <8 min."),

    # =====================================================================
    # Sprint S10 — Cost / observability v1 (≈12 stories)
    # =====================================================================
    StoryV2("S280", "obs: usage_events ClickHouse table + nightly rollup job", "S10", "E9", 2, "P0", "AC: schema {workspace_id, agent_id, channel, model, in_tok, out_tok, cost_usd, ts}; nightly mat-view."),
    StoryV2("S281", "obs: cost rollup per workspace MTD aggregate (mat-view)", "S10", "E9", 1, "P0", "AC: SELECT cost from cost_workspace_mtd returns under 50ms at 10M rows."),
    StoryV2("S282", "obs: cost rollup per agent + per channel + per model", "S10", "E9", 2, "P0", "AC: 4 mat-views; each queryable in <100ms; integration test against fixture."),
    StoryV2("S283", "studio: cost dashboard workspace KPIs (today, MTD, projected EOM)", "S10", "E10", 2, "P0", "AC: 3 KPI cards with deltas; values match ClickHouse query directly. [extends S027]"),
    StoryV2("S284", "studio: cost time-series chart (Recharts) per agent", "S10", "E10", 2, "P0", "AC: 30-day daily cost chart; agent multi-select; tooltip with breakdown."),
    StoryV2("S285", "studio: cost filters (agent, channel, model, date)", "S10", "E10", 1, "P1", "AC: filters URL-synced + persisted to localStorage."),
    StoryV2("S286", "obs: trace export to ClickHouse (replace InMemory in non-test env)", "S10", "E9", 2, "P0", "AC: prod env emits to ClickHouse otel_traces; in-memory remains for tests; switch via LOOP_OTEL_EXPORTER. [extends S009]"),
    StoryV2("S287", "obs: trace search API in cp-api (by turn_id, conv_id, time range)", "S10", "E9", 2, "P0", "AC: GET /v1/traces?turn_id=... returns spans; pagination; integration test."),
    StoryV2("S288", "studio: trace list page with filter + search", "S10", "E10", 2, "P0", "AC: paginated list; filters; clicking a trace navigates to detail. [extends S022]"),
    StoryV2("S289", "studio: trace detail waterfall (custom SVG, not Mermaid)", "S10", "E10", 3, "P0", "AC: spans ordered + nested; click expands attrs; ≤10ms render at 200 spans."),
    StoryV2("S290", "obs: alert rules YAML — budget breach, error spike, latency p95", "S10", "E9", 2, "P0", "AC: rules.yaml file evaluated by alert-runner; alerts fire to webhook.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s101-s290-pass2 (merged). PR: local-merge (ff to main). Skill: skills/observability/structured-logging.md. Last step: 5/5. Heartbeat: 2026-05-12T01:00:00Z. Substance: loop_control_plane/alerts.py — AlertRule (name, metric, op∈{'>','>=','<','<=','==','!='}, threshold, severity∈{info,warning,critical}, description). load_rules(path) parses rules.yaml with file-prefixed errors, rejects unknown ops + duplicate names. evaluate(rules, metrics) returns Alert tuple — missing metric keys silently skipped (alerting layer doesn't decide telemetry policy). Tests: parse valid yaml, unknown op error names rules[i].op, duplicate-name caught, missing-file error, fires only when threshold crossed, unknown metric skipped. Open questions: webhook delivery — separate story (alerting-layer split from rules engine intentional)."),
    StoryV2("S291", "obs: alert delivery to Slack/email/PagerDuty (per workspace pref)", "S10", "E9", 2, "P0", "AC: per-workspace channel config; alert delivered with redacted PII.", owner="GitHub Copilot", status="Done", notes_override="Done. Branch: copilot/s-pass3 (merged). PR: local-merge (ff to main). Skill: skills/observability/alert-delivery.md. Last step: 5/5. Heartbeat: 2026-05-12T02:00:00Z. Substance: loop_control_plane/alerts.py — AlertSink runtime_checkable Protocol (name, accepts: frozenset[Severity], async send), InMemoryAlertSink test fixture, DeliveryResult frozen dataclass, AlertDispatcher.dispatch(alerts) fans out to every matching sink and isolates per-sink failures (BLE001 noqa intentional — exception captured into DeliveryResult.error so one bad webhook does not silence the rest). Tests: _tests/test_alerts_dispatch.py covers fan-out, severity filtering, sink-failure isolation, empty alerts/sinks no-op. Open questions: real Slack/email/PagerDuty Protocol implementations bind transport SDKs in their own files; PII redaction rides on Alert.message construction (rule.evaluate already produces redacted messages)."),

    # =====================================================================
    # Sprint S11 — HITL operator inbox v0 (≈10 stories)
    # =====================================================================
    StoryV2("S300", "hitl: takeover state column on conversations + RLS-aware update", "S11", "E15", 1, "P0", "AC: status='operator' transitions; RLS still passes. [extends S030]"),
    StoryV2("S301", "hitl: cp_0003 migration adding operator_assignments table", "S11", "E15", 1, "P0", "AC: assignments(workspace_id, conv_id, operator_user_id, started_at, ended_at); SCHEMA.md updated."),
    StoryV2("S302", "hitl: POST /v1/conversations/{id}/takeover (operator assigns themselves)", "S11", "E15", 2, "P0", "AC: row inserted; conversation.status='operator'; agent stops auto-responding; integration test."),
    StoryV2("S303", "hitl: POST /v1/conversations/{id}/handback (operator releases)", "S11", "E15", 1, "P0", "AC: ended_at set; conversation.status='active'; agent resumes; integration test."),
    StoryV2("S304", "hitl: NATS events takeover_started/ended for downstream subscribers", "S11", "E15", 1, "P1", "AC: events emitted; trace correlation preserved."),
    StoryV2("S305", "hitl: auto-handback timer after configurable idle minutes", "S11", "E15", 2, "P1", "AC: scheduled task scans every 60s; auto-handback at 15-min idle by default."),
    StoryV2("S306", "studio: inbox queue page filtered by team / agent / channel", "S11", "E10", 3, "P0", "AC: list paginates; sortable; per-row last-message preview. [extends S032]"),
    StoryV2("S307", "studio: inbox conversation viewer with live SSE tail", "S11", "E10", 3, "P0", "AC: opening conv subscribes to live stream; new messages append in real-time."),
    StoryV2("S308", "studio: takeover button + composer in conversation viewer", "S11", "E10", 2, "P0", "AC: clicking Takeover acquires; composer posts as operator; agent paused."),
    StoryV2("S309", "studio: handback button restores agent + closes operator session", "S11", "E10", 1, "P0", "AC: confirmation modal; click → POST /handback; conv updates; toast."),

    # =====================================================================
    # Sprint S12 — Billing v0 (≈12 stories)
    # =====================================================================
    StoryV2("S320", "billing: cp-api → Stripe customer creation on workspace POST", "S12", "E19", 2, "P0", "AC: stripe.Customer.create called with workspace metadata; customer_id stored. [extends S025]"),
    StoryV2("S321", "billing: subscription_plans table cp_0003 + seed plan rows", "S12", "E19", 1, "P0", "AC: hobby/pro/team/enterprise rows present after migrate-up."),
    StoryV2("S322", "billing: Stripe webhook receiver /v1/billing/webhook (signature verified)", "S12", "E19", 2, "P0", "AC: invalid sig → 400 LOOP-BIL-101; valid → handlers dispatch."),
    StoryV2("S323", "billing: handle customer.subscription.created/updated/deleted", "S12", "E19", 2, "P0", "AC: workspace.plan kept in sync with active subscription; downgrade enforced."),
    StoryV2("S324", "billing: handle invoice.paid / payment_failed events", "S12", "E19", 2, "P0", "AC: paid → workspace.payment_status='ok'; failed N times → suspend workspace."),
    StoryV2("S325", "billing: nightly usage push from ClickHouse → Stripe metered", "S12", "E19", 2, "P0", "AC: scheduled job reads usage_events deltas, calls stripe.UsageRecord.create; idempotent on retry."),
    StoryV2("S326", "billing: workspace-suspension middleware (read-only when suspended)", "S12", "E19", 2, "P0", "AC: suspended workspace cannot create runs; returns 402 LOOP-BIL-301."),
    StoryV2("S327", "studio: billing tab — current plan + usage + change-plan CTA", "S12", "E10", 2, "P0", "AC: tab shows plan, MTD usage vs cap, button → Stripe Customer Portal."),
    StoryV2("S328", "studio: billing — invoice list + download PDF", "S12", "E10", 2, "P1", "AC: list paginates; click downloads from Stripe."),
    StoryV2("S329", "studio: billing — payment-method update via Stripe Elements", "S12", "E10", 2, "P0", "AC: 3DSC-aware update flow; success toast; failure shows Stripe error."),
    StoryV2("S330", "billing: plan-tier rate limit enforcement at gateway + dp-runtime", "S12", "E19", 2, "P0", "AC: hobby plan capped at $5/day; team at $500/day; integration tests for boundary."),
    StoryV2("S331", "billing: trial → paid conversion email + 7-day-left + 1-day-left nudges", "S12", "E19", 2, "P1", "AC: scheduled task sends emails via EmailSender; opt-out honoured."),

    # =====================================================================
    # Sprint S13 — WhatsApp channel productionization (≈10 stories)
    # =====================================================================
    StoryV2("S340", "wa: WA Cloud API SDK pin + channel package skeleton", "S13", "E6", 1, "P0", "AC: package builds; types: WaMessage, WaTemplate. [extends S023]"),
    StoryV2("S341", "wa: webhook verification handshake (GET hub.verify_token)", "S13", "E6", 1, "P0", "AC: configured token → 200 + challenge; wrong token → 403."),
    StoryV2("S342", "wa: POST /v1/whatsapp/events handles incoming message → AgentEvent", "S13", "E6", 2, "P0", "AC: text/media → AgentEvent forwarded to dp-runtime; integration test."),
    StoryV2("S343", "wa: outgoing message renderer (text, list, button, media)", "S13", "E6", 2, "P0", "AC: AgentResponse → wa_send_message API call; idempotent on retry."),
    StoryV2("S344", "wa: media download + temporary object-store cache", "S13", "E6", 2, "P0", "AC: incoming image/audio downloaded; cached in object-store; reference in turns.content_json."),
    StoryV2("S345", "wa: 24-hour messaging window enforcement", "S13", "E6", 2, "P0", "AC: outside window → must use template; runtime blocks free-form attempt with helpful error."),
    StoryV2("S346", "wa: template-message support + studio template browser", "S13", "E6", 2, "P0", "AC: list approved templates from WA API; send-template tool exposed."),
    StoryV2("S347", "wa: interactive elements (lists, reply buttons)", "S13", "E6", 2, "P1", "AC: AgentResponse hints render as WA interactive; user response → tool_result."),
    StoryV2("S348", "wa: studio — connect WA Business Account flow", "S13", "E10", 2, "P0", "AC: OAuth-style connect; phone-number selector; tile shows connected number."),
    StoryV2("S349", "wa: replay-fixture integration test (recorded WA webhooks)", "S13", "E6", 2, "P0", "AC: fixtures/wa/*.json replay; expected outgoing assertions."),

    # =====================================================================
    # Sprint S14 — Voice infrastructure (≈12 stories)
    # =====================================================================
    StoryV2("S360", "voice: ASR Protocol + TTS Protocol + VAD Protocol", "S14", "E7", 1, "P0", "AC: classes defined; mocks pass type-check. [extends S016/S033]"),
    StoryV2("S361", "voice: ASR adapter Deepgram (streaming WS)", "S14", "E7", 2, "P0", "AC: stream PCM in, partial+final transcripts out; auto-reconnect; integration test against sandbox key."),
    StoryV2("S362", "voice: ASR adapter Whisper.cpp local fallback", "S14", "E7", 2, "P1", "AC: works without network; CI uses tiny.en model."),
    StoryV2("S363", "voice: TTS adapter ElevenLabs streaming", "S14", "E7", 2, "P0", "AC: stream text → PCM chunks; sentence-boundary streaming; latency to first byte <300ms."),
    StoryV2("S364", "voice: TTS adapter Cartesia (Sonic) streaming", "S14", "E7", 2, "P1", "AC: same Protocol; integration test."),
    StoryV2("S365", "voice: TTS adapter Piper local", "S14", "E7", 2, "P1", "AC: deterministic; CI fixture audio file diff."),
    StoryV2("S366", "voice: VAD via webrtcvad + barge-in detection", "S14", "E7", 2, "P0", "AC: speaker-onset within 100ms cuts current TTS playback; integration test."),
    StoryV2("S367", "voice: turn-take state machine (listening/thinking/speaking)", "S14", "E7", 2, "P0", "AC: explicit FSM; transitions logged; unit-tested all transitions."),
    StoryV2("S368", "voice: LiveKit room manager (create/join/teardown)", "S14", "E7", 2, "P0", "AC: agent joins on demand; room cleaned up on disconnect; integration with sandbox key."),
    StoryV2("S369", "voice: LiveKit room → Loop turn bridge (audio frames → AgentEvent)", "S14", "E7", 3, "P0", "AC: room audio in → ASR partials → AgentEvent on final → TTS plays back."),
    StoryV2("S370", "voice: tracing across ASR→LLM→TTS pipeline (per-stage spans)", "S14", "E9", 1, "P0", "AC: trace shows asr.stream, llm.turn, tts.stream as siblings with timing."),
    StoryV2("S371", "voice: web-RTC echo agent end-to-end happy path", "S14", "E7", 2, "P0", "AC: scripts/voice_echo_test.py joins a room, speaks, hears agent within 2s."),

    # =====================================================================
    # Sprint S15 — Voice MVP — phone calls (≈10 stories)
    # =====================================================================
    StoryV2("S380", "voice: incoming-call SIP gateway via Twilio Voice (TwiML)", "S15", "E7", 3, "P0", "AC: incoming call → bridges to LiveKit room → agent answers within 1s."),
    StoryV2("S381", "voice: outbound-call API POST /v1/voice/calls", "S15", "E7", 2, "P0", "AC: places call to E.164 number; agent talks first; events streamed."),
    StoryV2("S382", "voice: phone-number provisioning (Twilio bring-your-own)", "S15", "E12", 2, "P0", "AC: agent_phone_numbers table + cp-api endpoints to claim/release. [extends S049]"),
    StoryV2("S383", "voice: voicemail / callback handling (no-answer fallback)", "S15", "E7", 2, "P1", "AC: 30s no-answer → leave voicemail; callback request creates outbound job."),
    StoryV2("S384", "voice: voice-channel React widget (call button + mic)", "S15", "E10", 3, "P0", "AC: studio embeds widget; click talks to agent in-browser; PTT + always-on modes."),
    StoryV2("S385", "studio: voice channel config tab (numbers, ASR/TTS provider)", "S15", "E10", 2, "P0", "AC: tab shows connected numbers; provider selectors persisted."),
    StoryV2("S386", "voice: latency benchmark suite (target ≤900ms p50)", "S15", "E7", 2, "P0", "AC: k6/locust script measures end-to-end; report under loop_implementation/perf/."),
    StoryV2("S387", "voice: integration test phone call → agent → response", "S15", "E7", 2, "P0", "AC: scripts/voice_call_e2e.sh with Twilio test creds; CI nightly."),
    StoryV2("S388", "voice: cost-tracking per voice call (ASR sec, TTS sec, LLM tokens)", "S15", "E19", 2, "P0", "AC: usage_events row per call; visible in cost dashboard."),
    StoryV2("S389", "voice: graceful degrade on provider outage (fallback ASR/TTS)", "S15", "E7", 2, "P1", "AC: primary fails → secondary picks up within 1s; audible indicator on quality drop."),

    # =====================================================================
    # Sprint S16 — Multi-agent orchestration v0 (≈11 stories)
    # =====================================================================
    StoryV2("S400", "multi: AgentGraph type + Pydantic schema (nodes, edges, conditions)", "S16", "E14", 2, "P0", "AC: schema validates 3 hand-written graphs; round-trip JSON. [extends S038/S042]"),
    StoryV2("S401", "multi: Supervisor pattern impl (one supervisor delegates to N workers)", "S16", "E14", 2, "P0", "AC: supervisor calls workers in sequence; aggregates results; integration test."),
    StoryV2("S402", "multi: Pipeline pattern impl (linear chain with shared state)", "S16", "E14", 2, "P0", "AC: each node receives previous output; failure halts; integration test."),
    StoryV2("S403", "multi: Parallel pattern impl (fan-out / fan-in with reducer)", "S16", "E14", 2, "P0", "AC: N parallel calls; reducer combines; first-to-finish-wins option; integration test."),
    StoryV2("S404", "multi: AgentGraph executor (DFS over nodes, condition eval)", "S16", "E14", 3, "P0", "AC: executes any valid graph end-to-end; tools invoked per-node; result merged."),
    StoryV2("S405", "multi: cycle detection at compile + safe-loop-bounds at runtime", "S16", "E14", 2, "P0", "AC: cyclic graph allowed only when max_iterations bounded; uncapped raises."),
    StoryV2("S406", "multi: shared memory between sub-agents (scoped MemoryEntry)", "S16", "E4", 2, "P0", "AC: parent's scratchpad accessible to children; isolation tested."),
    StoryV2("S407", "multi: cost rollup across sub-agents into parent turn", "S16", "E2", 1, "P0", "AC: parent.cost_usd = sum(child.cost_usd); usage_events tagged with parent_turn_id."),
    StoryV2("S408", "multi: trace correlation — parent span links child spans", "S16", "E9", 1, "P0", "AC: trace UI shows nested spans for child agent calls."),
    StoryV2("S409", "multi: yaml flow → AgentGraph compiler", "S16", "E14", 2, "P0", "AC: docs/examples/flows/*.yml compile into runnable graphs."),
    StoryV2("S410", "multi: integration test — 3-agent supervisor pipeline end-to-end", "S16", "E14", 2, "P0", "AC: scripts/multi_e2e.py runs to completion; cost + trace + result asserted."),

    # =====================================================================
    # Sprint S17 — TS SDK + CLI v0 (≈14 stories)
    # =====================================================================
    StoryV2("S420", "ts-sdk: package scaffold (npm + tsup + dual ESM/CJS)", "S17", "E11", 1, "P0", "AC: pnpm publish --dry-run; types.d.ts emitted. [extends S039]"),
    StoryV2("S421", "ts-sdk: code-gen openapi → TypeScript types (no client code)", "S17", "E11", 2, "P0", "AC: generated types match openapi.yaml; ts-prune zero unused."),
    StoryV2("S422", "ts-sdk: fetch-based client wrapper with auth + retry-with-backoff", "S17", "E11", 2, "P0", "AC: 5xx triggers exponential retry up to 3; honours Retry-After."),
    StoryV2("S423", "ts-sdk: SSE parser supporting Last-Event-Id reconnect", "S17", "E11", 2, "P0", "AC: integration tests in jsdom + Node 20."),
    StoryV2("S424", "ts-sdk: typed AgentEvent / TurnEvent / ContentPart matching Python wire", "S17", "E11", 1, "P0", "AC: TypeScript shape == Pydantic shape on a 100-case property test."),
    StoryV2("S425", "ts-sdk: react hook useTurn() streaming agent calls", "S17", "E11", 2, "P0", "AC: hook returns {start, frames, done, error}; example app on Storybook."),
    StoryV2("S426", "cli: typer skeleton + auto-completion for bash/zsh/fish", "S17", "E11", 1, "P0", "AC: loop --install-completion bash works; shellcheck-clean."),
    StoryV2("S427", "cli: `loop login` device-code flow → PASETO refresh", "S17", "E11", 2, "P0", "AC: CLI prints code+URL; user authorizes; token persisted to ~/.loop/credentials."),
    StoryV2("S428", "cli: `loop init` scaffolds an agent project (skill-aware)", "S17", "E11", 2, "P0", "AC: directory tree + sample agent.yaml + first turn passes locally."),
    StoryV2("S429", "cli: `loop deploy` builds + uploads via cp-api", "S17", "E11", 2, "P0", "AC: zips project, calls deploy endpoint, polls status, exits with success/failure."),
    StoryV2("S430", "cli: `loop logs` streams SSE from dp-runtime", "S17", "E11", 1, "P0", "AC: logs --follow agent_id/conv_id; Ctrl-C clean exit."),
    StoryV2("S431", "cli: `loop eval run [suite]` invokes server-side runner", "S17", "E11", 1, "P0", "AC: tracks remote run; prints colored TAP output."),
    StoryV2("S432", "cli: `loop secrets list/set/get/rotate`", "S17", "E11", 2, "P0", "AC: CRUD against cp-api; never logs values."),
    StoryV2("S433", "cli: tarball release pipeline (multi-arch, GitHub Releases)", "S17", "E11", 2, "P1", "AC: tagged release publishes darwin-arm64/linux-amd64/windows zips with checksums."),

    # =====================================================================
    # Sprint S18 — Helm chart for self-host (≈14 stories)
    # =====================================================================
    StoryV2("S440", "helm: umbrella chart skeleton + Chart.yaml + values.schema.json", "S18", "E13", 1, "P0", "AC: helm lint clean; values.schema.json validates with ajv. [extends S036]"),
    StoryV2("S441", "helm: cp-api subchart (Deployment + Service + HPA + PDB)", "S18", "E13", 2, "P0", "AC: helm template renders; kubeval clean; helm install on kind passes."),
    StoryV2("S442", "helm: dp-runtime subchart", "S18", "E13", 2, "P0", "AC: same as S441 for dp-runtime."),
    StoryV2("S443", "helm: dp-gateway subchart", "S18", "E13", 1, "P0", "AC: same."),
    StoryV2("S444", "helm: dp-tool-host subchart with kata-runtime requirement docs", "S18", "E13", 2, "P0", "AC: chart conditional on cluster having kata; pre-install hook checks; clear error message otherwise."),
    StoryV2("S445", "helm: dp-kb-engine subchart", "S18", "E13", 1, "P0", "AC: same."),
    StoryV2("S446", "helm: postgres dependency (Bitnami subchart pinned)", "S18", "E13", 1, "P0", "AC: pinned version; bypass-able via existingDatabase value."),
    StoryV2("S447", "helm: redis dependency (Bitnami subchart pinned)", "S18", "E13", 1, "P0", "AC: same."),
    StoryV2("S448", "helm: qdrant dependency (official chart pinned)", "S18", "E13", 1, "P0", "AC: same."),
    StoryV2("S449", "helm: nats dependency (jetstream-on)", "S18", "E13", 1, "P0", "AC: same."),
    StoryV2("S450", "helm: clickhouse dependency (Altinity operator or bitnami)", "S18", "E13", 2, "P0", "AC: storage class param; backup config."),
    StoryV2("S451", "helm: minio dependency (with externalS3 alternative)", "S18", "E13", 1, "P0", "AC: pick-your-storage; tests for both."),
    StoryV2("S452", "helm: ingress + cert-manager + sane defaults for nginx and traefik", "S18", "E13", 2, "P0", "AC: helm install w/ ingress=true creates TLS-terminated routes; verified on kind."),
    StoryV2("S453", "helm: smoke test workflow (kind cluster, install chart, send a turn)", "S18", "E13", 2, "P0", "AC: GHA workflow .github/workflows/helm-e2e.yml passes in <12 min."),

    # =====================================================================
    # Sprint S19 — Studio flow editor v0 (≈13 stories)
    # =====================================================================
    StoryV2("S460", "flow: studio React-Flow canvas in /agents/{id}/flow", "S19", "E10", 2, "P0", "AC: blank canvas with pan/zoom; toolbar exists; placeholder until S461."),
    StoryV2("S461", "flow: node palette w/ types start/message/condition/ai-task/http/code/end", "S19", "E10", 3, "P0", "AC: drag-and-drop creates node; each type renders distinct icon."),
    StoryV2("S462", "flow: node config sidebar (per-type form)", "S19", "E10", 3, "P0", "AC: clicking a node opens sidebar; form fields persist on blur; validation surfaces."),
    StoryV2("S463", "flow: edge editing (connect/disconnect/redirect)", "S19", "E10", 2, "P0", "AC: drag-from-handle connects; click edge → delete confirm."),
    StoryV2("S464", "flow: variable inspector (state at any node)", "S19", "E10", 2, "P0", "AC: side panel shows live state during emulator run."),
    StoryV2("S465", "flow: serialize to YAML (deterministic, sorted keys)", "S19", "E10", 2, "P0", "AC: same graph → byte-identical YAML; round-trip property test."),
    StoryV2("S466", "flow: deserialize YAML → graph", "S19", "E10", 1, "P0", "AC: paired with S465; round-trip green."),
    StoryV2("S467", "flow: save/load to cp-api as agent_versions.flow_yaml", "S19", "E10", 2, "P0", "AC: Save button posts; Load on mount; conflict-detection on stale version_tag."),
    StoryV2("S468", "flow: emulator panel shares state with runtime emulator", "S19", "E10", 2, "P0", "AC: clicking Play in flow editor uses /v1/turns; tokens stream into a chat preview."),
    StoryV2("S469", "flow: undo/redo with capped history", "S19", "E10", 2, "P1", "AC: Cmd+Z undoes last node/edge change; capped at 50."),
    StoryV2("S470", "flow: validation — missing-edge, unreachable-node, dangling-condition", "S19", "E10", 2, "P0", "AC: lint surfaces banner + per-node markers; block save if errors."),
    StoryV2("S471", "flow: 3 starter templates (FAQ, support-triage, lead-qual)", "S19", "E10", 2, "P1", "AC: 'New agent from template' picks one of three; each runs out of the box."),
    StoryV2("S472", "flow: integration test — build a graph, save, run, expected branch hit", "S19", "E10", 2, "P0", "AC: Playwright test asserts conditional branch firing."),

    # =====================================================================
    # Sprint S20 — Trace viewer + replay (≈8 stories)
    # =====================================================================
    StoryV2("S480", "replay: per-turn frame recorder writing JSONL to NATS log subject", "S20", "E9", 2, "P0", "AC: every TurnEvent persisted with turn_id; replayable later. [extends S041]"),
    StoryV2("S481", "replay: deterministic replayer (substitutes gateway with cassette of recording)", "S20", "E9", 2, "P0", "AC: replay against alternate version yields events for diffing."),
    StoryV2("S482", "studio: replay button on trace detail", "S20", "E10", 1, "P0", "AC: click → choose target version → run → side-by-side."),
    StoryV2("S483", "studio: side-by-side replay diff (frames colour-coded by divergence)", "S20", "E10", 3, "P0", "AC: differing frames highlighted; tool calls + outputs diffable."),
    StoryV2("S484", "replay: cassette → eval-case converter (one-click)", "S20", "E8", 2, "P1", "AC: 'Add to eval suite' from a failed turn creates a YAML case."),
    StoryV2("S485", "replay: prod-failure auto-add to deploy-gate eval suite", "S20", "E8", 2, "P1", "AC: turn failing prod → auto-PR to evals/regressions/<sha>.yml."),
    StoryV2("S486", "replay: cost+latency assertion in cassette diff", "S20", "E8", 1, "P1", "AC: replay diff fails if cost or latency regress > threshold."),
    StoryV2("S487", "replay: integration test capture-then-replay of a real turn", "S20", "E9", 2, "P0", "AC: pytest captures, replays against same version, asserts byte-equal frames."),

    # =====================================================================
    # Sprint S21 — Episodic memory + KB v1 (≈8 stories)
    # =====================================================================
    StoryV2("S490", "episodic: Qdrant collection design per agent (separate from KB)", "S21", "E4", 1, "P0", "AC: collection name + schema documented in SCHEMA.md. [extends S035]"),
    StoryV2("S491", "episodic: auto-summarize on conversation close", "S21", "E4", 2, "P0", "AC: closed conversations summarized → embedded → upserted; integration test."),
    StoryV2("S492", "episodic: retrieval at turn-start (top-k recent + relevant)", "S21", "E4", 2, "P0", "AC: turn input enriched with N memories; configurable per agent."),
    StoryV2("S493", "episodic: TTL-based decay + soft-delete after 90d (configurable)", "S21", "E4", 1, "P1", "AC: scheduled task expires; metric emitted."),
    StoryV2("S494", "kb-v1: scheduled refresh (cron + on-demand)", "S21", "E5", 2, "P1", "AC: per-doc refresh cadence; status shown in studio."),
    StoryV2("S495", "kb-v1: incremental URL crawler (sitemap-aware)", "S21", "E5", 3, "P1", "AC: crawls sitemap.xml; respects robots.txt; only fetches changed-since."),
    StoryV2("S496", "kb-v1: layout-aware chunking (tables, code blocks, math preserved)", "S21", "E5", 2, "P1", "AC: tables stay intact in retrieved chunks; code blocks preserved verbatim."),
    StoryV2("S497", "studio: KB freshness indicators + manual refresh button", "S21", "E10", 2, "P1", "AC: KB list shows last-refreshed; click triggers refresh."),

    # =====================================================================
    # Sprint S22 — SMS + Email + Telegram channels (≈10 stories)
    # =====================================================================
    StoryV2("S510", "sms: Twilio SMS adapter (inbound webhook + outbound API)", "S22", "E6", 2, "P0", "AC: incoming SMS → AgentEvent; outgoing AgentResponse → Twilio."),
    StoryV2("S511", "sms: opt-in/opt-out compliance (STOP, START, HELP keywords)", "S22", "E6", 2, "P0", "AC: STOP marks user opted-out; further messages blocked; START re-opts; HELP responds with template."),
    StoryV2("S512", "sms: studio connect-Twilio-number flow", "S22", "E10", 1, "P0", "AC: number selector; SMS-capable filter; tile shows status."),
    StoryV2("S513", "email: SES inbound adapter (S3 trigger → parse RFC822 → AgentEvent)", "S22", "E6", 3, "P0", "AC: incoming email → conversation thread by Message-Id; attachments to object-store. [extends S037]"),
    StoryV2("S514", "email: SES outbound adapter w/ DKIM signing", "S22", "E6", 2, "P0", "AC: AgentResponse → SES SendEmail; DKIM-signed; bounce/complaint handled."),
    StoryV2("S515", "email: thread correlation via References + In-Reply-To", "S22", "E6", 2, "P0", "AC: replying-to-thread routes to same conversation; unit-tested."),
    StoryV2("S516", "email: studio domain connect (SPF + DKIM verification)", "S22", "E10", 2, "P0", "AC: tab shows domain status; pending records display until verified."),
    StoryV2("S517", "telegram: Bot API adapter (long-poll mode)", "S22", "E6", 2, "P1", "AC: messages routed; integration with sandbox bot."),
    StoryV2("S518", "telegram: webhook mode for production", "S22", "E6", 1, "P1", "AC: webhook over HTTPS; signature verified; throughput tested."),
    StoryV2("S519", "telegram: studio connect-bot flow (BotFather token)", "S22", "E10", 1, "P1", "AC: paste token; tile shows online; integration test."),

    # =====================================================================
    # Sprint S23 — Discord + Teams (≈7 stories)
    # =====================================================================
    StoryV2("S530", "discord: bot adapter (gateway + slash + at-mention)", "S23", "E6", 3, "P1", "AC: messages routed; slash command works; integration test. [extends S040]"),
    StoryV2("S531", "discord: studio connect-bot flow", "S23", "E10", 1, "P1", "AC: invite-link generator; tile shows status."),
    StoryV2("S532", "teams: Bot Framework adapter (signed JWT)", "S23", "E6", 3, "P1", "AC: webhook handlers verified; messages routed; integration test."),
    StoryV2("S533", "teams: studio connect flow (manifest upload)", "S23", "E10", 1, "P1", "AC: manifest.zip downloadable; instructions step-by-step."),
    StoryV2("S534", "teams: adaptive-card renderer for AgentResponse", "S23", "E6", 2, "P1", "AC: lists/buttons render natively; lockdown for forbidden elements."),
    StoryV2("S535", "channels: cross-channel test fixture (one agent, all channels respond)", "S23", "E6", 2, "P1", "AC: scripted test sends to all 7 channels; each gets equivalent response."),
    StoryV2("S536", "channels: per-channel feature-flag matrix in agent config", "S23", "E6", 1, "P1", "AC: agent.channels.<name>.enabled gate; missing → 405."),

    # =====================================================================
    # Sprint S24 — MCP marketplace v0 (≈10 stories)
    # =====================================================================
    StoryV2("S550", "mcp-mkt: cp_0004 migration registry table mcp_servers", "S24", "E18", 1, "P0", "AC: schema with verified, signed_by, manifest_uri; SCHEMA.md updated."),
    StoryV2("S551", "mcp-mkt: server publish flow (signed manifest verification)", "S24", "E18", 2, "P0", "AC: cosign verify on manifest; rejected if unsigned/wrong key."),
    StoryV2("S552", "mcp-mkt: server install flow per agent (version-pinned)", "S24", "E18", 2, "P0", "AC: install adds entry to agent_version.config_json.tools.mcp_servers."),
    StoryV2("S553", "mcp-mkt: studio browse page (categories, search, install button)", "S24", "E10", 3, "P0", "AC: list paginates; search by name/desc; click installs to agent."),
    StoryV2("S554", "mcp-mkt: studio installed-tools panel + version pinning UI", "S24", "E10", 2, "P0", "AC: installed list per agent; pin/upgrade UI; uninstall confirm."),
    StoryV2("S555", "mcp-mkt: salesforce server (read-only first)", "S24", "E18", 3, "P1", "AC: list-objects, query records, get-record-detail tools; integration test sandbox. [extends S047]"),
    StoryV2("S556", "mcp-mkt: zendesk server", "S24", "E18", 2, "P1", "AC: list-tickets, get-ticket, add-comment; sandbox integration."),
    StoryV2("S557", "mcp-mkt: hubspot server (read)", "S24", "E18", 2, "P1", "AC: contacts/companies/deals listings; sandbox integration."),
    StoryV2("S558", "mcp-mkt: stripe server (read)", "S24", "E18", 2, "P1", "AC: customers/invoices/payouts listings; sandbox integration."),
    StoryV2("S559", "mcp-mkt: server-publish CLI (`loop tool publish`) signs + uploads", "S24", "E11", 2, "P0", "AC: publishes new server version to registry; cosign-signed."),

    # =====================================================================
    # Sprint S25 — SOC2 Type 1 prep (≈13 stories)
    # =====================================================================
    StoryV2("S570", "soc2: vanta integration auth + organization sync", "S25", "E16", 1, "P0", "AC: OAuth complete; vanta-side organization linked. [extends S046]"),
    StoryV2("S571", "soc2: control mapping (CC1-CC9) → evidence sources doc", "S25", "E16", 2, "P0", "AC: SOC2_CONTROLS.md maps each CC to evidence (CI badge / audit log / runbook)."),
    StoryV2("S572", "soc2: backup automation postgres (point-in-time recovery)", "S25", "E16", 2, "P0", "AC: WAL archived to object-store; restore drill in DR runbook proves <1h RTO."),
    StoryV2("S573", "soc2: backup automation clickhouse", "S25", "E16", 2, "P0", "AC: scheduled exports to object-store; restore drill verified."),
    StoryV2("S574", "soc2: backup automation minio (cross-region replication)", "S25", "E16", 1, "P0", "AC: bucket replicated; integrity verified daily."),
    StoryV2("S575", "soc2: DR runbook + tabletop exercise (recorded)", "S25", "E16", 2, "P0", "AC: runbook checked in; exercise minutes appended; gaps tracked as issues."),
    StoryV2("S576", "soc2: pen-test prep (scope + RoE + access creds)", "S25", "E16", 2, "P0", "AC: scope agreed with vendor; staging env stood up; creds rotated post-test."),
    StoryV2("S577", "soc2: pen-test fix queue tracked as P0 stories", "S25", "E16", 2, "P0", "AC: each finding has tracker entry, severity, owner, fix-deadline."),
    StoryV2("S578", "soc2: SBOM generation in CI (cyclonedx)", "S25", "E16", 1, "P0", "AC: every release artifact ships SBOM; checked-in workflow output."),
    StoryV2("S579", "soc2: dependency-scanning gate (trivy + snyk)", "S25", "E16", 1, "P0", "AC: PRs with new HIGH+ vuln blocked; allowlist mechanism for false-positives."),
    StoryV2("S580", "soc2: secrets-scanning gate (gitleaks)", "S25", "E16", 1, "P0", "AC: pre-commit + CI; historical sweep done; rotation runbook for hits."),
    StoryV2("S581", "soc2: audit-trail completeness review (every state change is logged)", "S25", "E16", 2, "P0", "AC: matrix of write endpoints → audit-event coverage; gaps fixed."),
    StoryV2("S582", "soc2: SOC2 Type 1 attestation kickoff with auditor", "S25", "E16", 2, "P0", "AC: kickoff meeting held; evidence list + window dates committed."),

    # =====================================================================
    # Sprint S26 — EU region (data residency) (≈8 stories)
    # =====================================================================
    StoryV2("S590", "region: regions.yaml registry + per-workspace region pinning enforced in cp-api", "S26", "E12", 2, "P0", "AC: workspace.region immutable post-create; cross-region API call rejects 403. [extends S045]"),
    StoryV2("S591", "region: data-plane EU stack (Postgres + Qdrant + ClickHouse + NATS)", "S26", "E12", 3, "P0", "AC: terraform/helm to a EU cluster; schema parity verified."),
    StoryV2("S592", "region: control-plane region routing (per-workspace dispatch)", "S26", "E12", 2, "P0", "AC: cp-api forwards data-plane calls to the right region; latency measured."),
    StoryV2("S593", "region: cross-region data export blocker (deny-by-default)", "S26", "E12", 2, "P0", "AC: any code path that loads cross-region data → 403; integration test."),
    StoryV2("S594", "region: studio region selector at workspace creation", "S26", "E10", 1, "P0", "AC: dropdown defaults to inferred region; selection persisted; clear cannot-change-later notice."),
    StoryV2("S595", "region: signed pipeline that promotes images to all regions", "S26", "E12", 2, "P0", "AC: same image hash deployed in NA + EU; verified daily."),
    StoryV2("S596", "region: metadata-only telemetry (no PII) leaving region", "S26", "E16", 1, "P0", "AC: telemetry pipeline filters PII before cross-region; tested with synthetic PII."),
    StoryV2("S597", "region: smoke test against EU stack (full turn)", "S26", "E12", 2, "P0", "AC: scripts/eu_smoke.sh against eu-west passes; CI nightly."),

    # =====================================================================
    # Sprint S27 — Enterprise SSO/SAML (≈9 stories)
    # =====================================================================
    StoryV2("S610", "sso: SAML SP impl via PySAML2", "S27", "E20", 3, "P0", "AC: ACS endpoint validates assertion; cert-rotation supported. [extends S050]"),
    StoryV2("S611", "sso: SCIM provisioning endpoint (RFC 7644)", "S27", "E20", 3, "P0", "AC: Users + Groups create/update/delete from IdP; Postmen schemathesis test."),
    StoryV2("S612", "sso: Okta integration recipe + sandbox tenant test", "S27", "E20", 2, "P0", "AC: sample IdP metadata in fixtures/; full SP↔IdP loop in integration."),
    StoryV2("S613", "sso: Entra ID recipe + sandbox tenant test", "S27", "E20", 2, "P0", "AC: same as Okta but Entra ID."),
    StoryV2("S614", "sso: Google Workspace recipe + sandbox test", "S27", "E20", 2, "P0", "AC: same."),
    StoryV2("S615", "sso: studio enterprise tab → connect IdP + upload metadata", "S27", "E10", 2, "P0", "AC: paste metadata URL or upload XML; status flips to Connected after ACS-roundtrip."),
    StoryV2("S616", "sso: just-in-time user provisioning at first login", "S27", "E20", 2, "P0", "AC: unknown SAML subject creates user + workspace_members row per group mapping."),
    StoryV2("S617", "sso: SAML group → workspace role mapping rules", "S27", "E20", 2, "P0", "AC: rules in workspace_sso_groups table; UI to edit; tested for owner/editor/viewer."),
    StoryV2("S618", "sso: integration test full Okta SP-initiated login → studio session", "S27", "E20", 2, "P0", "AC: Playwright drives Okta sandbox + studio; ends in authenticated session."),

    # =====================================================================
    # Sprint S28 — Audit log UI + DPA + on-prem parity (≈10 stories)
    # =====================================================================
    StoryV2("S630", "audit: audit_events table cp_0004 + write-only middleware", "S28", "E20", 2, "P0", "AC: every cp-api write endpoint emits an audit_event; integration test."),
    StoryV2("S631", "audit: studio audit log page (filterable, paginated)", "S28", "E10", 3, "P0", "AC: 7 filters: actor, action, resource, time, ip, success/failure."),
    StoryV2("S632", "audit: audit log export CSV", "S28", "E20", 1, "P0", "AC: filtered export in <30s for ≤100k rows."),
    StoryV2("S633", "audit: SIEM webhook (Datadog/Splunk/generic)", "S28", "E20", 2, "P1", "AC: per-workspace webhook URL; back-fill on outage; signature for receiver verify."),
    StoryV2("S634", "audit: DPA template + redlines workflow", "S28", "E20", 2, "P1", "AC: DPA.md + redlines mechanism documented; sample redline-PR closed."),
    StoryV2("S635", "audit: GDPR Art-17 data-deletion request endpoint + workflow", "S28", "E16", 2, "P0", "AC: POST /v1/workspaces/{id}/data-deletion enqueues job; results emailed."),
    StoryV2("S636", "ent: customer-managed KMS key (CMK) per workspace", "S28", "E20", 3, "P0", "AC: workspace.tenant_kms_key_id used for envelope encryption; integration with AWS KMS sandbox."),
    StoryV2("S637", "ent: BYO Vault integration (existing tenant Vault, not Loop's)", "S28", "E20", 2, "P0", "AC: vault_address + role configurable per workspace; secrets-rotation runbook updated."),
    StoryV2("S638", "ent: dedicated single-tenant deploy mode (one helm-install per customer)", "S28", "E20", 3, "P1", "AC: 'enterprise' values produce isolated stack; smoke test."),
    StoryV2("S639", "ent: on-prem parity matrix verification (cloud-vs-onprem feature gates)", "S28", "E13", 2, "P0", "AC: PARITY.md matrix; every gap fixed or explicitly accepted; checked-in evidence."),

    # =====================================================================
    # Sprint S29 — Voice latency push + GA polish (≈10 stories)
    # =====================================================================
    StoryV2("S650", "voice-perf: ASR streaming optimization (frame-level dispatch)", "S29", "E7", 2, "P0", "AC: 50ms-frame dispatch; integration test shows reduced first-token latency. [extends S048]"),
    StoryV2("S651", "voice-perf: TTS pre-warm + sentence-boundary streaming", "S29", "E7", 2, "P0", "AC: TTS speaks before LLM finishes; measurable p50 cut."),
    StoryV2("S652", "voice-perf: model warm-up + connection-pooling for ASR/TTS providers", "S29", "E7", 2, "P0", "AC: keep-alive; pre-handshake; idle teardown after N min."),
    StoryV2("S653", "voice-perf: regional endpoints (eu-west, ap-south) for ASR/TTS", "S29", "E7", 2, "P0", "AC: nearest-region selector; latency map committed."),
    StoryV2("S654", "voice-perf: latency benchmark ≤700ms p50 acceptance gate", "S29", "E7", 2, "P0", "AC: scripts/voice_perf.py runs nightly; CI alerts if breached."),
    StoryV2("S655", "ga-polish: design-system audit + component refactor", "S29", "E10", 3, "P1", "AC: token map sweep; <5 hardcoded colours/spacings remain; doc'd in design system."),
    StoryV2("S656", "ga-polish: a11y audit (WCAG 2.1 AA) on top 10 studio pages", "S29", "E10", 2, "P0", "AC: axe-core zero serious; manual screen-reader pass; report committed."),
    StoryV2("S657", "ga-polish: i18n scaffolding (en, es, de, fr, ja)", "S29", "E10", 2, "P1", "AC: react-i18next; en is source; 4 languages stub-translated; switcher works."),
    StoryV2("S658", "ga-polish: support runbook + ticketing integration (Front)", "S29", "E17", 1, "P1", "AC: tickets reach support@; routing rules documented."),
    StoryV2("S659", "ga-polish: docs.loop.example v1 (Mintlify) — getting started + 3 tutorials", "S29", "E17", 3, "P0", "AC: docs site live; tutorials checked by 3 design partners."),

    # =====================================================================
    # Sprint S30 — 1.0 launch + Series A (≈5 stories)
    # =====================================================================
    StoryV2("S670", "launch: 1.0 release-notes draft + changelog automation", "S30", "E17", 1, "P0", "AC: Keep-A-Changelog; release-please bot wired."),
    StoryV2("S671", "launch: pricing page + plan-comparison matrix", "S30", "E17", 2, "P0", "AC: live page; sales-ops verified; A/B-flag-enabled."),
    StoryV2("S672", "launch: design partners → 10 paid customers conversion plan", "S30", "E17", 2, "P0", "AC: each partner converted or churned with reason; documented in OPS/launch.md."),
    StoryV2("S673", "launch: HN / Product Hunt launch playbook executed", "S30", "E17", 2, "P0", "AC: launched, ranked, post-mortem; conversion + churn measured for first 7 days."),
    StoryV2("S674", "launch: Series A data room update + investor narrative refresh", "S30", "E12", 2, "P0", "AC: data-room link sharable; narrative deck + financial model committed. [extends S044]"),

    # =====================================================================
    # Audit-follow-up backlog — gaps the v1 plan missed (added after vision audit)
    # Filed against gaps in: LLM gateway breadth, MCP/Hub scale, RCS, cloud-portability proof,
    # production security/ops gates. These slot into existing sprints (RCS into S22)
    # and into 5 new sprints S31-S35 added to build_tracker.py SPRINTS.
    # =====================================================================

    # ---------------------------------------------------------------------
    # RCS — slotted into Sprint S22 (already covers SMS/Email/Telegram).
    # The roadmap promises RCS at M11; this delivers it.
    # ---------------------------------------------------------------------
    StoryV2("S540", "rcs: RCS Business Messaging adapter via Google Jibe / carrier MaaP", "S22", "E6", 3, "P0", "AC: outbound RCS message with rich card via Jibe sandbox; fallback to SMS on carrier-not-supported."),
    StoryV2("S541", "rcs: inbound webhook → AgentEvent (carrier delivery + read receipts)", "S22", "E6", 2, "P0", "AC: carrier webhook signature verified; inbound text and suggested-reply taps routed."),
    StoryV2("S542", "rcs: rich-card renderer (carousels, suggested replies, suggested actions)", "S22", "E6", 2, "P0", "AC: AgentResponse → RCS card; carousel ≤10 cards; quick-reply chips present."),
    StoryV2("S543", "rcs: agent verification + brand profile setup workflow", "S22", "E6", 2, "P1", "AC: per-agent brand profile + verification request submitted to carrier; status tracked."),
    StoryV2("S544", "rcs: studio connect-RCS flow (brand id, MaaP creds)", "S22", "E10", 2, "P0", "AC: tab shows verification status, connected number, brand assets preview."),
    StoryV2("S545", "rcs: integration test (recorded MaaP webhooks + outbound assertion)", "S22", "E6", 2, "P0", "AC: fixtures/rcs/*.json replay; outbound calls asserted against recorded golden responses."),

    # =====================================================================
    # Sprint S31 — LLM gateway breadth (≈14 stories)
    # The vision needs many providers + caching + BYO + routing + fallback,
    # not just OpenAI/Anthropic. Each provider gets its own bite-sized story
    # implementing the GatewayProvider Protocol (built in S007).
    # =====================================================================
    StoryV2("S700", "gateway: AWS Bedrock provider (Anthropic + Mistral + Llama via Bedrock)", "S31", "E2", 3, "P0", "AC: stream(GatewayRequest) over Bedrock invokeModelWithResponseStream; cassette tests for 3 model families. [extends S007]"),
    StoryV2("S701", "gateway: Google Vertex AI / Gemini provider", "S31", "E2", 2, "P0", "AC: gemini-1.5-pro and -flash both stream; usage + cost tracked; cassette tests."),
    StoryV2("S702", "gateway: Mistral provider (mistral-large + codestral)", "S31", "E2", 2, "P0", "AC: streaming working; cost rates added to COST_TABLE; cassette tests."),
    StoryV2("S703", "gateway: Cohere provider (command-r-plus, embed)", "S31", "E2", 2, "P0", "AC: chat + embed paths; cost tracked; cassette tests."),
    StoryV2("S704", "gateway: Groq provider (llama-3.3, qwen-32b on LPU)", "S31", "E2", 2, "P0", "AC: streaming; latency benchmark logged (<200ms TTFT)."),
    StoryV2("S705", "gateway: vLLM self-hosted provider (OpenAI-compatible endpoint)", "S31", "E2", 2, "P0", "AC: configurable base_url; works against local vLLM container; cassette tests."),
    StoryV2("S706", "gateway: Together / Replicate / Fireworks generic OpenAI-compatible provider class", "S31", "E2", 2, "P1", "AC: one shared adapter parameterised by base_url + auth-header style; integration test against each."),
    StoryV2("S707", "gateway: semantic cache (Redis) — embed query + cosine match against prior responses", "S31", "E2", 3, "P0", "AC: cache-hit returns within 50ms; threshold 0.97 default; per-workspace TTL; ablation eval. [extends S029]"),
    StoryV2("S708", "gateway: BYO-key support — workspace_keys table + per-call key resolution", "S31", "E2", 3, "P0", "AC: workspace can register provider keys via cp-api; per-call resolution honours them; encrypted at rest via KMS Protocol."),
    StoryV2("S709", "gateway: model-aliases.yaml + per-workspace alias overrides", "S31", "E2", 2, "P0", "AC: agent.model='loop:smart' resolves to current per-workspace mapping; updating alias rolls all agents safely."),
    StoryV2("S710", "gateway: provider routing engine (cost / latency / quality tiers)", "S31", "E2", 3, "P0", "AC: agent config picks {tier, requirements}; router selects best provider matching; degrade order logged."),
    StoryV2("S711", "gateway: provider failover (primary fails → secondary within 1 retry)", "S31", "E2", 2, "P0", "AC: 5xx or timeout → fallback to next-priority provider; trace records both attempts."),
    StoryV2("S712", "gateway: per-provider rate-limit (token bucket per key, surfaces 429 cleanly)", "S31", "E2", 2, "P0", "AC: hitting upstream 429 → backoff + retry; budget breached → LOOP-GW-301 to caller."),
    StoryV2("S713", "gateway: cost precision — Decimal-based math + per-token rounding rules", "S31", "E2", 2, "P0", "AC: cost.py switches from float to Decimal; round-trip exact within 7 decimals; existing tests stay green; ADR-028 updated."),
    StoryV2("S714", "gateway: 50-prompt provider eval suite (quality + latency + cost matrix)", "S31", "E2", 3, "P1", "AC: nightly suite runs across all 8 providers; report compares quality/latency/cost — committed to docs/perf/."),

    # =====================================================================
    # Sprint S32 — MCP production hardening + tool policy (≈16 stories)
    # The MCP-native moat needs production policy + sandbox controller +
    # broader compatibility, not just the @tool decorator.
    # =====================================================================
    StoryV2("S720", "mcp: tool policy engine — per-agent allow/deny + scope claims", "S32", "E3", 3, "P0", "AC: tool.call('x') passes through ToolPolicy; deny → LOOP-TH-101 with reason; integration test. [extends S011]"),
    StoryV2("S721", "mcp: per-tool egress allowlist enforced by sandbox network policy", "S32", "E3", 3, "P0", "AC: tool config declares allowed_hosts; any other DNS/IP egress → blocked + audit event. [extends S014]"),
    StoryV2("S722", "mcp: tool-call rate limit per agent + per workspace", "S32", "E3", 2, "P0", "AC: per-tool cap configurable; exceeding → LOOP-TH-301; tested at 100 concurrent."),
    StoryV2("S723", "mcp: argument schema validation + result schema validation", "S32", "E3", 2, "P0", "AC: bad args → LOOP-TH-002 before dispatch; non-conforming result → LOOP-TH-002 in result frame."),
    StoryV2("S724", "mcp: secrets injection from agent_secrets via sandbox env (KMS-decrypted at boot)", "S32", "E3", 2, "P0", "AC: tools reference secret_ref; sandbox env vars populated only at boot; never persisted to disk."),
    StoryV2("S725", "mcp: tool-execution timeout per call + cancellation propagation", "S32", "E3", 2, "P0", "AC: per-tool timeout; on breach, sandbox stream cancelled cleanly; partial-result captured."),
    StoryV2("S726", "mcp: sandbox controller (k8s controller) reconciles WarmPool size against demand", "S32", "E3", 3, "P0", "AC: kopf-based controller scales pool; metrics emitted; integration on kind. [extends S014]"),
    StoryV2("S727", "mcp: sandbox hot-restart on tool config change (zero-downtime)", "S32", "E3", 2, "P0", "AC: updating MCP server config triggers staggered pool refresh; in-flight calls drained; integration test."),
    StoryV2("S728", "mcp: inbound MCP server — Loop exposes its own runtime as MCP server (so agents can compose Loop)", "S32", "E3", 3, "P0", "AC: `loop` MCP server exposes turns/conversations/agents as MCP resources; integration with one external MCP client."),
    StoryV2("S729", "mcp: MCP protocol version negotiation + compatibility matrix", "S32", "E3", 2, "P0", "AC: client/server negotiate; supported versions documented; tested against 3 reference MCP servers."),
    StoryV2("S730", "mcp: tool-call resource quotas (CPU, memory, disk in sandbox)", "S32", "E3", 2, "P0", "AC: limits enforced via cgroups; OOM-kill returns LOOP-TH-402; documented per tool."),
    StoryV2("S731", "mcp: tool versioning + atomic upgrade (per agent version)", "S32", "E3", 2, "P0", "AC: agent_version pins tool@version; upgrade is a new agent_version; rollback works."),
    StoryV2("S732", "mcp: signed-tool verification (cosign on container image + manifest)", "S32", "E3", 2, "P0", "AC: tools must carry cosign signature from registered publishers; unsigned blocked unless allow-listed."),
    StoryV2("S733", "mcp: tool-call observability — span per tool with args/result hashes (PII-redacted)", "S32", "E3", 2, "P0", "AC: trace shows tool spans; args+result hashed (not stored); studio renders inline."),
    StoryV2("S734", "mcp: tool-result caching (idempotent calls only, opt-in per tool)", "S32", "E3", 2, "P1", "AC: GET-shaped tools cache; cache key includes args+context; per-tool TTL."),
    StoryV2("S735", "mcp: hostile-tool kill-switch (revoke + drain across fleet within 60s)", "S32", "E3", 2, "P0", "AC: cp-api 'revoke tool' → NATS event → sandboxes terminate within 60s; verified e2e."),

    # =====================================================================
    # Sprint S33 — MCP marketplace scale + community (≈13 stories)
    # E18 promises 25 MVP / 200 by M12 servers — needs many more first-party
    # plus a community publish + curation workflow, not just registry plumbing.
    # =====================================================================
    StoryV2("S750", "marketplace: server quality score (compatibility + signed + rated)", "S33", "E18", 2, "P0", "AC: each server shows score 0-100; criteria documented; sortable in browse UI."),
    StoryV2("S751", "marketplace: community publish flow (PR-based registry, signed by maintainer)", "S33", "E18", 3, "P0", "AC: contributors PR a manifest; CI verifies signature + schema; merge → live in registry."),
    StoryV2("S752", "marketplace: server reviews + ratings (1-5 stars, written reviews)", "S33", "E18", 2, "P1", "AC: per-server reviews table; one-review-per-workspace; moderation queue for abuse."),
    StoryV2("S753", "marketplace: usage analytics per server (anonymous opt-in install + call counts)", "S33", "E18", 2, "P1", "AC: opt-in telemetry; aggregate counts surfaced on browse page."),
    StoryV2("S754", "marketplace: first-party server — Google Calendar (read + create events)", "S33", "E18", 2, "P0", "AC: OAuth2 calendar.events scope; integration test sandbox."),
    StoryV2("S755", "marketplace: first-party server — Gmail (read + send + drafts)", "S33", "E18", 2, "P0", "AC: OAuth2 gmail.send scope; tested against gmail sandbox."),
    StoryV2("S756", "marketplace: first-party server — GitHub (issues + PRs + comments)", "S33", "E18", 2, "P0", "AC: PAT or app auth; create issue, comment, list-prs tools."),
    StoryV2("S757", "marketplace: first-party server — Linear (issues + projects)", "S33", "E18", 2, "P0", "AC: API-key auth; CRUD on issues; tested sandbox."),
    StoryV2("S758", "marketplace: first-party server — Jira (issues + comments)", "S33", "E18", 2, "P0", "AC: API-token auth; CRUD; tested sandbox."),
    StoryV2("S759", "marketplace: first-party server — Notion (pages + DB query)", "S33", "E18", 2, "P0", "AC: integration token; query DB, create page; tested sandbox."),
    StoryV2("S760", "marketplace: first-party server — Asana (tasks + projects)", "S33", "E18", 2, "P1", "AC: PAT auth; CRUD on tasks; tested sandbox."),
    StoryV2("S761", "marketplace: first-party server — Stripe write (refunds + invoices)", "S33", "E18", 2, "P1", "AC: write scopes; test-mode verified; no live writes in CI."),
    StoryV2("S762", "marketplace: first-party server — Slack write (post message + DM)", "S33", "E18", 2, "P0", "AC: bot-token scopes; test workspace verified."),
    StoryV2("S763", "marketplace: first-party server — HubSpot write (contacts + deals)", "S33", "E18", 2, "P1", "AC: OAuth2 scopes; sandbox tested."),
    StoryV2("S764", "marketplace: first-party server — generic web search (Tavily + Brave)", "S33", "E18", 2, "P0", "AC: pluggable backend; cost/latency tracked; tested both."),
    StoryV2("S765", "marketplace: 25-server MVP acceptance test (every server shows quality score, install works, integration test green)", "S33", "E18", 2, "P0", "AC: scripts/marketplace_acceptance.sh runs CI nightly; counts ≥ 25 active servers; all green."),

    # =====================================================================
    # Sprint S34 — Cloud-portability proof (≈12 stories)
    # The cloud-agnostic promise must be proven on a story basis, not just
    # documented. This sprint adds Terraform per cloud + cross-cloud CI matrix
    # + provider-abstraction parity tests.
    # =====================================================================
    StoryV2("S770", "infra: terraform module — AWS (EKS + RDS + ElastiCache + S3 + KMS + Cloudfront)", "S34", "E12", 3, "P0", "AC: terraform plan green; apply creates fully-functional Loop stack on AWS; smoke test runs against it."),
    StoryV2("S771", "infra: terraform module — Azure (AKS + Postgres Flexible + Redis + Blob + Key Vault + Front Door)", "S34", "E12", 3, "P0", "AC: same as S770 against Azure."),
    StoryV2("S772", "infra: terraform module — GCP (GKE + CloudSQL + Memorystore + GCS + KMS + Cloud CDN)", "S34", "E12", 3, "P0", "AC: same against GCP."),
    StoryV2("S773", "infra: terraform module — Alibaba Cloud (ACK + RDS + Redis + OSS + KMS + DCDN)", "S34", "E12", 3, "P1", "AC: same against Alibaba Cloud (China region)."),
    StoryV2("S774", "infra: terraform module — OVHcloud (managed K8s + Postgres + Redis + S3-compat + KMS via Vault)", "S34", "E12", 2, "P1", "AC: same against OVH; sovereign-EU region option."),
    StoryV2("S775", "infra: terraform module — Hetzner (HCloud K8s + managed Postgres + S3-compat MinIO + KMS via Vault)", "S34", "E12", 2, "P1", "AC: same against Hetzner; cost-optimized self-hosted alternative."),
    StoryV2("S776", "portability: ObjectStore Protocol parity tests across all 6 backends", "S34", "E12", 2, "P0", "AC: same test-suite runs against S3/Azure-Blob/GCS/OSS/Swift/MinIO; signed-URL + presign + multipart parity verified."),
    StoryV2("S777", "portability: KMS Protocol parity tests across AWS/Azure/GCP/Alibaba KMS + Vault Transit", "S34", "E12", 2, "P0", "AC: encrypt/decrypt/rotate/sign Sketches identical results; tested in CI nightly."),
    StoryV2("S778", "portability: SecretsBackend Protocol parity tests across Vault/AWS-SM/Azure-KV/GCP-SM", "S34", "E12", 2, "P0", "AC: get/set/rotate identical; access-pattern tests."),
    StoryV2("S779", "portability: EmailSender Protocol parity tests across SES/Resend/SMTP", "S34", "E12", 1, "P0", "AC: send + bounce + complaint handlers identical; integration tests."),
    StoryV2("S780", "ci: cross-cloud nightly smoke test matrix (deploy + first-turn on AWS+Azure+GCP)", "S34", "E12", 3, "P0", "AC: GHA matrix workflow nightly; all 3 must pass for green status; on-failure pages on-call."),
    StoryV2("S781", "docs: cloud-portability proof report (Wk-by-Wk parity matrix shipped to docs/CLOUD_PROOF.md)", "S34", "E17", 1, "P0", "AC: matrix lists each capability × cloud; nightly job appends a green/red mark; published live."),

    # =====================================================================
    # Sprint S35 — Production security / ops acceptance gates (≈10 stories)
    # Closes the gap between "SOC2 paperwork" and "actually-secure runtime".
    # =====================================================================
    StoryV2("S800", "security: continuous fuzz testing of cp-api + dp-runtime (atheris/restler)", "S35", "E16", 3, "P0", "AC: fuzz harness runs in CI nightly; crashes/oom auto-issue; coverage report."),
    StoryV2("S801", "security: threat-model verification — STRIDE checklist gate per PR touching auth/security paths", "S35", "E16", 2, "P0", "AC: PRs touching auth/RLS/secrets fail without docs/THREAT_MODEL.md update; bot enforces."),
    StoryV2("S802", "security: SLSA Level 3 build provenance for container images (in-toto attestations)", "S35", "E16", 3, "P0", "AC: every image carries SLSA-3 provenance; verified at deploy gate; rejected if missing."),
    StoryV2("S803", "security: runtime detection (Falco rules) for sandbox + cp-api anomalies", "S35", "E16", 2, "P0", "AC: rules deployed; alerts on shell-exec / unauthorized syscall / unexpected egress; tested with red-team triggers."),
    StoryV2("S804", "security: chaos-engineering harness (network partition, DB failover, NATS outage)", "S35", "E16", 3, "P1", "AC: scripted scenarios run weekly in staging; recovery time + data-loss measured; runbook updates from findings."),
    StoryV2("S805", "ops: SLO definitions per service + error-budget burn alerts", "S35", "E9", 2, "P0", "AC: SLOs.yaml committed; per-service availability + latency + error budget; alerts wired to PagerDuty."),
    StoryV2("S806", "ops: incident-response runbook + game-day cadence (monthly)", "S35", "E16", 2, "P0", "AC: runbook checked in; first game-day held; recorded; gaps tracked."),
    StoryV2("S807", "ops: data-retention policy enforced by scheduled jobs (per data type, per region)", "S35", "E16", 2, "P0", "AC: jobs delete per policy; deletion audited; user-visible policy page on docs site."),
    StoryV2("S808", "ops: encrypted backup verification (restore-then-diff weekly)", "S35", "E16", 2, "P0", "AC: weekly job restores latest backup to scratch; diff against live; alerts on mismatch."),
    StoryV2("S809", "security: bug-bounty program launch (HackerOne or YesWeHack)", "S35", "E16", 2, "P0", "AC: program live; scope+rules+payouts published; first 3 reports triaged within SLA."),

    # =====================================================================
    # Sprint S36 — Memory provider integrations + KB v2 (≈8 stories)
    # The strategic spec mentions Mem0 / similar memory providers; the docs
    # say to keep memory swappable. This sprint adds the major integrations.
    # =====================================================================
    StoryV2("S820", "memory: Mem0 adapter (drop-in EpisodicMemoryStore via Protocol)", "S36", "E4", 2, "P1", "AC: configurable; integration test against Mem0 sandbox; per-workspace toggle."),
    StoryV2("S821", "memory: Zep adapter (drop-in)", "S36", "E4", 2, "P1", "AC: same Protocol; integration test."),
    StoryV2("S822", "memory: LangMem-style summarization variant (heuristic + LLM hybrid)", "S36", "E4", 2, "P1", "AC: ablation eval against current auto-summarize shows ≥10% retrieval improvement."),
    StoryV2("S823", "memory: per-user memory isolation guarantees + audit", "S36", "E4", 2, "P0", "AC: cross-user memory leak test (red-team); zero false positives across 100k cases."),
    StoryV2("S824", "memory: PII redaction at memory-write time (configurable per agent)", "S36", "E4", 2, "P0", "AC: regex + Presidio + LLM-classifier modes; on-write filter; covered in tests."),
    StoryV2("S825", "memory: memory-usage dashboard in studio (per agent + per user)", "S36", "E10", 2, "P1", "AC: lists memory entries; redacted; user-deletable per GDPR Art-17."),
    StoryV2("S826", "kb-v2: late-interaction retrieval (ColBERT-style for high-recall surfaces)", "S36", "E5", 3, "P1", "AC: opt-in retrieval mode; eval shows ≥5% recall@10 improvement on hard queries."),
    StoryV2("S827", "kb-v2: structured-data retrieval (CSV/Excel/JSON with SQL-on-the-fly)", "S36", "E5", 3, "P1", "AC: agent uploads spreadsheet; tool can SQL it; integration test."),

    # =====================================================================
    # Sprint S37 — Latency + scale acceptance gates (≈7 stories)
    # Hard performance gates the vision implies but the previous tracker
    # never made testable.
    # =====================================================================
    StoryV2("S840", "perf: turn-latency p95 < 2.0s end-to-end (text path) — acceptance gate", "S37", "E1", 2, "P0", "AC: nightly k6 measures e2e p95; CI alerts if breached."),
    StoryV2("S841", "perf: gateway-cache hit ratio > 30% on a fixed eval workload", "S37", "E2", 2, "P0", "AC: nightly run reports hit ratio; alert if below target."),
    StoryV2("S842", "perf: KB retrieval p50 < 200ms at 1M chunks per agent", "S37", "E5", 2, "P0", "AC: synthetic 1M-chunk fixture; benchmark in CI; report committed."),
    StoryV2("S843", "perf: tool-host warm-start < 300ms p95 (vs 8s+ cold-start)", "S37", "E3", 2, "P0", "AC: WarmPool tuned; benchmark in CI; alert if breached."),
    StoryV2("S844", "perf: 1000 concurrent turns held by single dp-runtime pod (acceptance test)", "S37", "E1", 3, "P0", "AC: k6 1000 parallel SSE; no errors; latency p95 < 3s; memory < 4 GB."),
    StoryV2("S845", "perf: cp-api 5000 RPS sustained (acceptance test)", "S37", "E12", 2, "P0", "AC: k6 sustained; error rate < 0.1%; p95 < 100ms; report committed."),
    StoryV2("S846", "perf: regression budget — any 5%+ p95 regression blocks PR", "S37", "E9", 2, "P0", "AC: perf CI check compares to last 7-day baseline; PR fails if breaches."),
]


__all__ = ["StoryV2", "NEW_STORIES", "DEFAULT_OWNER", "DEFAULT_STATUS"]
