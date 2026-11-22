# Test 08 run-02: every arm on Qwen at 1,024-token answers (2026-11-22, Nibi 3g.40gb slices)

FactConsolidation multi-hop 262k, 100 questions, the Haiku-built graph (2026-11-13), Qwen3.8-27B W4A16 answering with a
1,024-token cap (run-01 used 256 and cut 26-35% of the one-call arms' answers). 3 repeats per arm, all the same day.

| Arm | ID | Right per repeat (of 100) | Mean | Gold in facts shown | Qwen calls per question | Answers cut at 1,024 tokens |
|---|---|---|---|---|---|---|
| A, mode C | G08 | 44, 44, 44 | 44.0 | 51% | 1 | 28-30 |
| B, the guide | G35 | 48, 48, 49 | 48.3 | 59% | 2.0 | 21-25 |
| C v2, working memory in the graph | G33 | 33, 35, 34 | 34.0 | 40% | 4.6 | 0 |
| C- v2, working memory in the prompt | G34 | 32, 33, 33 | 32.7 | 38-39% | 4.6 | 0 |
| E, the guide + working memory | G38 | 47, 46, 47 | 46.7 | 53% | 4.6 | 0 |

Jobs: A Nibi 28366750, 28366764, 28366766; B 28366767, 28366768, 28448320; C v2 28366770, 28448417, 28448434; C- v2
28366840, 28366859, 28448436; E 28448439, 28366866, 28366871. Excluded (no scores, killed by the port-8000 clash on
shared nodes): 28366769, 28366790, 28366805, 28366862, 28366864; each was rerun with a free port (GRAFT eeeb995).

Reading: at 1,024 tokens mode C rises from 39.3 (run-01, 256 tokens) to 44.0, the guide from 47.0 to 48.3, and the
guide stays ahead of mode C by 4.3 points. Working memory stays well below mode C on Qwen (34.0 and 32.7). The guide
with working memory (E, 46.7) is 1.6 below the guide alone, with 2.3 times the calls: G38 stays parked, as decided after
test 06. The guide remains GRAFT's default on Qwen.
