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

   The gateway cannot fix Haiku's sampling: the API rejects temperature and other sampling parameters since 2026-10-21
   (baselines/claude_llm.py). 13 questions flip between right and wrong across arm A's three repeats, which gives a spread of
   about 1.8 points per run. In the four questions that differ most (q13, q80, q21, q49) the gold fact was in the pool in
   both runs, and the only difference was whether Haiku picked the newer serial.

A single run at 38 against three runs at 34 to 35 fits that spread (about 1.8 SD above the mean). A second, independent check
from the other session found the same thing (fact-set Jaccard between repeats 0.770 to 0.778, old run vs repeats 0.764 to
0.774; no scorer commits since Sep 25).

For Haiku vs Qwen: compare 3 or more repeats each and report mean and range. Qwen runs greedy (temperature 0 on vLLM), so its
repeats vary only through retrieval; a smaller spread there is not a quality difference. The cleanest comparison gives both
models the same retrieved facts per question (save one retrieval pass, answer it with each model). The baseline for comparisons is arm A's 34.7, run with the
same code as the arms it is compared with. The nondeterministic retrieval is worth fixing (seeded GOAt and stable ordering) so
that repeats measure the model, not the walk.

## Rerun on 2026-11-21 (user: the old modes all scored 37-38, so check the code)

Three Haiku runs on the same day, 3 repeats each, same 100 questions, same graph:

| Run | Per repeat | Mean |
|---|---|---|
| The 2026-11-13 commit (28d4fd5), its config unchanged except 3 repeats (Fir 4828272) | 36 / 36 / 36 | 36.0 |
| Today's code, arm A config (Fir 4826810) | 36 / 33 / 35 | 34.7 |
| Today's Haiku re-answering the exact facts the 2026-11-13 run retrieved, no retrieval at all (replay_retrieved, Fir 4826810) | 34 / 36 / 33 | 34.3 |
| For reference: the 2026-11-13 run itself | 38 | 38 |

**The drop came from outside the code.** Given the very facts that scored 38 on 2026-11-13, with the same prompt, today's Haiku
scores 34.3. The model alias is the same (claude-haiku-5-5 requested and returned), so Haiku's behaviour behind the alias has
changed, or 2026-11-13 was a good day for it; either way the code cannot cause a drop on identical inputs.

Old code against today's code, on the same day: 36.0 vs 34.7, a 1.3-point gap inside today's spread (33 to 36; 12 to 17
answers flip between repeats of each run, and the old code's retrieval also varies run to run: identical for 1 of 100
questions, so its three 36s are a coincidence). Not significant with 3 repeats each, so no code change is reverted.

**Haiku's best setup stays mode C as in arm A**, and the Qwen run on that setup was released (Fir 4823564). Spend $0.244.
