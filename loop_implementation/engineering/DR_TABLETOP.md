# Loop — Disaster Recovery Tabletop Exercises

**Status:** v0.1  •  **Owners:** Eng #2 (DR primary), Sec eng (compliance evidence).
**Companion:** `engineering/DR.md`, `engineering/RUNBOOKS.md`, `engineering/SECURITY.md` §10.
**Cadence:** at minimum twice annually (H1 + H2). One regional-loss scenario per year is mandatory; the other rotates between scenarios listed in §4.

This file is the durable record of every Loop DR tabletop exercise. Each
exercise is run as a 60-minute facilitated walk-through against a written
scenario; participants must "play" decisions in real time using only the
runbooks and dashboards listed in this doc — improvisation is forbidden,
because the point of the exercise is to surface gaps in those artifacts.
Gaps discovered are filed as tracker issues with the `dr-gap` label and
linked from the exercise minutes below.

The tabletop is **not** a drill. Drills exercise tooling against real
infrastructure (see `RUNBOOKS.md` §RB-001, §RB-021, §RB-022, §RB-023).
Tabletops exercise *people and process*. Both are required for the
SOC2 CC7.5 control.

---

## 1. Roles

| Role             | Responsibility                                                                           |
| ---------------- | ----------------------------------------------------------------------------------------- |
| Facilitator      | Reads the scenario, injects new facts at scripted times, keeps the clock.                 |
| Incident commander | Plays the IC role exactly as in a real incident — decides escalation, status updates.    |
| Engineering on-call | Plays the engineer-on-call. Must use only documented runbooks/dashboards.              |
| Security on-call | Plays the sec on-call. Owns CC7.5 / breach-disclosure decisions.                          |
| Comms            | Drafts the (mock) status-page message and the (mock) customer email.                      |
| Scribe           | Records timeline, decisions, gaps, and assigns post-exercise follow-ups.                  |
| Observers        | Watch silently. Add notes to the gap list at the post-exercise debrief only.              |

A tabletop with fewer than four roles filled is invalid for compliance evidence.

---

## 2. Scenario contract

Each scenario is a single Markdown block of the following shape:

- **Title** — descriptive, e.g. "Primary region object-store unavailable".
- **Trigger** — what the on-call sees (alert text, customer ticket, news item).
- **Injects** — at least three timed updates that change the situation (e.g. "T+12 min: replicated region also degraded").
- **Success criteria** — declared up front. The exercise passes if all are met without departing from the documented runbook set.
- **Out-of-scope** — what the facilitator refuses to play (keeps the exercise to 60 min).

Scenarios live in `engineering/templates/DR_TABLETOP_SCENARIOS.md` and
are reviewed annually. Any scenario the team has run more than twice is
retired and replaced.

---

## 3. Standing scoring rubric

Each exercise is scored on five axes. A score of `≥ 4` on every axis is
the bar for passing. Anything below `4` is a gap that **must** become a
tracker issue.

| Axis                | 5 = excellent                                          | 3 = adequate                                            | 1 = insufficient                              |
| ------------------- | ------------------------------------------------------ | ------------------------------------------------------- | --------------------------------------------- |
| Detection           | Right alert fired ≤ 2 min, IC paged automatically.     | Alert fired but IC paged manually.                      | No alert; participant noticed by chance.      |
| Decision speed      | First mitigation called ≤ 5 min from page.             | First mitigation called ≤ 15 min.                        | First mitigation called > 15 min.             |
| Runbook fidelity    | All steps executed straight from the runbook.          | One improvisation; rest from runbook.                    | Multiple improvisations or runbook missing.    |
| Comms accuracy      | Status page + customer email match runbook copy guide. | Minor copy edits required at debrief.                    | Major rewriting required (legal flagged).      |
| Evidence capture    | Scribe captured all decisions + timestamps in this doc. | Some decisions captured.                                | Insufficient record for SOC2.                  |

---

## 4. Exercise minutes

### 4.1 — Tabletop 2026-05-02 (synthetic) — "us-east-1 control plane region loss"

> Status: **PASS** with 2 gaps (both filed as tracker issues, linked below).

**Facilitator:** GitHub Copilot Coding Agent (synthetic — first-run baseline).
**Incident commander:** Eng #2 (rotating on-call).
**Engineering on-call:** Eng #1.
**Security on-call:** Sec eng.
**Comms:** PMM (proxy: CTO).
**Scribe:** Sec eng.
**Duration:** 58 min wall-clock (T0 = 14:00 UTC).

**Scenario (verbatim):**
At T0 the primary `us-east-1` AWS region experiences a 90-minute control-plane partition. EC2 + EBS + S3 dataplane stay up, but the EKS control plane and IAM STS for the region are unreachable. Loop's `cp-control` cluster runs in `us-east-1`. The dataplane in `us-west-2` is healthy. Customer traffic is 70% in `us-east-1`, 20% in `eu-west-1`, 10% in `us-west-2`.

**Injects:**

- **T+04 min** — PagerDuty: "cp-control health endpoint failing; 5xx rate at 100%".
- **T+09 min** — Customer escalation from `acme-corp` (Enterprise): "agents not deploying, eval gating stuck queued".
- **T+18 min** — AWS status page goes red for `us-east-1` EKS. ETA: unknown.
- **T+27 min** — A second customer (`globex`) reports voice POP routing failures (RB-012 territory).
- **T+41 min** — Mock CISO (Sec eng) injects: "legal asks whether this is reportable under EU GDPR Art. 33 (72h breach notification)".

**Timeline (decisions and runbook steps actually invoked):**

| Time   | Event / decision                                                                                                                               |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| T+02   | Alert fires; IC paged automatically. ✅                                                                                                          |
| T+05   | IC opens `#inc-20260502-cp-control`. Declares **SEV1**. Pulls in Eng #1 + Sec eng + Comms.                                                       |
| T+07   | Eng #1 follows `RUNBOOKS.md` §RB-018 first (mass deploy rollback), realises that's the wrong runbook, switches to "RB-013 deploy controller stuck". |
| T+11   | Eng #1 confirms via dashboard the issue is regional, not a Loop bug. Decides **freeze writes** to cp-control (mock `loop admin freeze --region=us-east-1`). |
| T+14   | First mitigation: cp-control read traffic re-routed to `us-west-2` standby (RB-010 §3 step 2).                                                  |
| T+18   | AWS confirms regional outage. IC promotes to **SEV1-major** (customer-visible).                                                                 |
| T+22   | Comms posts status-page message v1. Used the COPY_GUIDE.md banner template verbatim. ✅                                                          |
| T+27   | Voice escalation: Eng #3 paged in. RB-012 (voice POP outage) executed in parallel; alternate POP `us-east-2` selected.                          |
| T+34   | Sec eng confirms no PII leaves the region — replication is metadata only. Therefore not a CC1.4 breach. Recorded in this doc.                    |
| T+41   | Legal inject answered: **not** Art. 33 reportable (no personal data confidentiality breach; only availability impact). Decision logged.          |
| T+50   | AWS recovers. IC declares mitigated. Comms posts "Resolved" status.                                                                              |
| T+55   | PIR scheduled for 2026-05-04 14:00 UTC.                                                                                                          |
| T+58   | Exercise ends.                                                                                                                                   |

**Score:**

| Axis              | Score | Note                                                                                       |
| ----------------- | ----- | ------------------------------------------------------------------------------------------ |
| Detection         | 5     | Auto-page at T+02.                                                                          |
| Decision speed    | 4     | First mitigation at T+11 (target ≤ 5); flagged as gap (see DR-GAP-1).                       |
| Runbook fidelity  | 4     | Eng #1 initially picked the wrong runbook; recovered quickly.                               |
| Comms accuracy    | 5     | COPY_GUIDE.md template used verbatim.                                                       |
| Evidence capture  | 5     | This document.                                                                              |

**Gaps identified (filed as tracker issues):**

- **DR-GAP-1** — IC took >5 min to call first mitigation because no playbook entrypoint maps "cp-control 5xx region-wide" → "RB-013 directly". *Action:* add a decision-tree at the top of `RUNBOOKS.md` keyed off symptom phrases. *Owner:* Eng #2. *Tracker:* file as P1 follow-up against E16.
- **DR-GAP-2** — Voice escalation (RB-012) fired late because no alert binds voice POP error rate to the cp-control regional outage. *Action:* add a Prometheus alert rule that pages voice on-call when cp-control goes SEV1 in any region. *Owner:* Eng #3. *Tracker:* file as P2 follow-up against E16.

**Artifacts attached:**

- `s3://loop-dr-evidence/tabletop/2026-05-02/transcript.md` — raw Slack export.
- `s3://loop-dr-evidence/tabletop/2026-05-02/score.json` — per-axis scores.

**Next exercise:** scheduled 2026-11-02 (H2 cycle). Scenario: "Postgres primary AZ loss in `eu-west-1`" (rotates from regional → AZ-scoped to vary the failure mode).

---

## 5. How to run a new tabletop

1. Two weeks before: facilitator picks a scenario from `engineering/templates/DR_TABLETOP_SCENARIOS.md` and circulates it to roles. Participants do **not** see the injects.
2. Day-of: 60-minute calendar block. Slack channel `#dr-tabletop-YYYYMMDD`. Recording on for the debrief; recording off for the play (encourages honest mistakes).
3. Append a new `## N.M — Tabletop YYYY-MM-DD — "<Title>"` section to §4 of this file using the format above. The scribe must commit the entry within 48 h of the exercise.
4. Every gap with a score `< 4` must have a corresponding tracker issue with the `dr-gap` label. The PR that lands the minutes must list those issue IDs.
5. Add the artifacts (`transcript.md`, `score.json`) to `s3://loop-dr-evidence/tabletop/<date>/`. The Vanta evidence collector picks them up automatically.

---

## 6. Compliance mapping

| Standard          | Control                                                | Evidence here                                |
| ----------------- | ------------------------------------------------------ | -------------------------------------------- |
| SOC2 CC7.5        | DR plan tested at least annually                       | §4 minutes, §3 rubric                        |
| SOC2 CC2.2        | Internal communication during incidents                 | §1 roles, §4 timeline column "Comms"          |
| ISO 27001 A.17.1.3 | Verify and review information security continuity     | §4 score column                              |
| GDPR Art. 33      | Breach-notification triage                              | §4.1 T+41 inject and decision                 |

This document is the durable artifact for those controls. Do not delete prior exercise sections — the audit window for the SOC2 Type II is 12 months rolling.
