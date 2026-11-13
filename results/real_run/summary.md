# Real-run summary tables

Generated from the per-question files in this folder. Score = the benchmark's substring exact match, of 100 multi-hop questions.

### Answer limit 16 tokens (Slurm job 3787840; HippoRAG 2 ran on the Mac)

| Variant | Score | Strict (final line) | Answer reached the model | Cut off | Tokens / question | Answer cost / question | Run cost |
|---|---|---|---|---|---|---|---|
| A · PPR → GNN + GOAt (current) | 15 | 15 | 51 | 65 | 2,395 | $0.000245 | $1.0599 |
| B · GNN + GOAt (400 nearest) → PPR | 13 | 13 | 51 | 66 | 2,397 | $0.000245 | $0.0245 |
| C · PPR → GNN + GOAt → short PPR | 17 | 17 | 51 | 58 | 2,388 | $0.000244 | $0.0244 |
| D · extends the synthetic starting graph | 22 | 22 | 44 | 49 | 2,393 | $0.000244 | $1.0642 |
| HippoRAG 2 (benchmark copy, top 10 passages) | 0 | 0 |  | 97 | 5,822 | $0.000588 | $0.0588 |
| BM25 (top chunks) | 1 | 1 | 32 | 84 | 9,363 | $0.000942 | $0.0942 |

### Answer limit 256 tokens (Slurm job 3845944; HippoRAG 2 ran on the Mac)

| Variant | Score | Strict (final line) | Answer reached the model | Cut off | Tokens / question | Answer cost / question | Run cost |
|---|---|---|---|---|---|---|---|
| A · PPR → GNN + GOAt (current) | 37 | 36 | 51 | 0 | 2,455 | $0.000275 | $0.0275 |
| B · GNN + GOAt (400 nearest) → PPR | 37 | 33 | 51 | 0 | 2,452 | $0.000272 | $0.0272 |
| C · PPR → GNN + GOAt → short PPR | 38 | 36 | 51 | 1 | 2,439 | $0.000269 | $0.0269 |
| D · extends the synthetic starting graph | 37 | 36 | 44 | 0 | 2,443 | $0.000269 | $0.0269 |
| HippoRAG 2 (benchmark copy, top 10 passages) | 15 | 14 |  | 49 | 5,653 | $0.000648 | $0.0648 |
| BM25 (top chunks) | 4 | 4 | 32 | 4 | 9,444 | $0.000982 | $0.0982 |

### Answer limit 2048 tokens (HippoRAG 2 only, on the Mac; the paper did not cap HippoRAG)

| Variant | Score | Strict (final line) | Answer reached the model | Cut off | Tokens / question | Answer cost / question | Run cost |
|---|---|---|---|---|---|---|---|
| HippoRAG 2 (benchmark copy, top 10 passages) | 14 | 14 |  | 0 | 6,236 | $0.000723 | $0.0723 |

API spend for these 13 runs: **$2.67**. Not included: the HippoRAG 2 index build ($0.58, hipporag_index_build/) and the failed HippoRAG attempts (see README).

HippoRAG 2's 'cut off' counts answers that stopped exactly at the limit, from its API log (usage.jsonl), since its per-question rows do not carry the stop reason. 'Answer reached the model' is blank for HippoRAG 2: its retrieved passages are not recorded per question.
