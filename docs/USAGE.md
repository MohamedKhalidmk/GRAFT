# Using the GRAFT test bench

Setup, fake mode, the pipeline and the cluster jobs. The project overview and results are in the
[README](../README.md); every test is in [experiments/INDEX.md](../experiments/INDEX.md).

Revision-aware graph memory (GRAFT, ours) vs. memory systems from MemoryAgentBench, on the
Selective Forgetting task: FactConsolidation-SH and -MH. Every method answers with
**Claude Haiku 5.5** (`claude-haiku-5-5`) unless a config says otherwise (Qwen runs use `llm.mode: local`).
Results are laid out like the paper's Table 3, with the paper's own numbers as a separate reference block.

GRAFT was called SGAR during development. Files under `results/`, the cluster folders, the writer's
prompt headers (`SGAR-EXTRACT`, `SGAR-OPS`) and the benchmark agent name `Structure_rag_sgar` keep the
old name so the recorded runs stay reproducible; configs that say `method: sgar` still run.

- [docs/design/](design): designs before code. [docs/reference/experiments.md](reference/experiments.md): the full write-up of the
  read-order and baseline runs.

## Quick start

```bash
git clone --recurse-submodules <this repo> && cd GRAFT
bash scripts/setup_envs.sh                     # core .venv + one env per third-party baseline
.venv/bin/python -m data.paper_reference       # paper's Table 3 -> results/paper_table3.csv
.venv/bin/python -m my_method.gnn.train --source synthetic --out results/checkpoints/gnn_default
.venv/bin/streamlit run ui/app.py              # control panel
.venv/bin/python -m pytest tests -q            # offline tests (no API calls)
```

Real runs need `ANTHROPIC_API_KEY` in the environment of whatever starts them (never in a file).
Everything else, including every test, runs offline in **fake mode** (below).

## How it fits together

```
 eval/run.py ── builds the task from the benchmark ──> task.json (chunks + query prompts, no answers)
     │
     ├─ starts the Claude gateway (baselines/claude_gateway/server.py) on a free local port
     │      /v1/messages          Claude Messages API (our code, via the Anthropic SDK)
     │      /v1/chat/completions  OpenAI-style, translated to Claude (Mem0, Letta, HippoRAG)
     │      /v1/embeddings        the run's one shared embedding model
     │      every call -> usage.jsonl (phase, question, tokens, cost); --fake = scripted replies
     │
     ├─ starts the method in its own environment:  python -m <module> --task --config --out --gateway
     │      memorize(all chunks in order) -> build.json;  answer(each question) -> predictions.jsonl
     │
     └─ scores with the benchmark's metric, attributes tokens/cost -> scored.jsonl, summary.json
 eval/table.py ── latest run per method/variant ──> results/table_<length>_<mode>.{csv,md}
 eval/queue.py ── several configs in sequence (the UI and Slurm jobs use it)
```

- **Benchmark code is reused, not reimplemented.** `baselines/memoryagentbench` is the authors'
  repo as a git submodule (commit `5380260`, 2026-09-25), unmodified. Data loading, chunking,
  prompt templates and scoring are imported from it (`eval/benchmark.py`).
- **One memory for both splits.** SH and MH share the identical context at every length, so each
  method builds memory once and answers the 100 SH and 100 MH questions.
- **Gold answers never reach a method process.** Scoring happens in the runner.
- **Why a gateway.** Mem0, Letta and HippoRAG are written for OpenAI. Pointing their own OpenAI
  clients at the gateway keeps their code paths untouched, applies the same Claude settings to
  everyone (thinking off, no sampling parameters, which the API rejects since 2026-10-21), gives
  all of them the same embedding model, and logs every call's tokens and cost in one place.
- **Why separate environments.** The systems pin conflicting package versions
  (`scripts/setup/*.sh`; uv shares files between them, so disk use stays modest).

## Methods

| Key | Row | Family | Code | Notes |
|---|---|---|---|---|
| `long_context` | Claude Haiku 5.5 (1M, full history) | Long context | benchmark's long-context agent path | the "model alone" row; reads all ~262K tokens (Haiku 5.5 has 1M) |
| `long_context_128k` | Claude Haiku 5.5 (newest 128K) | Long context | same | keeps the newest 123,990 tokens, as the paper's GPT-4o-mini setting did |
| `bm25` | BM25 | Simple RAG | benchmark's BM25 path (LangChain BM25Retriever, top 10) | |
| `hipporag_bundled` / `_upstream` | HippoRAG-v2 | Structure-augmented | benchmark's copy (2.0.0a3) / PyPI 2.0.0a4 | NV-Embed-v2 option for Fir |
| `mem0_bundled` / `_upstream` | Mem0 | Structure-augmented | benchmark's copy (= mem0ai 0.1.88) / mem0ai 2.2.1 | 4096-token chunks, top 100, as the paper |
| `letta_bundled` / `_upstream` | MemGPT / Letta | Agentic | benchmark's copy (Letta 0.7.0) / Letta server 0.16.8 | current PyPI `letta` is Letta Code, not MemGPT |
| `total_agent_memory` | total-agent-memory (supersede) | Agentic, optional | benchmark's handler + PyPI 14.5.1 | supersede-style prior work |
| `knowl` | Knowl (supersede) | Agentic, optional | benchmark's handler + Knowl v5.6.0 | needs `scripts/setup/knowl.sh` (Node build) |
| `graft` | GRAFT (ours) | Ours | `my_method/` | variants below |

Each adapter's module docstring lists every deviation from the benchmark's handling of that
system. The common ones: Claude instead of GPT-4o-mini through the gateway; the shared embedding
model instead of OpenAI's (TAM and Knowl keep their own internal embedders, which define those
systems); all state inside the run's folder.

## GRAFT (`my_method/`)

| File | Role |
|---|---|
| `schema.yaml` / `schema.py` | the graph schema the writer must follow (Entity; Fact(subject, relation, object) with provenance; subject_of, object_of, SUPERSEDES). Swap the YAML for a FHIR schema later |
| `writer.py` | per chunk: Claude extracts schema facts, then picks ADD / MERGE / SUPERSEDE / IGNORE per fact against stored candidates (same subject). `RuleWriter`: template-parser ablation |
| `graph_store.py` | NetworkX graph saved as JSON (`<run>/repeat_k/memory/graph.json`); superseded facts are kept |
| `gnn/` | GOAt's GCN_NC (submodule `gnn/GOAt`, commit `1ef20f0`, unmodified), features, weak labels, training data, training, GOAt attribution |
| `retrieval.py` | entity linking -> PPR picks the 400 most relevant nodes in the whole graph -> GNN+GOAt / GNN top-k ranks them (or PPR alone) -> latest-version rule -> budget |
| `answer.py` | facts with provenance, in the benchmark's RAG prompt layout |
| `agent.py` | the method process |

Budget: 5120 tokens, what BM25 and HippoRAG hand the model (top 10 chunks of 512 tokens). PPR runs over
the whole graph, as HippoRAG does. The GNN modes score the 400 nodes PPR ranks highest (see the change
log); `retrieval_workers` retrieves in parallel, which is what makes GOAt fast on a cluster.

Toggles (UI or `method_config`): `writer` llm/rule, `schema` fixed/free, `revisions` on/off,
`retrieval` gnn_goat/gnn_topk/ppr, `gnn_checkpoint`, `max_facts`, `max_tokens`, `include_outdated`.

**GNN.** Node scoring with GOAt's own `GCN_NC` (3 GCN layers + 2 linear), because GOAt's
`gcn_explain` decomposes exactly that model. GOAt takes one edge type, so SUPERSEDES status and
node type are node features; hop distance from the question's entities is a feature too (as in
SubgraphRAG), giving a question signal beyond 3 layers. Weak labels: nodes on shortest paths
from question entities to answers through current facts. Training data never comes from
MemoryAgentBench or MQuAKE (FactConsolidation contains ~all MQuAKE-CF facts):
`synthetic` = invented worlds with revisions (only the 37 relation templates are shared),
`subgraphrag` = WebQSP + CWQ (`rmanluo/RoG-*`), or `both`. Each checkpoint folder has
`config.json`, `metrics.jsonl` (live chart), `model.pt`.

GOAt imports two compiled packages (`torch_scatter`, `torch_sparse`) that don't build against
current torch on macOS; it only calls them on code paths we don't use, so `gnn/compat/` provides
stand-ins used only when the real packages are missing. GOAt's node-classification folder imports
model files that exist only in its graph-classification folder; `gnn/goat.py` puts both on the
path (no `__init__.py`, so Python merges them) instead of editing GOAt.

## Fake mode

`llm.mode: fake` starts the gateway with `--fake`: no request leaves the machine. Replies come
from `baselines/claude_gateway/fake_rules/` (one module per prompt family: GRAFT's writer, Mem0's
extraction/update, HippoRAG's NER/triples/filter/QA, Letta's tool loop, the FC answer), in the
shape each system parses, so every code path runs. Accuracy in fake mode is meaningless; token
counts approximate a real run's input side (used for the UI's cost estimate). The
"answer in retrieved" column is real even in fake mode for methods that report their retrieved
memory (BM25, GRAFT): it checks whether the gold answer reached the answering model.

## Control panel (`ui/app.py`)

**Run**: tick baselines, add GRAFT variants, choose length / questions / repeats / embedding
model / answer cap, Fake or Real. Real requires the key in the environment, a fake-mode cost
estimate of the exact selection, and an approval tick. Live progress and logs.
**Train GNN**: data source and sizes, live loss and validation chart.
**Results**: the table for any length and mode, with the paper's reference block.
**Runs**: every run with its exact config and per-question answers; re-run fake configs.

## Fir (Digital Research Alliance)

`scripts/fir/`: `common.sh` (modules, `HF_HOME` and `RESULTS_DIR` in `~/scratch/sgar`),
`setup_login_node.sh` (environments, data, embedding weights; login nodes have internet),
`check_internet.sbatch` (do compute nodes reach api.anthropic.com?), `train_gnn.sbatch` (H100 slice),
`run_cpu_queue.sbatch` (32 CPU cores, for fake-mode GOAt runs), `run_queue.sbatch` (GPU, for real runs).
Code lives in `~/SGAR` because this account has no `~/projects` link yet. `common.sh` loads the `arrow`
module and the venv uses `--system-site-packages`, because pip cannot install pyarrow on the cluster.

Tested on Fir: setup, GNN training, and fake-mode runs of GRAFT. Not tested on Fir: `run_queue.sbatch`,
`check_internet.sbatch`, the third-party baseline environments, and anything calling the real API.
Importing the embedding library takes minutes on Fir's disks, so the runner waits up to 30 minutes for
the gateway.

## Change log

### 2026-10-30: the GNN's subgraph is chosen by PPR, not by distance

**Problem.** The GNN can only look at 400 nodes (GOAt's cost limit). They were the 400 *nearest* the
question's entities, so hubs filled the slots first: "United States of America" has 1,281 links. On
FC-MH at 262K the answer was inside those 400 nodes for 42 of 100 questions, against 99 of 100 with no
limit. When the GNN could see the answer it ranked it well (median rank 7), so the limit was the cause.

**Change.** `my_method/gnn/features.py`: `k_hop_subgraph` is replaced by `select_subgraph`, which runs
Personalized PageRank from the question's entities over the whole graph and keeps the top 400 nodes.
A walker splits its steps across a node's links, so hubs pass on little to each neighbour. The same
selection is used in training (`dataset.py`) and retrieval (`retrieval.py`), and `--radius` is gone.
`tests/test_core.py` has a test that selection reaches past a hub.

**Also changed.** Retrieval budget raised from 20 facts to 5,120 tokens to match BM25; `retrieval_workers`
added; training stores each text vector once, because 8 GB of RAM could not hold the data otherwise.

**Results.** FactConsolidation 262K, fake LLM, retrieval only, `bge-small` embeddings, GNN trained on 400
synthetic worlds. Score: the gold answer is the object of a fact shown to the model. The writer was
simulated with the rule parser, and each number rests on 100 questions.

| Mode | 50 facts, SH | 50 facts, MH | ~181 facts, SH | ~181 facts, MH |
|---|---|---|---|---|
| PPR only | 97 | 48 | 98 (full budget, about 300 facts) | 68 (full budget) |
| GNN top-k | 97 | 55 | 98 | 65 |
| GNN + GOAt | 97 | 57 | 98 | 65 |

At about 181 facts everything PPR selected fits the budget, so the GNN has nothing to choose and the row
is really PPR's result. At 50 facts ranking decides what reaches the model, and GNN + GOAt beats PPR by 9
questions on multi-hop. These checks used the test questions' gold answers to find the cause, so the
final evaluation should not be tuned further against them.

## Results table

`python -m eval.table --length 262k --mode real` -> `results/table_262k_real.{csv,md}`. Columns:
FC-SH, FC-MH, Avg (± std over repeats), tokens per question, memory build time, query time, API
cost, questions per split, repeats, answer-in-retrieved. Every number comes from run outputs; the
paper block comes from `data/paper_reference.py`, which parses arXiv's HTML.

## Known benchmark issues

- FC chunk size: the paper states 512 tokens; the released main run lists use 4096 (512 only in
  the chunk-size ablation). We use 512, except 4096 for Mem0 and Letta (the paper's setting).
- The NLTK sentence splitter attaches a fact's serial number to the end of the previous fact, so
  most chunks begin with a fact whose number is in the previous chunk. Same for every method.
- Scoring is substring exact match: an answer naming both the old and the new value counts.
- Some gold labels look like the older value (e.g. "Who founded Shingon Buddhism?" gold Kūkai,
  later replaced in the context). Estimated 7-10 of 100 at 262K SH; not yet hand-checked.
- Mem0 (both versions) caps its extraction output at 2000 tokens; a 4096-token FC chunk holds
  ~250 facts, so extraction is likely truncated. Kept for fidelity; probably part of why Mem0
  scores low in the paper.
