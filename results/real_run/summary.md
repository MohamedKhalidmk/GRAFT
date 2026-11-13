# Real-run summary tables

Generated from the per-question files in this folder. Score = the benchmark's substring exact match, of 100 multi-hop questions.

### Answer limit 16 tokens (Slurm job 3787840)

| Variant | Score | Strict (final line) | Answer reached the model | Cut off | Tokens / question | Answer cost / question | Run cost |
|---|---|---|---|---|---|---|---|
| A · PPR → GNN + GOAt (current) | 15 | 15 | 51 | 65 | 2,395 | $0.000245 | $1.0599 |
| B · GNN + GOAt (400 nearest) → PPR | 13 | 13 | 51 | 66 | 2,397 | $0.000245 | $0.0245 |
| C · PPR → GNN + GOAt → short PPR | 17 | 17 | 51 | 58 | 2,388 | $0.000244 | $0.0244 |
| D · extends the synthetic starting graph | 22 | 22 | 44 | 49 | 2,393 | $0.000244 | $1.0642 |
| BM25 (top chunks) | 1 | 1 | 32 | 84 | 9,363 | $0.000942 | $0.0942 |

### Answer limit 256 tokens (Slurm job 3845944)

| Variant | Score | Strict (final line) | Answer reached the model | Cut off | Tokens / question | Answer cost / question | Run cost |
|---|---|---|---|---|---|---|---|
| A · PPR → GNN + GOAt (current) | 37 | 36 | 51 | 0 | 2,455 | $0.000275 | $0.0275 |
| B · GNN + GOAt (400 nearest) → PPR | 37 | 33 | 51 | 0 | 2,452 | $0.000272 | $0.0272 |
| C · PPR → GNN + GOAt → short PPR | 38 | 36 | 51 | 1 | 2,439 | $0.000269 | $0.0269 |
| D · extends the synthetic starting graph | 37 | 36 | 44 | 0 | 2,443 | $0.000269 | $0.0269 |
| BM25 (top chunks) | 4 | 4 | 32 | 4 | 9,444 | $0.000982 | $0.0982 |

Total API spend for these 10 runs: **$2.47**.
