# GRAFT experiments

Each test has a README (Question, Setup, Result, Decision, Revisions), `config.yaml` naming the run configs, `runs/run-NN/` with the small per-run files, and `table.csv`, `table.md` and `figure.png` built by its `make_table.py` from those runs. Designs live in [docs/design/](../docs/design/). Old runs are never edited: a fix or rerun is a new run-NN and a Revisions line.

Candidate IDs (G01...) and setups (S01...) are in the [registry](../docs/REGISTRY.md).

| Test | Question | Status | Current run | Decision |
|---|---|---|---|---|
| [01 · Read order and starting graph](test-01-read-order/README.md) | Which read order (A: PPR then GNN + GOAt; B: GNN + GOAt then PPR; C: PPR, GNN + GOAt, short PPR) and which starting graph (empty vs D, a synthetic starting graph) answer FactConsolidation multi-hop best? | done | run-02 | **G08** (mode C, `ppr_goat_ppr`) is the default read order, answers capped at 256 tokens; G04 (A), G07 (B), G09 (D) not adopted |
| [02 · Retrieval variants on mode C](test-02-retrieval-variants/README.md) | Does anything added to mode C bring more gold facts to the model and more right answers? | done | run-01 | G08 (mode C with GOAt) stays; none of G10-G23 is kept |
| [03 · Base graph from RoG (Freebase)](test-03-base-graph-rog/README.md) | Does a base knowledge graph under the documents (GRAFT layer 1) help, starting with a 20,000-fact Freebase slice from RoG? | done | run-01 | G25 not adopted (G24 cancelled): a small off-domain base mostly adds hub noise to PageRank |
| [04 · Base graph from full T-REx (Wikidata)](test-04-base-graph-trex-full/README.md) | Does a large general base graph (all T-REx triples on its 45 most common Wikidata properties) under the documents help GRAFT answer? | done | run-02 | G27-G29 not adopted (G26 cancelled): the T-REx base halves accuracy (17-19% vs 34.7%); GRAFT keeps the empty-start graph |
| [05 · Working memory in the graph](test-05-working-memory/README.md) | Does answering in steps, with the question, sub-steps, notes and partial results written into the graph and read back, beat one-shot GRAFT, and does writing to the graph matter or only answering in steps? | done on Haiku; on Qwen in test 08 | run-02 | G31 and G33 not kept on Haiku: about 1 point over G08 in two rounds (35.3, 35.7 vs 34.7), inside the spread, at three times the cost; writing to the graph beats prompt-only by 2.6-2.7 (on Qwen level: 33.3 vs 33.0) |
| [06 · T-REx as a structure guide](test-06-trex-structure-guide/README.md) | Does T-REx help as a guide to how facts connect (B), a walk-only bridge (C) or labelled background facts (D), with no T-REx fact reaching the answering model as a memory? | done on Haiku; on Qwen in test 08 | run-03 | **G35 (the guide) kept: 45.7 vs 34.7, confirmed the same day (46.0 vs 34.0).** G36 (bridge, 17.3) and G37 (background, 17.7) not adopted. G38 (guide + working memory, 46.7, level with G35 at twice the cost) parked, not dropped |
| [07 · Haiku drift and the fixed check](test-07-haiku-drift/README.md) | Mode C scored 38 on 2026-11-13 and 34.7 a week later: did our side change, or Haiku? | done | run-01 | G08's identical prompts score about 34 now on Haiku; nothing on our side differs. Compare within one day; the Haiku check (S101) opens every paid batch |
| [08 · GRAFT on Qwen](test-08-graft-on-qwen/README.md) | Do the Haiku results carry over when Qwen3.8-27B (W4A16, local) answers: mode C, the guide, and working memory in the graph vs in the prompt? | run-01 done, run-02 running | run-01 | **G35 holds on Qwen: 47.0 vs 39.3 for G08** (256-token cap, a lower bound). G33 33.3, G34 33.0; all five arms rerunning at 1,024 tokens (run-02) |

## Designs

- [Working memory in the graph](../docs/design/graft_working_memory_design.md) (test 05)
- [T-REx as a structure guide](../docs/design/graft_trex_structure_guide_design.md) (test 06, approved)

## Reports

- [Why the T-REx base halved accuracy](test-04-base-graph-trex-full/runs/run-02/analysis/why_accuracy_halved.md) (test 04 run-02)
- [Fixed Haiku check, history](test-07-haiku-drift/haiku_canary.md) (the same 100 prompts in every paid Haiku batch)
- [Why arm A scored 34.7 when mode C scored 38](test-07-haiku-drift/baseline_check.md) (test 07): nothing on our side changed; identical inputs score about 34 today on Haiku
- [T-REx cleaning: everything dropped](test-04-base-graph-trex-full/runs/run-02/cleaning/dropped_items.md) (test 04 run-02, also .pdf)
- [Read order, starting graph and baselines, full write-up](../docs/experiments.md) (test 01)
