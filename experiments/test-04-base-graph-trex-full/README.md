# Test 04 · Base graph from full T-REx (Wikidata)

| Test | Date | Status | Current run |
|---|---|---|---|
| 04 | 2026-11-21 | done | [run-02](runs/run-02/run.json) |

## Candidates and setups

IDs from the [registry](../../docs/REGISTRY.md) (frozen 2026-11-21). A candidate is the method, a setup is the candidate plus model,
answer cap, benchmark and scoring; old run folders keep their names.

| Candidate | Setup | Row in this test |
|---|---|---|
| G08 | S17 | Mode C, GOAt, empty-start graph (test 05 arm A) |
| G27 | S48 | Mode C, EiG |
| G28 | S51 | Mode C, GOAt (2 of 3 repeats: job time limit) |
| G29 | S53 | Question layer + EiG |

## Question

Does a large general base graph (all T-REx triples on its 45 most common Wikidata properties) under the documents help GRAFT answer?

## Setup

Base: 1,215,416 facts, 344,996 entities (leakage-checked). Haiku writes the 537 chunks onto it with entity linking (62.8% of document names matched to the base, vs 55.8% by exact name); 1,230,691 facts in the built graph. Answer passes: mode C with EiG, GOAt, and question layer + EiG, 3 repeats each; then Qwen instead of Haiku on the same graph.

## Result

run-01 (build + first answer passes): all 9 repeats scored 0.0. Cause: NetworkX PageRank stopped after one step on the 1.58M-node graph, so the 400-node subgraphs held no facts. Fixed (a stop rule that holds on big graphs), plus: never link a single stopword (an entity named "THE" matched 89 of 100 questions), and a run stops if most questions get no facts.

run-02: base cleaning ([everything dropped](runs/run-02/cleaning/dropped_items.md): 60 entities, 107 facts; generic words kept; the first, too-wide rule was caught before use), stopword-link counts ([stopword_links.jsonl](runs/run-02/cleaning/stopword_links.jsonl)), then the 9 Haiku answer passes and 3 Qwen passes on the **original, uncleaned** graph (user: the dropped items are mostly real facts, and the linking rule already fixes "THE"; the cleaned graph stays on file, unused).

run-02 answer passes (Haiku, mode C, 100 multi-hop questions per repeat, original graph; Fir CPU jobs 4762064, 4751804, 4742454):

| Pass | Accuracy (per repeat) | Mean (SD) | Gold in final facts | Cost / 100 q | Time / q |
|---|---|---|---|---|---|
| EiG | 18 / 15 / 20 | 17.7 (2.5) | 33.3 | $0.066 | 2.6 s |
| GOAt | 17 / 21 / - | 19.0 (2 repeats) | 34.0 | $0.067 | 3.6 s |
| Question layer + EiG | 18 / 16 / 17 | 17.0 (1.0) | 28.0 | $0.081 | 3.1 s |
| Reference: mode C GOAt, empty-start document graph (test 05 arm A) | 35 / 34 / 35 | 34.7 (0.6) | 50.7 | $0.027 | |

The facts now reach Haiku (49 per question on average, none empty), but the base pulls PageRank toward T-REx facts that are not about the documents: the gold fact is in the final facts for about a third of questions, against half on the document graph alone, and accuracy halves. Why: [analysis](runs/run-02/analysis/why_accuracy_halved.md), mostly crowding out (T-REx sentences take two thirds of the slots and push out the edited document facts), sometimes a T-REx fact that contradicts the gold. GOAt's third repeat hit the job's 2 h limit and was not rerun: the gap to the reference (about 15 points) is far beyond the repeat spread.

## Decision

Not adopted. A full T-REx base under the documents halves GRAFT's accuracy (17 to 19% vs 34.7%) on these questions; GRAFT keeps the empty-start document graph. The Qwen swap runs on that graph instead (test 05, Qwen arms), and the three Qwen jobs on the T-REx graph were cancelled before they started ($0).

## Revisions

- 2026-11-21: **run-01's answer passes are invalid** (setups S48, S51, S53; registry rule: pre-fix runs keep their IDs and are marked invalid): `exp_c_real_mh_262k_ans256_trexfull_link_build_eig` (answer pass), `exp_c_real_mh_262k_ans256_trexfull_goat`, `exp_c_real_mh_262k_ans256_trexfull_qgraph_eig`. NetworkX PageRank's stop rule grows with graph size, so on 1.58M nodes it stopped after one step and returned 0 facts; the all-caps entity "THE" also linked to "the" in 89 of 100 questions. Both were fixed with no config switch; run-02 (pprfix) replaces these passes. The run-01 graph build itself stays valid.
- 2026-11-20: test folder created from the existing runs and the Flotilla run log.
- 2026-11-21: why accuracy halved, 10 failed questions checked (runs/run-02/analysis/).
- 2026-11-21: run-02 answer passes done; decision: not adopted; Qwen moved to the empty-start graph.
- 2026-11-20: runs use the original graph, not the cleaned one (user). Node vectors are embedded once (scripts/embed_graph.py) and loaded by every pass; GPU and CPU twins per pass, whichever starts first.
