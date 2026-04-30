# Security policy

Loop takes the security of its software seriously. If you believe you have
found a security vulnerability in any Loop repository, please report it to
us as described below.

## Reporting a vulnerability

**Do not file a public GitHub issue.**

Instead:

- **Email:** `security@loop.example` (PGP key fingerprint published on the
  Loop website once available).
- **GitHub private vulnerability reporting:** open a private advisory at
  <https://github.com/loop-ai/loop/security/advisories/new>.

Please include:

- A description of the issue and its impact.
- Reproduction steps (proof-of-concept, scripts, screenshots).
- The version / commit SHA where you observed the issue.
- Any mitigation you may already have applied.

## Response timeline

| Stage                  | Target SLA          |
|------------------------|---------------------|
| Acknowledge receipt    | Within 2 business days |
| Initial triage + severity | Within 5 business days |
| Fix or mitigation date | Within 30 days for High/Critical, 90 days for Medium |
| Coordinated disclosure | Within 90 days of first report (unless extended by mutual agreement) |

We follow [coordinated disclosure](https://en.wikipedia.org/wiki/Coordinated_disclosure)
practice and will credit reporters in the advisory unless they request
anonymity.

## Scope

In scope:

- Code in this repository (runtime, gateway, control plane, channels, SDK,
  studio, eval harness, infra IaC).
- Loop-managed cloud services derived from this code.

Out of scope (report directly to the upstream vendor):

- Third-party LLM provider security (OpenAI, Anthropic, etc.).
- Third-party MCP servers not authored by Loop.
- Self-hosted deployments operated by the customer where the vulnerability
  is misconfiguration on the customer side.

## Safe-harbor

Good-faith research is welcome. Loop will not pursue legal action against
researchers who:

- Do not access, modify, or destroy data beyond what is necessary to
  demonstrate the vulnerability.
- Do not perform DoS, social engineering, or physical attacks.
- Give us a reasonable opportunity to remediate before public disclosure.

## Reference

Full threat model and security controls live in
[loop_implementation/engineering/SECURITY.md](loop_implementation/engineering/SECURITY.md).
