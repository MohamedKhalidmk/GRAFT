# Test 04 · Base graph from full T-REx (Wikidata)

| Test | Date | Status | Current run |
|---|---|---|---|
| 04 | 2026-11-20 | running | [run-02](runs/run-02/run.json) |

## Question

Does a large general base graph (all T-REx triples on its 45 most common Wikidata properties) under the documents help GRAFT answer?

## Setup

Base: 1,215,416 facts, 344,996 entities (leakage-checked). Haiku writes the 537 chunks onto it with entity linking (62.8% of document names matched to the base, vs 55.8% by exact name); 1,230,691 facts in the built graph. Answer passes: mode C with EiG, GOAt, and question layer + EiG, 3 repeats each; then Qwen instead of Haiku on the same graph.

## Result

run-01 (build + first answer passes): all 9 repeats scored 0.0. Cause: NetworkX PageRank stopped after one step on the 1.58M-node graph, so the 400-node subgraphs held no facts. Fixed (a stop rule that holds on big graphs), plus: never link a single stopword (an entity named "THE" matched 89 of 100 questions), and a run stops if most questions get no facts.

run-02: base cleaning ([everything dropped](runs/run-02/cleaning/dropped_items.md): 60 entities, 107 facts; generic words kept; the first, too-wide rule was caught before use), stopword-link counts ([stopword_links.jsonl](runs/run-02/cleaning/stopword_links.jsonl)), then the 9 Haiku answer passes and 3 Qwen passes: pending.

## Decision

Pending the run-02 answer passes.

## Revisions

- 2026-11-20: test folder created from the existing runs and the Flotilla run log.
