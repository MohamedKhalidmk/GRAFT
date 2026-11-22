# Test 02 · Retrieval variants on mode C

| Test | Date | Status | Current run |
|---|---|---|---|
| 02 | 2026-11-19/20 | done | [run-01](runs/run-01/run.json) |

## Candidates and setups

IDs from the [registry](../../docs/REGISTRY.md) (frozen 2026-11-21). A candidate is the method, a setup is the candidate plus model,
answer cap, benchmark and scoring; old run folders keep their names.

| Candidate | Setup | Row in this test |
|---|---|---|
| G04 | S09 | Mode A with GOAt, 2026-11-13 (test 01) |
| G08 | S17 | Mode C with GOAt, 2026-11-13 (test 01) |
| G10 | S24 | Mode A, EiG instead of GOAt |
| G10 | S25 | Mode A, EiG |
| G11 | S26 | Mode C, EiG (free-check baseline) |
| G12 | S27 | 50/50 hybrid with embedding search, EiG |
| G12 | S28 | 50/50 hybrid, EiG |
| G13 | S29 | 50/50 hybrid with embedding search, GOAt |
| G13 | S30 | 50/50 hybrid, GOAt |
| G14 | S31 | 50/50 hybrid, 800-node subgraph |
| G15 | S32 | 50/50 hybrid, 1,600-node subgraph |
| G16 | S33 | Top-10 hybrid, EiG |
| G16 | S34 | Top-10 hybrid, EiG |
| G17 | S35 | Top-5 hybrid, EiG |
| G18 | S36 | Embedding entity linking (k=5), EiG |
| G19 | S37 | Embedding entity linking (k=5), GOAt |
| G20 | S38 | Linking + hybrid, EiG |
| G21 | S39 | Linking + hybrid, GOAt |
| G22 | S40 | Bigger subgraphs, 1,600-node GNN |
| G23 | S41 | Question graph (Haiku parses the question), EiG |
| G23 | S42 | Question graph, EiG |
| Embedding RAG (bge-small) | S78 | Embedding search only (no graph) |

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
