# Bug Bounty Program

Loop runs a responsible-disclosure / bug-bounty program for security
researchers.  Submissions are managed through our HackerOne program page.

## Scope

**In scope** (eligible for bounty)

| Asset | Notes |
|---|---|
| `*.loop.so` — production API | All HTTP endpoints |
| `studio.loop.so` — Studio web app | Front-end + API |
| `app.loop.so` — customer-facing portal | Front-end + API |
| Published Loop SDKs (Python, TypeScript) | Published on PyPI / npm |
| Loop mobile apps (iOS, Android) | Public App Store / Play Store builds |

**Out of scope**

* `*.staging.loop.so` and `*.dev.loop.so`
* Third-party services integrated into the platform (Twilio, Stripe, etc.)
* Physical attacks, social engineering, or attacks against Loop employees
* Denial-of-service attacks
* Issues in software we do not control (browsers, OS, CDN)

## Severity and payouts

| Severity | CVSS range | Bounty (USD) |
|---|---|---|
| Critical | 9.0 -- 10.0 | $5,000 -- $20,000 |
| High | 7.0 -- 8.9 | $1,500 -- $5,000 |
| Medium | 4.0 -- 6.9 | $300 -- $1,500 |
| Low | 0.1 -- 3.9 | $100 -- $300 |
| Informational | N/A | Acknowledgement only |

Final bounty amount is determined by Loop's security team taking into account
exploitability, business impact, and quality of the report.

## Rules of engagement

1. **Do not** access, modify, or destroy data that is not your own.
2. **Do not** perform testing that could degrade service quality for other
   customers (rate limits, load testing, fuzzing in production).
3. **Do not** publicly disclose vulnerabilities until Loop has issued a fix
   and you have received written permission to disclose.
4. Testing must be performed only against accounts you own or have explicit
   permission to test.
5. Automated scanning of in-scope targets is allowed at a rate of up to
   10 requests/second from a single IP.

## Response SLA

| Stage | Target |
|---|---|
| Initial acknowledgement | 24 hours |
| Triage decision (Valid / Duplicate / N/A) | 5 business days |
| Fix shipped (Critical) | 14 calendar days |
| Fix shipped (High) | 30 calendar days |
| Fix shipped (Medium / Low) | 90 calendar days |
| Bounty paid | Within 14 days of fix |

## How to submit

1. Visit [https://hackerone.com/loop](https://hackerone.com/loop).
2. Create an account and click **Submit Report**.
3. Fill in the title, severity estimate, description, reproduction steps,
   and any supporting screenshots or proof-of-concept code.
4. We will acknowledge within 24 hours.

## Safe harbour

Loop will not pursue legal action against security researchers who:

* Follow these rules in good faith.
* Avoid privacy violations, destruction of data, and service disruption.
* Report findings to us before any public or third-party disclosure.

This program is governed by HackerOne's [standard safe harbour policy](https://www.hackerone.com/policies/disclosure).

## Hall of fame

Researchers whose reports lead to a valid finding of Medium severity or above
are listed on our [security acknowledgements page](acknowledgements.md)
(with their consent).
