# Test 05 · Working memory in the graph

| Test | Date | Status | Current run |
|---|---|---|---|
| 05 | 2026-11-20 | running | [run-01](runs/run-01/) |

## Question

Does answering in steps, with the question, sub-steps, notes and partial results written into the graph and read back, beat one-shot GRAFT, and does writing to the graph matter or only answering in steps?

## Setup

Design: [docs/design/graft_working_memory_design.md](../../docs/design/graft_working_memory_design.md). Arms A (mode C), B (question layer), C (working memory), C- (same steps, nothing written to the graph). Haiku, 3 repeats, empty-start graph first, then full T-REx. Starts after the fixed T-REx run (user, 2026-11-20).

## Result

run-01, empty-start document graph, Haiku, 3 repeats per arm ([table.csv](table.csv), built by `make_table.py` from the runs):

| Arm | Accuracy (mean, SD) | Per repeat | Gold fact in final facts | Calls / question | Cost / 100 questions |
|---|---|---|---|---|---|
| A · mode C | [34.7](table.csv), 0.6 | 35 / 34 / 35 | 50.7 | 1.0 | $0.027 |
| B · question layer | [33.7](table.csv), 0.6 | 34 / 33 / 34 | 49.0 | 2.0 | $0.037 |
| C · working memory in the graph | [35.3](table.csv), 1.2 | 34 / 36 / 36 | 43.0 | 4.5 | $0.077 |
| C- · same steps, prompt only | [32.7](table.csv), 1.2 | 34 / 32 / 32 | 41.7 | 4.5 | $0.078 |

C beats A by 0.6, inside the repeat spread, so by the rule it is not kept; C beats C- by 2.6, so writing the work into
the graph helps over keeping it in the prompt. Traced by hand (repeat 0): C wins where the documents' edited chain has
to be followed hop by hop (q30 Dave Matthews Band -> rock music -> Spain; q48, four hops to "Spanish"; q82, three hops
to "Riyadh Region"), where A gives up or answers from world knowledge. C loses where a step takes the older of two
conflicting facts (q62, q67: the step prompt never said the newer fact wins, the benchmark's answer prompt does) and
where the plan splits one entity into two edges (q41, "directed and managed"). Gold in the final facts is lower for C
(43 vs 51) because only the cited facts reach the final call. Each arm's working memory is logged per question
(`runs/run-01/*/repeat_*/memory/working_memory.jsonl`). Spend: $0.66 for all four arms.

run-02 (pending): C and C- with step prompt v2, which adds that the newer fact wins.

## Decision

Kept only if C beats A by more than its repeat spread and beats C-.

## Revisions

- 2026-11-21: arm A (34.7) vs test 01's mode C (38) checked: same code path, config, graph, prompt, grader and model; run-to-run noise in retrieval and answers ([baseline_check.md](baseline_check.md)).

- 2026-11-20: test folder created from the existing runs and the Flotilla run log.
- 2026-11-20: run-01 (four arms, 3 repeats). Step prompt v2 (newer fact wins) for run-02, from the run-01 traces.
