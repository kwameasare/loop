# Data Processing Agreement (DPA) — Template

> Version: **1.0**  
> Owner: Legal / Security  
> Last updated: 2026-06-01  
> Status: **Approved for use**

This template is used when a customer requests a signed Data Processing
Agreement as part of their procurement process.  Fill in the bracketed
placeholders before sending to the customer for signature.

---

## DATA PROCESSING AGREEMENT

This Data Processing Agreement ("DPA") forms part of the Agreement between
**Loop Technologies, Inc.** ("Processor") and **[CUSTOMER LEGAL NAME]**
("Controller") and is effective as of **[EFFECTIVE DATE]**.

---

### 1. Definitions

| Term                   | Meaning                                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| **Agreement**          | The subscription or services agreement to which this DPA is incorporated by reference.         |
| **Personal Data**      | Any information relating to an identified or identifiable natural person processed under the Agreement. |
| **Sub-processor**      | A third-party engaged by the Processor to process Personal Data on the Controller's behalf.    |
| **Data Subject**       | The natural person to whom the Personal Data relates.                                          |
| **GDPR**               | Regulation (EU) 2016/679 and any equivalent local implementing legislation.                    |
| **SCCs**               | Standard Contractual Clauses issued under Commission Implementing Decision (EU) 2021/914.      |

---

### 2. Scope and Nature of Processing

2.1 The Processor shall process Personal Data only to the extent necessary to
deliver the Services described in the Agreement and as further documented in
**Annex I** (Description of Processing Activities).

2.2 The Processor shall not process Personal Data for its own purposes or for
any purpose other than those set out in this DPA and the Agreement unless
required to do so by applicable law.

---

### 3. Controller's Instructions

3.1 The Processor shall process Personal Data only on documented instructions
from the Controller.  The Agreement and this DPA constitute the Controller's
complete instructions as of the Effective Date.

3.2 If the Processor is required by applicable law to process Personal Data
beyond the scope of the Controller's instructions, the Processor shall inform
the Controller before such processing, unless prohibited by law.

---

### 4. Confidentiality

4.1 The Processor shall ensure that persons authorised to process Personal Data
have committed to confidentiality or are under an appropriate statutory
obligation of confidentiality.

---

### 5. Security

5.1 The Processor shall implement and maintain the technical and organisational
measures described in **Annex II** (Technical and Organisational Measures) to
ensure a level of security appropriate to the risk.

5.2 The Processor's current security certifications and attestations are
available at [https://trust.loop.ai](https://trust.loop.ai).

---

### 6. Sub-processing

6.1 The Controller grants the Processor general authorisation to engage
Sub-processors. The current list of Sub-processors is published at
[https://trust.loop.ai/sub-processors](https://trust.loop.ai/sub-processors).

6.2 The Processor shall notify the Controller of any intended changes to the
Sub-processor list at least **30 days** in advance by updating the published
list and emailing the Controller's registered security contact.

6.3 The Controller may object to a new Sub-processor by providing written
notice within 14 days of the Processor's notification. If no agreement is
reached, either party may terminate the affected Services on 30 days' notice
without penalty.

---

### 7. Data Subject Rights

7.1 The Processor shall assist the Controller in responding to Data Subject
requests under applicable law, including requests for access, rectification,
erasure, restriction, portability, and objection, within the timescales
required by applicable law.

7.2 Requests shall be submitted to **privacy@loop.ai**.

---

### 8. Data Breach Notification

8.1 The Processor shall notify the Controller without undue delay, and in any
event within **72 hours** of becoming aware of a Personal Data breach affecting
the Controller's Personal Data.

8.2 Notifications shall be sent to the Controller's designated security contact
and shall include the information required under Article 33(3) GDPR to the
extent available at the time of notification.

---

### 9. Data Protection Impact Assessments

9.1 The Processor shall provide reasonable assistance to the Controller in
carrying out data protection impact assessments and prior consultations with
supervisory authorities where required under applicable law.

---

### 10. Deletion and Return of Data

10.1 Upon termination or expiry of the Agreement, and at the Controller's
written request, the Processor shall securely delete or return all Personal
Data (and all copies thereof) within **30 days**, unless applicable law
requires further retention.

10.2 The Processor shall certify in writing that deletion has been completed
upon request.

---

### 11. Audit Rights

11.1 The Processor shall make available to the Controller all information
necessary to demonstrate compliance with this DPA.

11.2 The Processor shall allow for and contribute to audits or inspections
conducted by the Controller or a mandated third-party auditor, provided that:

* the Controller gives at least **30 days** prior written notice;
* audits are conducted during normal business hours;
* audits do not unreasonably disrupt Processor operations;
* the auditor signs a confidentiality agreement acceptable to the Processor.

11.3 The Processor's current SOC 2 Type II report satisfies the Controller's
audit rights for the period covered by the report.

---

### 12. International Data Transfers

12.1 Where the transfer of Personal Data requires a transfer mechanism under
Chapter V GDPR, the parties agree that the SCCs (Module Two: Controller to
Processor) are incorporated by reference into this DPA and shall apply.

12.2 The relevant Annexes to the SCCs are set out in **Annex III** (SCCs
Appendices) of this DPA.

---

### 13. General Provisions

13.1 **Order of precedence.** In the event of a conflict between this DPA and
the Agreement with respect to the processing of Personal Data, this DPA shall
prevail.

13.2 **Governing law.** This DPA shall be governed by the laws of the State of
Delaware, USA, unless the SCCs require a different governing law for specific
provisions.

13.3 **Termination.** This DPA shall terminate automatically on termination of
the Agreement.

---

## Annex I — Description of Processing Activities

| Field                  | Detail                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------ |
| **Categories of Data Subjects** | End-users of the Controller's AI agents (members of the public, employees, customers). |
| **Categories of Personal Data** | Conversation transcripts, session identifiers, device/browser metadata, optional PII fields submitted by end-users. |
| **Special Categories** | None by default; Controller is responsible for ensuring no special-category data is submitted unless a separate addendum is agreed. |
| **Nature of Processing** | Storage, indexing, retrieval, inference routing, logging.                               |
| **Purpose of Processing** | Delivery of AI agent runtime services as described in the Agreement.                   |
| **Retention Period**   | Active subscription + 30-day post-termination deletion window. Backup retention: 90 days. |
| **Sub-processors**     | See [https://trust.loop.ai/sub-processors](https://trust.loop.ai/sub-processors).         |

---

## Annex II — Technical and Organisational Measures

| Control Area           | Measure                                                                                   |
| ---------------------- | ----------------------------------------------------------------------------------------- |
| **Encryption at rest** | AES-256 for all persistent stores.                                                        |
| **Encryption in transit** | TLS 1.2+ enforced on all endpoints.                                                   |
| **Access control**     | Role-based access; MFA required for all production system access.                         |
| **Audit logging**      | Append-only, hash-chained audit log for all write operations; retained 90 days.           |
| **Vulnerability management** | Automated dependency scanning (Dependabot + Trivy); critical CVEs patched within 72 h. |
| **Penetration testing** | Annual third-party pen test; findings tracked to closure.                               |
| **Business continuity** | RTO ≤ 4 h, RPO ≤ 1 h; tested quarterly.                                               |
| **Incident response**  | Documented IR runbook; 24/7 on-call; 72-hour breach notification SLA.                    |
| **Sub-processor due diligence** | All sub-processors assessed annually against ISO 27001 or SOC 2 Type II.       |

---

## Annex III — SCC Appendices

_Populate per the SCCs Module Two template when applicable._

---

*For questions, contact **privacy@loop.ai**.*
