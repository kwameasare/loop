# Eval

Eval is a first-class Loop primitive, not a bolt-on. Every agent has at
least one eval suite, and no production deploy can ship without a green
run.

## The model

```python
from loop_eval import EvalRunner, Sample, regex_match, latency_scorer

runner = EvalRunner(scorers=[regex_match(r"order \d+"), latency_scorer(max_ms=2000)])
report = await runner.run(dataset=samples, agent=my_agent)
assert report.pass_rate >= 0.7
```

A run is `(sample → agent → output → scorers → score)`. Scorers are pure
functions. Reports are structured `EvalReport` pydantic models.

## Built-in scorers

| Scorer | Use it for |
| --- | --- |
| `exact_match` | Deterministic text equality |
| `regex_match(pattern)` | Structural assertions (e.g. "mentions an order id") |
| `llm_judge(rubric, judge=...)` | Subjective quality |
| `latency_scorer(max_ms=...)` | SLO enforcement |
| `cost_scorer(max_usd=...)` | Spend ceilings |
| `hallucination_scorer(grounding=...)` | Cite-or-die assertions |

## Production replay

Failed turns from production can be sampled into the eval suite via
`loop_eval.replay`. The capture function uses a deterministic hash so
the same `(workspace_id, request_id)` pair always lands on the same
side of the sample-rate boundary — meaning retries don't double-count.

```python
from loop_eval import capture, should_capture

if should_capture(workspace_id=ws, request_id=rid, sample_rate=0.05):
    capture(sink=sink, turn=failed_turn, sample_rate=0.05)
```

Captured turns become `Sample`s via `to_samples()` and feed back into
the same `EvalRunner` you use offline.

## Eval-gated deploys

The control plane refuses to promote a candidate version to production
if its eval pass rate regresses against the previous deploy. See the
[ops/deploy-agent-version](../../loop_implementation/skills/ops/deploy-agent-version.md)
skill for the gate's exact contract.
