# Test 06 · T-REx as a structure guide, not an answer source

| Test | Date | Status | Current run |
|---|---|---|---|
| 06 | 2026-11-21 | done on Haiku (Qwen next) | [run-01](runs/run-01/) |

## Question

Test 04 showed that T-REx facts in the graph crowd out the documents' edited facts and halve accuracy. Does T-REx help
when no T-REx fact reaches the answering model as a memory: as a guide to how facts connect (B), as a bridge in the walk
only (C), or as a few clearly labelled background facts that the knowledge pool always overrides (D)?

## Setup

Design: [docs/design/graft_trex_structure_guide_design.md](../../docs/design/graft_trex_structure_guide_design.md). The
same 100 FactConsolidation multi-hop questions, Haiku, 256-token answers, 3 repeats per arm, mode C (`ppr_goat_ppr`).
Each paid batch starts with the fixed Haiku check ([haiku_canary.md](../test-07-haiku-drift/haiku_canary.md)).

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

Paid arms, Haiku, 3 repeats each ([table.csv](table.csv), built by `make_table.py` from the runs; Fir 4834168, 4832786,
4834224):

| Arm | Accuracy (mean, SD) | Per repeat | Gold fact in final facts | Cost / 100 questions |
|---|---|---|---|---|
| A · empty start, mode C (rerun the same day) | 34.7, 1.5 | 36 / 33 / 35 | 50.3 | $0.027 |
| B · T-REx as a structure guide | **45.7**, 1.5 | 47 / 46 / 44 | 60.3 | $0.037 |
| C · T-REx as a bridge, documents only | 17.3, 1.2 | 18 / 16 / 18 | 32.0 | $0.022 |
| D · C + 5 labelled background facts | 17.7, 1.5 | 19 / 16 / 18 | 33.0 | $0.029 |

B beats A by 11 points, about seven times the repeat spread, and brings the gold fact to the model for 10 more questions in
100; its added cost is the question parse (one short Haiku call). C shows that T-REx hurts even when none of its facts
are returned: in the walk it still pulls PageRank away from the documents, so gold in the final facts falls to 32%, as
in test 04. D's labelled background facts change nothing on top of C. Spend $0.263 (B $0.110, C $0.067, D $0.086).
The Haiku checks at the start of the B and D batches collided in one run folder (both started in the same second; fixed
in eval/run.py since), so this round has no clean check.

run-02, the same-day confirmation (user): arm A and the guide rerun side by side on 2026-11-21, after a clean fixed Haiku
check on its own (36, inside its 33-36 range; [test 07](../test-07-haiku-drift/haiku_canary.md)). Fir 4868000, 4868003:

| Arm | Accuracy (mean, SD) | Per repeat | Gold fact in final facts |
|---|---|---|---|
| A · mode C | 34.0, 0.0 | 34 / 34 / 34 | 50.7 |
| B · T-REx structure guide | **46.0**, 3.0 | 46 / 43 / 49 | 60.0 |

The gain holds: +12.0 the same day (+11.0 in run-01). Spend $0.217 (A $0.080, B $0.109, Haiku check $0.027).

run-03, arm E (user): the guide plus working memory written into the graph (test 05 C v2, the guide's planned chain
cited from the first step), against the guide alone the same day. Fir 4874611, 4874613; the fixed Haiku check before
it scored 35.

| Arm | Accuracy (mean, SD) | Per repeat | Gold fact in final facts | Cost / 100 questions |
|---|---|---|---|---|
| B · the guide alone | 46.7, 1.5 | 48 / 47 / 45 | 60.7 | $0.036 |
| E · the guide + working memory (C v2) | 46.7, 2.9 | 50 / 45 / 45 | 55.7 | $0.079 |

Working memory adds nothing on top of the guide: the same mean, a wider spread, about twice the cost. Gold in the final
facts falls (55.7 vs 60.7) because only the facts the steps cite reach the final call, as in test 05. Spend $0.373
(E $0.237, B $0.109, Haiku check $0.027).

## Decision

**B is kept: the T-REx structure guide becomes GRAFT's default on top of mode C** (11 points over A on Haiku). C and D
are not adopted: T-REx as part of the graph hurts in any role tried (test 04 and here). Next: B on Qwen, the model the
system ships with, and which of B's two parts carries the gain (linking only, planning only; about $0.10 each).

## Revisions

- 2026-11-21: run-03, arm E (guide + working memory) 46.7 vs the guide alone 46.7 the same day: not kept.
- 2026-11-21: run-02, same-day A vs B confirmation (+12.0); the guide is GRAFT's default (user).
- 2026-11-21: run-01 paid arms done; B kept, C and D not adopted.
- 2026-11-21: design approved (user); arm D added (user); guide built from the raw T-REx parquet after the 45-property
  base covered too few question relations; revision threshold raised to 0.92 after the dry check; arm C reran with
  200 GB after running out of memory at 64 GB ($0); arm D started in parallel with C (user).
