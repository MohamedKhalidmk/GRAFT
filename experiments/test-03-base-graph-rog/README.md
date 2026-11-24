# Test 03 · Base graph from RoG (Freebase)

| Test | Date | Status | Current run |
|---|---|---|---|
| 03 | 2026-11-20 | done | [run-01](runs/run-01/run.json) |

## Candidates and setups

IDs from the [registry](../../docs/reference/REGISTRY.md) (frozen 2026-11-21). A candidate is the method, a setup is the candidate plus model,
answer cap, benchmark and scoring; old run folders keep their names.

| Candidate | Setup | Row in this test |
|---|---|---|
| G08 | S17 | Mode C, empty-start graph (test 01, 2026-11-13) |
| G25 | S44 | Mode C (EiG) + RoG base, Haiku linking |
| G25 | S45 | Same graph, fake answerer |

## Question

Does a base knowledge graph under the documents (GRAFT layer 1) help, starting with a 20,000-fact Freebase slice from RoG?

## Setup

20,000 leakage-checked RoG-WebQSP/CWQ facts (my_method/base_graph.py). Haiku writes the documents onto it, linking each new name to the base (top 10 by name embedding, Haiku picks one or new).

## Result

Haiku matched 21.9% of document names to a base entity (13.3% by exact name); 79% of document facts touch a base entity, almost all through hubs (USA, football, Catholicism). Gold in final facts 42% in the free check and 41% in the paid run; accuracy 21% (one real run, 2026-11-20) vs mode C 38% (one run, 2026-11-13; 34.7 over 6 repeats a week later, see test 07).

## Decision

Not adopted: a small off-domain base mostly adds hub noise to PageRank. The full T-REx base is the real test (test 04).

## Revisions

- 2026-11-20: test folder created from the existing runs and the Flotilla run log.
