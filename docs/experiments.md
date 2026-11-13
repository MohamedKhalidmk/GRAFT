# SGAR experiments: read order (A, B, C) and starting graph (D)

All runs use FactConsolidation from MemoryAgentBench at 262K tokens (537 chunks of 512 tokens),
the same GNN checkpoint (`results/checkpoints/gnn_bge_400w`, BAAI/bge-small-en-v1.5 embeddings),
and the same budget: at most **50 facts** handed to the answering model. Only public benchmark data
is used, on the Mac or on Fir.

## What each experiment changes

| | Write | Read |
|---|---|---|
| **A** (current method) | LLM writer, empty start | PPR picks the 400 most relevant nodes → GNN scores them → GOAt's key facts first, then the GNN's ranking |
| **B** | same as A | GNN + GOAt first on a region chosen **without PPR** → PPR from GOAt's picks over the whole graph |
| **C** | same as A | PPR cuts to 400 nodes → GNN + GOAt → a short second PPR from GOAt's picks, inside those 400 nodes |
| **D** (ablation) | LLM **extends a ready-made graph** (the *synthetic starting graph*) vs LLM builds from scratch (A) | same as A |

Shared details:

- B and C rank: GOAt-picked facts first (by GOAt importance), then the other facts by the second
  PPR's score, then the GNN's ranking to fill the budget. The second PPR uses restart 0.5 (PageRank
  damping 0.5, as HippoRAG 2), seeded with GOAt's picked nodes weighted by their importance.
- B's region: GOAt explains every node it is given, so it cannot be assumed to scale to the whole
  graph (about 29,000 nodes). It was timed on the full graph first (below). If too slow, B uses the
  400 nodes nearest the question's entities by hop count (`nearest_nodes`), still with no PPR.
- Every variant keeps the latest-version rule: each fact is swapped for its newest version
  (following SUPERSEDES) before the budget cut.
- Code: `my_method/retrieval.py` modes `gnn_goat` (A), `goat_ppr` (B), `ppr_goat_ppr` (C);
  `start_graph: synthetic` for D (`my_method/gnn/data_synthetic.py::synthetic_start_graph`,
  `my_method/writer.py::graph_pattern`). Configs: `configs/runs/exp/`.

### The synthetic starting graph (D)

Made up for now, labelled **synthetic starting graph** everywhere. It is one generated world from the
GNN's training-data generator: invented syllable names (no benchmark entity can appear), the 37
relation labels of the schema, 150 entities, 400 facts, about 20% of them revised (SUPERSEDES).
In D the writer starts from this graph and its extraction prompt adds: *"The memory graph already
exists; you only extend it. Follow its pattern"*, with the graph's relation labels and six stored
facts. The from-scratch arm is variant A's graph build.

## Two kinds of measurement

- **Fake mode** (free): no API calls. The writer is played by a rule parser and the answer is not
  real, so the number reported is **answer reached the model**: does a gold answer appear in the
  facts handed to the model? This isolates retrieval.
- **Real run** (paid): Claude Haiku 5.5 writes the graph and answers. Reported: the benchmark's own
  score (substring exact match), answer reached the model, tokens and cost per question.

## Results

### GOAt on the whole graph (decides B's region)

One MH question (73), the whole 262K graph (about 29,000 nodes), Fir, one H100 + 8 CPU cores:
**not finished after 67 minutes** (6 h 40 min of CPU time), 4.8 GB of memory. Cancelled and
counted as a loss. GOAt's `gcn_explain` loops over every node in Python on the CPU, so the GPU
does not help. At over an hour per question, 100 questions would take more than four days.
**B therefore uses the 400 nodes nearest the question's entities (no PPR).**

### A, B, C in fake mode (free)

Fir job 3782158 (one H100 for embeddings, 8 CPU workers for GNN + GOAt), 2026-11-13, 39 min for
all three. All three read the **same graph** (rule-played writer: 10,821 entities, 18,326 facts,
7,227 SUPERSEDES edges). Metric: answer reached the model, of 100 questions per split, 50 facts.

| Variant | SH | MH | Tokens / question | Retrieval time / question |
|---|---|---|---|---|
| A · PPR → GNN + GOAt (current) | 98 | 57 | 1,399 | 1.85 s |
| B · GNN + GOAt (400 nearest) → PPR | 98 | 58 | 1,406 | 2.64 s |
| C · PPR → GNN + GOAt → short PPR | **99** | **60** | 1,401 | 1.84 s |

A reproduces the earlier run (57 on MH, 2026-10-30). Question by question against A:

| | SH gained / lost | MH gained / lost |
|---|---|---|
| B | 0 / 0 | 6 / 5 |
| C | 1 / 0 | 6 / 3 |

**What it means.** Expanding from GOAt's picks with a short PPR walk (C) helps a little: +3 on MH,
+1 on SH, at the same token cost and speed. Putting GNN + GOAt first (B) changes which questions
are answered (6 gained, 5 lost) but not how many: without PPR, the 400 nearest nodes fill up with
a hub's neighbours, which is why A used PPR for the region in the first place. These differences
are 1–3 questions out of 100, inside run-to-run noise for one repeat; the real run below is the
check that matters. The writer here is a rule parser, so these numbers say nothing about
experiment D.

### Real run: A, B, C, BM25 and D on FC-MH (Claude Haiku 5.5)

Fir job 3787840, 2026-11-13, 3 h 50 min, cost guard capped at $15. **Total spend: $2.27.**
Claude Haiku 5.5 wrote the graph once from an empty start (1,066 writer calls, 87 min, $1.04).
A, B and C read that **same graph** (10,839 entities, 18,088 facts, 5,994 SUPERSEDES edges).
D wrote its own graph starting from the synthetic starting graph (1,064 calls, 88 min, $1.04;
10,869 entities, 18,022 facts, 5,930 SUPERSEDES edges). 100 MH questions, 50 facts, answer capped
at 16 tokens (the benchmark's setting).

| Variant | Score (substring exact match) | Answer reached the model | Tokens / question | Answer cost / question | Answers cut off at 16 tokens |
|---|---|---|---|---|---|
| A · PPR → GNN + GOAt (current) | 15 | 51 | 2,395 | $0.00024 | 65 |
| B · GNN + GOAt (400 nearest) → PPR | 13 | 51 | 2,397 | $0.00024 | 66 |
| C · PPR → GNN + GOAt → short PPR | 17 | 51 | 2,388 | $0.00024 | 58 |
| D · extends the synthetic starting graph (read as A) | **22** | 44 | 2,393 | $0.00024 | 49 |
| BM25 (top chunks) | 1 | 32 | 9,363 | $0.00094 | 84 |

Graph building is a one-time cost on top: $1.04 for A's graph (shared by A, B, C) and $1.04 for D's,
about $0.01 per question over these 100.

**The 16-token cap dominates the score.** The benchmark's prompt asks for "a very concise answer",
but Haiku 5.5 often starts with "Based on the knowledge pool, …" or "Let me trace this", and is cut
off before the answer. **No cut-off answer scored in any run**: every correct answer came from the
35–51 answers the model finished. So all scores are low, and they partly measure how often the
model answers directly rather than retrieval. The cap is the same for every row, so the comparison
is fair, but the absolute numbers understate every method.

**What it means.**

- **Read order (A, B, C).** All three hand the gold answer to the model in 51 of 100 questions, the
  so on this graph the read order changes which facts reach the model more than how many. C scores best of the three
  (17 vs 15 vs 13), in the same order as fake mode, but 2–4 questions is within noise for one repeat.
- **D, extend vs from scratch.** Extending the synthetic starting graph scored 22 vs A's 15 at the
  same cost, but the gold answer reached the model *less* often (44 vs 51). The gain comes from
  fewer cut-off answers (49 vs 65), not from better retrieval, so this run does not show that a
  starting graph helps retrieval. The writer kept the same shape either way (about 12,000 current
  facts, about 5,900 revisions).
- **BM25.** Raw chunks put the answer in front of the model 32 times but the model almost never
  answered within 16 tokens (84 cut off, 1 correct), at four times SGAR's tokens. SGAR's short facts
  are both cheaper and easier for the model to answer from.

Run folders on Fir: `~/scratch/sgar/results/runs/exp_{a,b,c,bm25,d_extend}_real_mh_262k_*`.

### Re-answer with a 256-token limit

To see past the cut-off, the same five runs were answered again with `answer_max_tokens: 256`
(configs `configs/runs/exp/*_ans256.yaml`). Nothing else changed: the same saved graphs (A, B, C
share one; D loads its own), the same retrieval, the same benchmark prompt. Fir job 3845944,
2026-11-13, 45 min, **$0.21**. Total paid spend for all real runs: **$2.47**.

Because a longer answer can mention the gold entity while reasoning and still end on a wrong one,
a stricter score was also computed: the gold answer must appear in the **final line** of the
answer (after "Answer:").

| Variant | Score, 16 tokens | **Score, 256 tokens** | Strict (final line), 256 | Answer reached the model | Tokens / question | Answer cost / question | Cut off at 256 |
|---|---|---|---|---|---|---|---|
| A · PPR → GNN + GOAt (current) | 15 | **37** | 36 | 51 | 2,455 | $0.00027 | 0 |
| B · GNN + GOAt (400 nearest) → PPR | 13 | **37** | 33 | 51 | 2,452 | $0.00027 | 0 |
| C · PPR → GNN + GOAt → short PPR | 17 | **38** | 36 | 51 | 2,439 | $0.00027 | 1 |
| D · extends the synthetic starting graph | 22 | **37** | 36 | 44 | 2,443 | $0.00027 | 0 |
| BM25 (top chunks) | 1 | **4** | 4 | 32 | 9,444 | $0.00098 | 4 |

**What it means.**

- With room to answer, every SGAR variant scores 37–38, more than double the 16-token scores. The
  strict score is within 1–4 of it, so the gain is real answers, not lucky mentions.
- **Read order (A, B, C) and starting graph (D) do not differ** once answers are not cut off. The
  16-token gaps (13 to 22) came from how often the answer was cut off, not from retrieval. C's
  small edge in fake mode and at 16 tokens shrinks to one question.
- **Retrieval is now the limit.** When the gold answer reaches the model, it answers right about
  73% of the time (37 of 51 for A). But the answer reaches the model in only 51 of 100 questions
  (44 for D). Raising that number is where the next gain is.
- BM25 stays far behind (4) at four times the tokens: raw 512-token chunks hold the right fact 32
  times, but the model rarely resolves it from them.

Run folders on Fir: `~/scratch/sgar/results/runs/exp_*_real_mh_262k_ans256_*`.

### HippoRAG 2 baseline, real run (same conditions)

Run on the Mac on 2026-11-13 with the same model (Claude Haiku 5.5), embedding model (bge-small),
100 MH questions, top 10 passages and answer limits (16 and 256 tokens). It uses the benchmark's bundled
HippoRAG copy, with its answer capped like every other method (`cap_answer`). Configs:
`configs/runs/exp/hipporag_real_mh_262k*.yaml`. Raw answers: `results/real_run/hipporag_*`.

| | 16 tokens | 256 tokens | Tokens / question | Answers cut off (16 / 256) |
|---|---|---|---|---|
| HippoRAG 2 | 0 | **15** (strict 14) | about 5,700 | 97 / 49 |
| GRAFT A, B, C | 13–17 | **37–38** | about 2,450 | 58–66 / 0–1 |
| BM25 | 1 | 4 | about 9,400 | 84 / 4 |

**Beside the paper** (MemoryAgentBench Table 3, FC-MH): HippoRAG 2 gets 5 and BM25 gets 3 there.
Our 0 at 16 tokens is not comparable: the paper never capped HippoRAG's answer (up to 2,048 tokens),
and its answer prompt writes "Thought:" first, so 16 tokens never reach the answer. Our 15 at 256
tokens is higher than the paper's 5 mainly because of the model (Claude Haiku 5.5 vs GPT-4o-mini; in
the paper's own table GPT-5-mini gets 28 on MH while most GPT-4o-mini methods get 2 to 7), despite a
much smaller embedding model (bge-small vs NV-Embed-v2) and 49 answers still cut off at 256 tokens.
One run of 100 questions is about ±4. The fair comparison is across our own rows.

**What it took to run HippoRAG with Claude** (details in `results/real_run/README.md`): its extraction
calls use Claude's structured output (Claude otherwise answered the dialogue-shaped chunks
conversationally and the index came out empty); a graph-search crash falls back to HippoRAG's own
dense retrieval (not needed in the final runs); and on the Mac the gateway now embeds on the CPU
(Apple's GPU returned NaN and wrong vectors). HippoRAG cost $1.30 in all, failed attempts included;
all real runs together cost **$3.77**.
