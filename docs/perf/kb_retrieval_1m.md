# KB Retrieval 1M Benchmark

S842 adds a nightly KB retrieval performance gate for a synthetic corpus
with 1M chunks.

- Script: `scripts/kb_retrieval_perf.py`
- Workflow: `.github/workflows/kb-retrieval-perf.yml`
- Report: `bench/results/kb_retrieval_1m.json`
- Threshold: fail when p50 retrieval latency is 200 ms or higher

The fixture models a million indexed chunks with deterministic sparse
postings, then times top-k retrieval across repeated queries. This keeps
the benchmark stable in CI while still exercising the retrieval ranking
path and preventing accidental high-latency regressions.
