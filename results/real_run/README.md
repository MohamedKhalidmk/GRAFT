# Real run: Claude Haiku 5.5 on FactConsolidation multi-hop

Raw results of the paid real runs written up in [`docs/experiments.md`](../../docs/experiments.md).
FactConsolidation from MemoryAgentBench, 262K tokens (537 chunks of 512 tokens), the 100 multi-hop
(MH) questions. Claude Haiku 5.5 (`claude-haiku-5-5`) writes the memory graph and answers. Public
benchmark data only. Run on the Fir cluster (one H100, 8 CPU cores) on 2026-11-13.

## Slurm jobs

| Job | What | Runs | API cost |
|---|---|---|---|
| **3787840** | Answer limit **16 tokens** (the benchmark's setting). Builds both graphs. | A, B, C, BM25, D | $2.27 |
| **3845944** | Same runs answered again with a **256-token** limit. Reuses the saved graphs, nothing rebuilt. | A, B, C, D, BM25 | $0.21 |

Both jobs ran under a cost guard (`scripts/fir/run_real_guarded.sbatch`) that stops every run past
a cap. Total: **$2.47**.

## Variants

| Folder prefix | Variant |
|---|---|
| `a_` | A · PPR picks 400 nodes → GNN + GOAt (the current method). Writer starts from an empty graph. |
| `b_` | B · GNN + GOAt on the 400 nodes nearest the question's entities → PPR from GOAt's picks. Same graph as A. |
| `c_` | C · PPR picks 400 nodes → GNN + GOAt → short PPR from GOAt's picks. Same graph as A. |
| `d_extend_` | D · the writer extends a *synthetic starting graph* instead of starting empty. Read as A. Own graph. |
| `bm25_` | BM25 baseline: top 512-token chunks handed straight to the model. |

Suffix `_16tok` or `_256tok` is the answer limit. All SGAR variants hand at most 50 facts to the model
and use the same GNN checkpoint (`gnn_bge_400w`, BAAI/bge-small-en-v1.5 embeddings).

## Files

Each run folder holds:

- `scored.jsonl`: one line per question: question id, gold answers, the model's full answer, stop
  reason, every score (substring exact match, exact match, F1, ROUGE), whether the gold answer was in
  the retrieved facts, and the retrieved text itself.
- `summary.json`: the run's totals (score, answer reached the model, tokens, cost, timing).
- `usage.jsonl`: every API call with input and output tokens, cost and latency.
- `build.json`: graph size and the writer's operations (ADD, MERGE, SUPERSEDE, IGNORE).
- `config.yaml`: the exact config the run used.

At the top level: `summary.csv` and `summary.md` (both tables below), and `configs/`, the ten run
configs as committed in `configs/runs/exp/`. The memory graphs, caches and checkpoints are not in
git; they stay on Fir under `~/scratch/sgar/`.

## Results

Score = the benchmark's substring exact match, of 100. *Strict* = the gold answer must be in the
answer's final line, so a longer answer can't score by mentioning it while reasoning.

| Variant | Score, 16 tokens | Score, 256 tokens | Strict, 256 | Answer reached the model | Tokens / question (256) |
|---|---|---|---|---|---|
| A · PPR → GNN + GOAt | 15 | 37 | 36 | 51 | 2,455 |
| B · GNN + GOAt → PPR | 13 | 37 | 33 | 51 | 2,452 |
| C · PPR → GNN + GOAt → short PPR | 17 | 38 | 36 | 51 | 2,439 |
| D · extends synthetic starting graph | 22 | 37 | 36 | 44 | 2,443 |
| BM25 | 1 | 4 | 4 | 32 | 9,444 |

At 16 tokens Haiku often starts with "Based on the knowledge pool…" and is cut off before the answer
(49 to 84 answers per run); no cut-off answer scored. With 256 tokens almost nothing is cut off. Full
tables, with cut-offs and costs, are in [`summary.md`](summary.md).
