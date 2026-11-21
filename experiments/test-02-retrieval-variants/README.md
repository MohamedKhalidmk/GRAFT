# Test 02 · Retrieval variants on mode C

| Test | Date | Status | Current run |
|---|---|---|---|
| 02 | 2026-11-19/20 | done | [run-01](runs/run-01/run.json) |

## Question

Does anything added to mode C bring more gold facts to the model and more right answers?

## Setup

Same graph and questions as test 01, mode C as baseline (38%). Free checks first (gold fact in subgraph and in the final 50), paid repeats only for variants that beat the baseline on the free check.

## Result

| Variant | Result | Decision |
|---|---|---|
| EiG instead of GOAt | 36% vs 37% (one question), 2.6x faster | GOAt stays default |
| Embedding entity linking (k=5) | gold present 51% -> 22-25% (free) | rejected |
| 50/50 hybrid with embedding search | 3 repeats, 32.0% mean vs 38% | not adopted |
| Top-10 hybrid | 3 repeats 33/31/29 vs 38 | not adopted |
| Question graph (Haiku parses the question) | 3 repeats 39/37/35 (mean 37.0) vs 38 | not adopted |
| Bigger subgraphs, 1,600-node GNN | gold in final 48% vs 51% (free) | not adopted |

## Decision

Mode C with GOAt stays; none of the variants is kept. Source: Flotilla docs/run_log.md (2026-11-19/20 entries).

## Revisions

- 2026-11-20: test folder created from the existing runs and the Flotilla run log.
