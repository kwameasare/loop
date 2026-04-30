# Design Partners Programme

> Sprint 0, Epic 17 — first 3 design partners onboarded, weekly office hour.

## Goals

The Design Partners Programme exists to keep Loop honest while the
platform is still pre-GA. Each partner runs a real workload on the
runtime and gets:

* A direct Slack channel (private, partner-only) for triage.
* Pre-release access to staged builds (channels: `voice/echo`,
  `inbox`, `studio/cost`, `studio/inbox`).
* A standing weekly office hour with the founding team.
* Influence over the next-sprint backlog: each partner has the right
  to nominate one P1 story per fortnight (subject to the standard
  capacity caps).

In return we ask partners to:

* Run at least one production-grade conversation surface on Loop.
* File at least one structured feedback ticket per fortnight.
* Sit through the office hour, even when there's nothing burning.

## Roster

| Slot | Partner | Domain | Surface | Status | Onboarded | DRI |
| ---- | ------- | ------ | ------- | ------ | --------- | --- |
| P1   | _TBD_   | _TBD_  | _TBD_   | Intake | _pending_ | CEO |
| P2   | _TBD_   | _TBD_  | _TBD_   | Intake | _pending_ | CEO |
| P3   | _TBD_   | _TBD_  | _TBD_   | Intake | _pending_ | CEO |

> Slots are filled in order. Slot fills are committed in PRs that
> update this table and add a per-partner runbook stub under
> [`loop_implementation/engineering/RUNBOOKS.md`](../engineering/RUNBOOKS.md).

## Intake checklist (per partner)

Before a slot flips from **Intake** to **Live**, the DRI must:

1. **Workspace + agent** — provision a workspace, register the
   first agent version (`deploy.create`) and confirm `READY`.
2. **Quotas + caps** — set workspace caps under
   [hard caps + graceful degrade](../engineering/RUNBOOKS.md) so a
   pilot can never burn the shared eval budget.
3. **Eval baseline** — capture a 100-case eval baseline using
   [eval-harness](../../scaffolding/packages/eval-harness/) and
   store the pass-rate via `BaselineRegistry.record`.
4. **Inbox + HITL** — confirm the operator inbox is wired
   (`InboxAPI.escalate` round-trip) and at least one operator on
   the partner's side has tested take-over from the Studio.
5. **Cost dashboard** — verify the partner's workspace shows up in
   the Studio cost dashboard with a non-zero usage rollup after a
   smoke conversation.
6. **Office-hour invite** — add the partner DRIs to the standing
   weekly invite (see below).
7. **Feedback intake** — confirm the partner has access to the
   feedback intake (GitHub project board column
   `design-partners/<slot>`).

## Weekly office hour

* **Cadence**: every Friday, 16:00 UTC, 45 minutes.
* **Owner**: CEO chairs; Eng #1 takes notes.
* **Standing agenda**:
  1. Status round-robin (≤ 3 minutes per partner).
  2. P0/P1 incidents from the past week (RUNBOOKS references).
  3. Backlog nominations + sprint-N+1 priorities.
  4. Open Q&A.
* **Notes**: archived under
  `loop_implementation/operations/office-hours/<YYYY-MM-DD>.md`
  (created on the day; previous week's notes are linked from the
  next week's heading).
* **Cancellation**: only the CEO may cancel; missed weeks roll up
  into the next session and a written status replaces the meeting.

## Feedback intake

Partners file structured feedback as GitHub issues with the
`design-partner` label and one of:

* `bug/p0`, `bug/p1`, `bug/p2` — defects, severity by partner blast
  radius.
* `feedback/dx` — developer-experience polish.
* `feedback/runtime` — runtime / agent behaviour observations.
* `feedback/ux` — Studio surfaces.
* `nomination` — backlog nominations (see Goals).

Each issue gets triaged inside the next office hour and either
closed, scheduled into the next sprint, or escalated to a P0
incident under [`triage-incident`](../skills/ops/triage-incident.md).

## Promotion gate

A slot is considered **Onboarded** (and counts toward the S034
target) when:

* All seven intake checklist items are green.
* The partner has run a non-trivial conversation through the
  runtime (≥ 50 turns or ≥ 10 voice minutes).
* The partner has attended at least one office hour.

When all three slots reach **Onboarded**, S034 is delivered. The
weekly office-hour cadence then continues indefinitely as part of
sustained operations.
