# DPA Redlines Workflow

> Owner: Legal / GTM  
> Last updated: 2026-06-01  
> Status: **Active**

This document describes the process for handling customer-requested
redlines to Loop's standard Data Processing Agreement (DPA).

---

## Overview

Enterprise customers frequently request changes ("redlines") to the
standard DPA before signing. This workflow ensures redlines are reviewed
promptly, tracked transparently, and never silently accepted.

---

## Roles

| Role                  | Responsibility                                                    |
| --------------------- | ----------------------------------------------------------------- |
| **Account Executive** | Receives redline request; opens a redline PR; keeps customer informed. |
| **Legal Reviewer**    | Reviews each redline for risk; approves, rejects, or counter-proposes. |
| **Security Reviewer** | Reviews any change to Annex II (TOMs) or sub-processor terms.    |
| **DPA Owner**         | Merges approved PRs; updates the canonical DPA.md; cuts signed PDF. |

---

## Process

### Step 1 — Customer Sends Redlines

Customers submit redlines as:

* A Word (`.docx`) track-changes document, **or**
* A marked-up PDF, **or**
* A plain list of proposed clause changes.

The Account Executive forwards the redlines to **legal@loop.ai** with
the subject line `DPA Redlines — [CUSTOMER NAME] — [DATE]`.

---

### Step 2 — Open a Redline PR

The Legal Reviewer (or AE) opens a Pull Request against
`loop_implementation/engineering/DPA.md` in this repository:

1. **Branch naming**: `legal/dpa-redlines-<customer-slug>-<YYYY-MM-DD>`
2. **PR title**: `DPA redlines: <Customer Name>`
3. **PR description** must include:
   - Customer name and CRM link
   - Summary of each proposed change
   - Risk assessment (Low / Medium / High) for each change
   - Proposed Loop counter-position for any rejected clause

**Label the PR** with `dpa-redlines` and assign the Legal Reviewer and
Security Reviewer as required reviewers.

---

### Step 3 — Review and Negotiate

* The Legal Reviewer reviews each changed line in the PR diff.
* Accepted changes are committed directly.
* Rejected changes are commented with the rationale and a
  counter-proposal, which is communicated back to the customer.
* Security Reviewer must approve any change to Annex II or §6 (sub-processors).
* **SLA**: initial response within **3 business days** of PR open.

---

### Step 4 — Close the Redline PR

Once all redlines are resolved (accepted, rejected, or counter-accepted):

1. The DPA Owner merges the PR with a **squash merge**.
2. The merged DPA.md commit SHA is recorded in the CRM as the
   authoritative version for this customer.
3. Legal generates a signed PDF from the merged DPA and delivers it
   to the customer.

---

### Step 5 — Archive

* The signed PDF is stored in the legal archive (link in CRM record).
* The redline PR is closed with the label `dpa-redlines:signed`.
* The AE updates the CRM opportunity to `DPA Signed`.

---

## Sample Redline PR (Closed)

The following PR demonstrates the full workflow end-to-end:

**PR**: `legal/dpa-redlines-acme-corp-2026-06-01`  
**Customer**: Acme Corp  
**Changes negotiated**:

| Clause | Customer Ask | Loop Response | Outcome |
| ------ | ------------ | ------------- | ------- |
| §6.2 (sub-processor notice) | Reduce notice period from 30 to 10 days | Counter: 14 days | **Accepted** |
| §11.2 (audit rights) | Remove requirement for auditor to sign NDA | Rejected: NDA required to protect IP | **Rejected — standard language retained** |
| §8.1 (breach notification) | Reduce breach notification from 72 h to 24 h | Counter: 48 h | **Accepted** |
| Annex II (TOMs) | Add requirement for SOC 2 Type II report annually | Already standard practice | **Accepted as-is** |

**Resolution**: PR merged at commit `abc1234`; signed PDF archived; CRM updated.

---

## Escalation

If a customer requests a change that cannot be resolved within the
standard process (e.g., changes to governing law, limitation of
liability, or data residency commitments outside existing regions),
escalate to the **VP of Legal** and **Head of Security**.

---

## References

* [DPA.md](DPA.md) — Canonical DPA template
* [REGIONAL_DEPLOYS.md](REGIONAL_DEPLOYS.md) — Data residency commitments
* [SOC2.md](SOC2.md) — SOC 2 compliance status
* [SECURITY.md](SECURITY.md) — Security controls (Annex II basis)
