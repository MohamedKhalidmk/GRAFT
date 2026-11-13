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

HippoRAG 2 ran later the same day on the Mac (`scripts/run_real_guarded_local.py`, $3 cap), with the
same model, embedding model, questions and answer limits. Final runs: `20261113-142733` (16 tokens)
and `20261113-142941` (256 tokens), both reusing one HippoRAG index built at 13:15 for $0.58
(`hipporag_index_build/`). HippoRAG 2 cost **$1.30** in all, including five failed attempts (below),
so the real runs together cost **$3.77**.

A third HippoRAG 2 run gave its answers up to **2,048 tokens** (`hipporag_2048tok`, run `20261113-145119`, $0.07), as the paper did. No answer was cut off (longest 412 tokens) and it scored **14** (strict 14), the same as 15 at 256 tokens within noise. So the 256-token limit was not what held HippoRAG back. With it, all real runs cost **$3.84**.

## Variants

| Folder prefix | Variant |
|---|---|
| `a_` | A · PPR picks 400 nodes → GNN + GOAt (the current method). Writer starts from an empty graph. |
| `b_` | B · GNN + GOAt on the 400 nodes nearest the question's entities → PPR from GOAt's picks. Same graph as A. |
| `c_` | C · PPR picks 400 nodes → GNN + GOAt → short PPR from GOAt's picks. Same graph as A. |
| `d_extend_` | D · the writer extends a *synthetic starting graph* instead of starting empty. Read as A. Own graph. |
| `hipporag_` | HippoRAG 2, the benchmark's bundled copy: top 10 passages, its own answer prompt, capped at the run's answer limit. |
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
| HippoRAG 2 | 0 | 15 (2,048 tok: 14) | 14 | not recorded | 5,653 |
| BM25 | 1 | 4 | 4 | 32 | 9,444 |

At 16 tokens Haiku often starts with "Based on the knowledge pool…" and is cut off before the answer
(49 to 84 answers per run); no cut-off answer scored. With 256 tokens almost nothing is cut off. Full
tables, with cut-offs and costs, are in [`summary.md`](summary.md).

## HippoRAG 2: what it took to run with Claude

The benchmark's HippoRAG copy was written for GPT-4o-mini. Four things had to be handled (code in
`baselines/hipporag/agent.py` and `baselines/claude_gateway/`); HippoRAG's prompts were not changed.

1. **Extraction replies.** Every chunk is wrapped in the benchmark's "Dialogue between User and
   Assistant" text, and Claude answered it conversationally ("Understood. I've noted the facts...")
   instead of listing entities, so the index came out empty. HippoRAG's own config asks for JSON
   (`response_format`), but the bundled client never sends it, and a written JSON instruction was not
   enough. Its NER and triple calls now carry a strict JSON schema, which the gateway maps to Claude's
   structured output (`json_openie: schema`).
2. **Crash in graph search.** The bundled code stops the whole run when a question's node weights are
   all zero. Such questions fall back to HippoRAG's own dense passage retrieval; none of the final 200
   answers needed it (`graph_fallback` in each prediction).
3. **Embeddings on the Mac.** The gateway's bge-small model on Apple's GPU returned NaN or wrong
   vectors (922 NaN entity vectors, about a third of entities wrong), so every passage scored NaN. On
   macOS the gateway now embeds on the CPU, one batch at a time, and rejects NaN vectors; the saved
   index was re-embedded on the CPU. The Fir runs (CUDA) were not affected.
4. **Answer limit.** HippoRAG's answer prompt writes "Thought: ..." before "Answer: ...". At 16 tokens
   every answer is cut off (0); at 256, 49 of 100 still are. The paper ran HippoRAG with no cap
   (up to 2,048 tokens) and GPT-4o-mini, and reports 5 on FC-MH.

Failed attempts (all on 2026-11-13, kept out of this folder): 12:57 empty index ($0.42), 13:09
stopped after 105 calls ($0.02), 13:15 index built but crashed in graph search ($0.58 + $0.02), 13:29
NaN embeddings ($0.13), 14:12 network outage ($0).
