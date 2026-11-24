# Test 05 · Working memory in the graph

| Test | Date | Status | Current run |
|---|---|---|---|
| 05 | 2026-11-21 | done on Haiku (Qwen pending) | [run-02](runs/run-02) |

## Candidates and setups

IDs from the [registry](../../docs/reference/REGISTRY.md) (frozen 2026-11-21). A candidate is the method, a setup is the candidate plus model,
answer cap, benchmark and scoring; old run folders keep their names.

| Candidate | Setup | Row in this test |
|---|---|---|
| G08 | S17 | mode C, one answer call |
| G30 | S55 | question layer |
| G31 | S56 | working memory in the graph |
| G32 | S58 | same steps, prompt only |
| G33 | S59 | C, step prompt with the newer-fact rule |
| G34 | S62 | C-, same prompt |

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

run-02, step prompt v2 (the newer fact wins), with arm A rerun the same day (Fir 4827601, 4827603, 4826810):

| Arm | Accuracy (mean, SD) | Per repeat | Gold fact in final facts | Cost / 100 questions |
|---|---|---|---|---|
| A · mode C, rerun the same day | 34.7, 1.5 | 36 / 33 / 35 | 50.3 | $0.027 |
| C v2 · working memory in the graph | 35.7, 2.1 | 38 / 34 / 35 | 45.3 | $0.080 |
| C- v2 · same steps, prompt only | 33.0, 0.0 | 33 / 33 / 33 | 41.3 | $0.081 |

The newer-fact rule moves C up by 0.4 (35.3 to 35.7) and C- by 0.3: both inside the spread. C v2 beats A by 1.0 with an
SD of 2.1, so by the rule it is not kept. C beats C- again (by 2.7), in both rounds: when the work is done in steps,
writing it into the graph is what helps. Spend $0.49 (C v2 $0.240, C- v2 $0.243).

## Decision

Not kept on Haiku: working memory in the graph is at most about 1 point above mode C in two rounds, inside the repeat spread, for about three times the cost per question. It does beat the prompt-only version by 2.6 to 2.7 in both rounds, so writing to the graph is the useful part if steps are used. The same three arms run on Qwen (Fir 4823564), since Qwen is the model the system ships with.

## Revisions

- 2026-11-21: run-02 (step prompt v2) and the same-day arm A rerun; decision on Haiku: not kept.
- 2026-11-21: arm A (34.7) vs test 01's mode C (38) checked: same code path, config, graph, prompt, grader and model; run-to-run noise in retrieval and answers ([baseline_check.md](../test-07-haiku-drift/baseline_check.md)).

- 2026-11-20: test folder created from the existing runs and the Flotilla run log.
- 2026-11-20: run-01 (four arms, 3 repeats). Step prompt v2 (newer fact wins) for run-02, from the run-01 traces.
