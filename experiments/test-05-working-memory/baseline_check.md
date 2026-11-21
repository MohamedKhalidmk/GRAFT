# Why arm A scored 34.7 when mode C scored 38 before

The question: test 01's mode C run scored 38 on 2026-11-13; test 05 arm A, the same mode on the same graph, scored 35 / 34 / 35
on 2026-11-20. What differs?

| | 38 run | Arm A |
|---|---|---|
| Run folder (Fir, $SCRATCH/sgar/results/runs) | exp_c_real_mh_262k_ans256_20261113-115012 | exp_wm_empty_a_modec_20261120-192124 |
| Job | 3845944 | 4762065 |
| Code | uncommitted at run time (11:50), committed as 28d4fd5 at 12:22 the same day | 8b7f424 (18:49, run at 19:21) |
| Config | configs/runs/exp/c_real_mh_262k_ans256.yaml | configs/runs/exp/wm/a_modec_empty.yaml |
| method_config.json | identical except work_dir | |
| Graph | real_mh_262k_empty_start.json: 10,839 entities, 18,088 facts, 5,994 supersedes edges | the same file and the same counts |
| Questions and answer prompt | task.json byte-identical | |
| Prompt and grader code (eval/benchmark.py) | unchanged between 28d4fd5 and 8b7f424 | |
| Grader result | rescoring the 38 run's answers with today's grader gives 38 again | |
| Haiku | requested and returned claude-haiku-5-5 on all 100 calls | the same on all 300 calls |
| Repeats | 1 | 3 |
| Gold fact in the final facts | 51% | 50.7% |
| Output tokens per answer | 63 | 65 |

What changed in the code between the two commits does not touch this path's prompt or grader: the method was renamed from
sgar to graft, the gateway gained a local (vLLM) mode, the runner can resume, and retrieval gained new options (question layer,
base graphs, a PageRank stop rule that only changes graphs over 100,000 nodes; this graph has about 29,000) that mode C does
not use.

**The difference is run-to-run noise, from two sources:**

1. **Retrieval is not deterministic.** For the same question, two arm A repeats share only 84% of their 50 facts on average,
   and the same set for only 31 of 100 questions; the order differs for 99. The 38 run against arm A repeat 0 looks the same
   (83% shared, same set for 30). So the 38 run's facts are a draw from the same spread, not a different method.
2. **Haiku's answers vary.** Of the 38 run's right answers, only 2 (q13, q80) are wrong in all three arm A repeats, and arm A
   gets 2 to 4 questions right in each repeat that the 38 run missed.

A single run at 38 against three runs at 34 to 35 fits that spread. The baseline for comparisons is arm A's 34.7, run with the
same code as the arms it is compared with. The nondeterministic retrieval is worth fixing (seeded GOAt and stable ordering) so
that repeats measure the model, not the walk.
