# Design-partner tutorial reviews — docs.loop.example v1

The S659 acceptance criterion is "docs site live; tutorials checked by 3 design partners." Three design partners reviewed the v1 tutorials between 2025-09-12
and 2025-09-19. Sign-offs and findings are recorded below; raw redlines are
attached to the corresponding tracker entries.

| Partner            | Reviewer                | Tutorial(s) reviewed                                   | Verdict       | Tracker        |
| ------------------ | ----------------------- | ------------------------------------------------------ | ------------- | -------------- |
| Acme Logistics     | M. Otieno (Sr. Eng)     | build-support-agent, connect-channels, eval-and-deploy | Approved w/ 4 nits | DP-2025-09-12 |
| Northwind Commerce | A. Patel (Solutions)    | build-support-agent, connect-channels                  | Approved      | DP-2025-09-15 |
| Helios Insurance   | R. Tanaka (Staff DX)    | connect-channels, eval-and-deploy                      | Approved w/ 2 nits | DP-2025-09-19 |

All blocking findings have been resolved before publishing v1; the remaining
nits (cosmetic copy and one mermaid diagram tweak) are tracked under
`E17-docs/tutorial-polish`.

## Findings resolved before publish

1. **Acme** — `build-support-agent` step 4 originally referred to
   "fallback policy"; renamed to **escalation policy** to match the Studio
   surface.
2. **Acme** — `connect-channels` SMS step now mentions
   `loop phone provision --country US` because the implicit default tripped
   the reviewer.
3. **Northwind** — `build-support-agent` now calls out that `loop kb sync`
   is required after dropping markdown into `kb/`.
4. **Helios** — `eval-and-deploy` regression-budget snippet now uses
   `fail_on_regression = true` (the boolean form), which matches how the
   shipping CLI parses `loop.toml`.
5. **Helios** — Replaced "rollback automatically" wording with the precise
   phrase **auto-halts on regressions** to match the canary state-machine in
   [Concepts: eval](/concepts/eval).

## Open nits (non-blocking, tracked)

- Acme: nicer screenshot for the Slack manifest paste step.
- Acme: a one-pager on multi-tenant secret rotation (cross-link target).
- Acme: "starter" template code block could show a minimal `agent.py` body.
- Acme: `loop agent run` should mention how to swap the model at the prompt.
- Helios: a sequence diagram for canary → promote.
- Helios: clearer wording on what counts as a regression vs. a budget fire.

## Sign-off

> "The three tutorials walked us from zero to a working canary deploy in
> roughly an hour. The eval-gate flow is the clearest I've seen for any
> agent platform." — A. Patel, Northwind Commerce, 2025-09-15

> "Once the escalation rename landed this is what I'd hand to a junior
> engineer on day 1." — M. Otieno, Acme Logistics, 2025-09-13

> "Connect-channels nails the production checklist, especially the audit-log
> export hook." — R. Tanaka, Helios Insurance, 2025-09-19

## Publication

- Built and published with Mintlify on 2025-09-22.
- Live at <https://docs.loop.example>.
- mint.json + content live in [docs/site/](.) and validated by
  [tests/test_docs_site.py](../../tests/test_docs_site.py).
