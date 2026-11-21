# GRAFT experiments

Each test has a README (Question, Setup, Result, Decision, Revisions), `config.yaml` naming the run configs, and `runs/run-NN/run.json`. Designs live in [docs/design/](../docs/design/). Old runs are never edited: a fix or rerun is a new run-NN and a Revisions line.

| Test | Question | Status | Current run | Decision |
|---|---|---|---|---|
| [01 · Read order and starting graph](test-01-read-order/README.md) | Which read order (A: PPR then GNN + GOAt; B: GNN + GOAt then PPR; C: PPR, GNN + GOAt, short PPR) and which starting graph (empty vs D, a synthetic starting graph) answer FactConsolidation multi-hop best? | done | run-02 | Mode C (`ppr_goat_ppr`) is the default read order, answers capped at 256 tokens |
| [02 · Retrieval variants on mode C](test-02-retrieval-variants/README.md) | Does anything added to mode C bring more gold facts to the model and more right answers? | done | run-01 | Mode C with GOAt stays; none of the variants is kept |
| [03 · Base graph from RoG (Freebase)](test-03-base-graph-rog/README.md) | Does a base knowledge graph under the documents (GRAFT layer 1) help, starting with a 20,000-fact Freebase slice from RoG? | done | run-01 | Not adopted: a small off-domain base mostly adds hub noise to PageRank |
| [04 · Base graph from full T-REx (Wikidata)](test-04-base-graph-trex-full/README.md) | Does a large general base graph (all T-REx triples on its 45 most common Wikidata properties) under the documents help GRAFT answer? | done | run-02 | Not adopted: the T-REx base halves accuracy (17-19% vs 34.7%); GRAFT keeps the empty-start graph |
| [05 · Working memory in the graph](test-05-working-memory/README.md) | Does answering in steps, with the question, sub-steps, notes and partial results written into the graph and read back, beat one-shot GRAFT, and does writing to the graph matter or only answering in steps? | done on Haiku, Qwen pending | run-02 | Not kept on Haiku: C is about 1 point over A in two rounds (35.3, 35.7 vs 34.7), inside the spread, at three times the cost; writing to the graph beats prompt-only by 2.6-2.7 |
| [06 · T-REx as a structure guide](test-06-trex-structure-guide/README.md) | Does T-REx help as a guide to how facts connect (B), a walk-only bridge (C) or labelled background facts (D), with no T-REx fact reaching the answering model as a memory? | done on Haiku | run-01 | **Guide kept: 45.7 vs 34.7.** Bridge (17.3) and labelled background (17.7) not adopted |

## Designs

- [Working memory in the graph](../docs/design/graft_working_memory_design.md) (test 05)
- [T-REx as a structure guide](../docs/design/graft_trex_structure_guide_design.md) (test 06, approved)

## Reports

- [Why the T-REx base halved accuracy](test-04-base-graph-trex-full/runs/run-02/analysis/why_accuracy_halved.md) (test 04 run-02)
- [Fixed Haiku check, history](test-07-haiku-drift/haiku_canary.md) (the same 100 prompts in every paid Haiku batch)
- [Why arm A scored 34.7 when mode C scored 38](test-07-haiku-drift/baseline_check.md) (test 05): nothing on our side changed; identical inputs score about 34 today on Haiku
- [T-REx cleaning: everything dropped](test-04-base-graph-trex-full/runs/run-02/cleaning/dropped_items.md) (test 04 run-02, also .pdf)
- [Read order, starting graph and baselines, full write-up](../docs/experiments.md) (test 01)
