# Test 01 · Read order and starting graph

| Test | Date | Status | Current run |
|---|---|---|---|
| 01 | 2026-11-13 | done | [run-02](runs/run-02/run.json) |

## Question

Which read order (A: PPR then GNN + GOAt; B: GNN + GOAt then PPR; C: PPR, GNN + GOAt, short PPR) and which starting graph (empty vs D, a synthetic starting graph) answer FactConsolidation multi-hop best?

## Setup

Claude Haiku 5.5 writes the graph once from the 537 FC chunks (empty start; D extends a synthetic graph). 100 MH questions, 50 facts per answer. BM25 and HippoRAG 2 as baselines under the same conditions. Configs: `configs/runs/exp/{a,b,c,d_extend,bm25}_real_mh_262k*.yaml`, `hipporag_real_mh_262k*.yaml`.

## Result

| Variant | 16-token answers | 256-token answers | Gold reached the model |
|---|---|---|---|
| A | 15 | 37 | 51 |
| B | 13 | 37 | 51 |
| C | 17 | **38** | 51 |
| D (synthetic start) | 22 | 37 | 44 |
| BM25 | 1 | 4 | 32 |
| HippoRAG 2 | 0 | 15 | |

With room to answer, A, B, C and D do not differ; the 16-token gaps came from cut-off answers. Retrieval is the limit: the gold fact reaches the model in 51 of 100 questions. Full write-up: [docs/experiments.md](../../docs/experiments.md).

## Decision

Mode C (`ppr_goat_ppr`) is the default read order, answers capped at 256 tokens.

## Revisions

- 2026-11-20: test folder created from the existing runs and the Flotilla run log.
