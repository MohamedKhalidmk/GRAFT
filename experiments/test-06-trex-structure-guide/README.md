# Test 06 · T-REx as a structure guide, not an answer source

| Test | Date | Status | Current run |
|---|---|---|---|
| 06 | 2026-11-21 | running | run-01 |

## Question

Test 04 showed that T-REx facts in the graph crowd out the documents' edited facts and halve accuracy. Does T-REx help
when no T-REx fact reaches the answering model as a memory: as a guide to how facts connect (B), as a bridge in the walk
only (C), or as a few clearly labelled background facts that the knowledge pool always overrides (D)?

## Setup

Design: [docs/design/graft_trex_structure_guide_design.md](../../docs/design/graft_trex_structure_guide_design.md). The
same 100 FactConsolidation multi-hop questions, Haiku, 256-token answers, 3 repeats per arm, mode C (`ppr_goat_ppr`).
Each paid batch starts with the fixed Haiku check ([haiku_canary.md](../haiku_canary.md)).

| Arm | Graph | T-REx used for | Facts Haiku sees | Config |
|---|---|---|---|---|
| A | empty start, documents only | nothing | documents | test 05 arm A (34.7, rerun the same day 34.7) |
| B | empty start, documents only | the guide (`my_method/guide.py`): relation mapping adds missed revisions, type-checked name merges, chain planning that follows the parsed chain through the documents | documents: planned chain first (at most 10), then mode C | [b_guide.yaml](../../configs/runs/exp/tg/b_guide.yaml) |
| C | the test 04 full T-REx graph | walk edges touching a T-REx fact weigh 0.2 (documents 1.0) | documents only | [c_bridge.yaml](../../configs/runs/exp/tg/c_bridge.yaml) |
| D | as C | as C, plus the top 5 T-REx facts per question shown apart as labelled background, with the rule that the knowledge pool always wins | documents, plus 5 labelled background facts | [d_background.yaml](../../configs/runs/exp/tg/d_background.yaml) |

The guide (`scripts/trex_guide.py`) holds only relation labels, coarse types, type signatures, relation chain counts and
name types, from the raw T-REx parquet (1.46M triples, 248 Wikidata properties with labels and aliases): no
(subject, object) pair.

## Result

Free steps (run-01):

- Coverage: the guide maps 244 of 253 question relations and 17,820 of 18,088 document facts (cosine >= 0.8); the 45
  properties of the test 04 base covered only 144 question relations.
- Dry check without an LLM (`scripts/guide_check.py`): linking added 1,012 revisions the writer missed and merged 9
  name variants (0 refused). The first version joined "founded by" with "founded in city" at cosine 0.91, so labels now
  join only at 0.92 or above. The planned chain holds the gold answer for 44 of 100 questions (mode C's facts: 49),
  10 where mode C's facts do not, and 18 that the question layer got wrong.

Paid arms B, C, D: running (Fir).

## Decision

Pending. Keep an arm if it beats A by more than the repeat spread.

## Revisions

- 2026-11-21: design approved (user); arm D added (user); guide built from the raw T-REx parquet after the 45-property
  base covered too few question relations; revision threshold raised to 0.92 after the dry check; arm C reran with
  200 GB after running out of memory at 64 GB ($0); arm D started in parallel with C (user).
