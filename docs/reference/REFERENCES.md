# References: what GRAFT borrows, and from whom

Every paper, dataset, model and piece of code GRAFT borrows from. A file that copies or follows one of these names it
near its top in a `Sources:` line with the keys below (`original` = written for GRAFT); `tests/test_references.py`
checks that every key named in a file is listed here. Flotilla keeps its own list (Flotilla
`docs/reference/REFERENCES.md`); NOTICE gives the licence notices for the bundled code.

Licences: "repo" = stated in this repository or in the source's own files we hold; "check" = not yet confirmed from
the source's licence file or dataset card (to do before any publication). The two submodules
(`baselines/memoryagentbench` at 5380260, `my_method/gnn/GOAt` at 1ef20f0) are unmodified and not edited here.

## Methods and papers

| Key | Citation | Link | Licence | What we take | Where (files, IDs) |
|---|---|---|---|---|---|
| `goat` | Lu, Mills, He, Liu, Niu. GOAt: Explaining Graph Neural Networks via Graph Output Attribution. ICLR 2024 (arXiv 2401.14578) | https://github.com/sluxsr/GOAt | no licence file (NOTICE) | the GCN_NC model and gcn_explain, used unmodified from the submodule | `my_method/gnn/goat.py`, `my_method/gnn/explain.py`, `my_method/gnn/train.py`, `my_method/retrieval.py`; the explainer of G01, G04, G07-G09, G13, G19, G21, G28, G30-G48; tests 01, 02, 04-09 |
| `eig-search` | Lu, Liu, Mills, He, Niu. EiG-Search: Generating Edge-Induced Subgraphs for GNN Explanation in Linear Time. ICML 2024 (arXiv 2405.01762) | https://github.com/sluxsr/EiG-Search | no licence (NOTICE; use cleared by Prof. Lu) | the method, written again (follows its main.py node-classification branch) | `my_method/gnn/eig.py`, `tests/test_eig.py`; G10-G12, G14-G18, G20, G22-G27, G29; tests 02-04 |
| `hipporag` | Gutiérrez, Shu, Gu, Yasunaga, Su. HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models. NeurIPS 2024; Gutiérrez et al. From RAG to Memory (HippoRAG 2), arXiv 2502.14802, 2025 | https://github.com/OSU-NLP-Group/HippoRAG | check | personalized PageRank over the whole graph, HippoRAG-style entity linking, 0.5 damping for the second walk; also a baseline | `my_method/retrieval.py`, `my_method/gnn/features.py`, `baselines/hipporag/agent.py`; G03, G06 and every read order from G04; S79-S85 |
| `subgraphrag` | Li, Miao, Li. Simple is Effective: The Roles of Graphs and Large Language Models in Knowledge-Graph-Based Retrieval-Augmented Generation (SubgraphRAG). ICLR 2025 | https://github.com/Graph-COM/SubgraphRAG | check | weak labels on question-to-answer shortest paths, hop-distance node features | `my_method/gnn/labels.py`, `my_method/gnn/features.py`, `my_method/gnn/data_subgraphrag.py`; every GNN candidate |
| `memoryagentbench` | Hu, Wang, McAuley. Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions. ICLR 2026 (arXiv 2507.05257) | https://github.com/HUST-AI-HYZ/MemoryAgentBench | MIT (submodule LICENSE) | FactConsolidation, data loading and chunking, prompt templates, scoring, the baseline handlers, Table 3 numbers | `eval/benchmark.py`, `eval/methods.py`, `data/download.py`, `data/paper_reference.py`, `my_method/answer.py`, `my_method/working_memory.py`, `baselines/*/agent.py`; S01-S101; tests 01-09 |
| `longmemeval` | Wu, Wang, Yu, Zhang, Chang, Yu. LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory. ICLR 2025 (arXiv 2410.10813) | https://github.com/xiaowu0162/LongMemEval | MIT (Flotilla's run log) | the benchmark and its official judge prompts (runs happen in Flotilla) | `my_method/writer.py` (chat rules for G41), `scripts/plan_relation_check.py`, LongMemEval design docs; G41-G48, S163-S167 |
| `mquake` | Zhong, Wu, Manning, Potts, Chen. MQuAKE: Assessing Knowledge Editing in Language Models via Multi-Hop Questions. EMNLP 2023 | https://github.com/princeton-nlp/MQuAKE | check | the 37 relation cloze templates and their Wikidata labels (downloaded) | `data/build_fc_relations.py`, `my_method/fc_relations.json`, `my_method/writer.py`, `my_method/gnn/data_synthetic.py`; every GNN checkpoint, G09 |
| `densephrases` | Lee, Sung, Kang, Chen. Learning Dense Representations of Phrases at Scale (DensePhrases). ACL 2021; its eval utils (SQuAD-style normalisation), adopted by MemoryAgentBench | https://github.com/princeton-nlp/DensePhrases | check | answer normalisation and substring scoring, through MemoryAgentBench's utils | `eval/benchmark.py` (through the submodule); every setup |
| `mem0` | Chhikara et al. Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory. arXiv 2504.19413, 2025 | https://github.com/mem0ai/mem0 | check | a baseline (bundled 0.1.88 in the submodule; upstream 2.2.1) | `baselines/mem0/agent.py`; S95-S98 |
| `letta` | Packer et al. MemGPT: Towards LLMs as Operating Systems. arXiv 2310.08560, 2023 (Letta) | https://github.com/letta-ai/letta | check | a baseline (bundled Letta 0.7.0; upstream server 0.16.8) | `baselines/letta/agent.py`; S87-S90 |
| `knowl` | Knowl memory server v5.6.0 | https://github.com/dat999zx/knowl | check | a baseline, called through MemoryAgentBench's handler | `baselines/knowl/agent.py`, `baselines/knowl/bench_shim.py`; S86 |
| `total-agent-memory` | total-agent-memory 14.5.1 | https://github.com/vbcherepanov/total-agent-memory | check | a baseline | `baselines/total_agent_memory/agent.py`; S99, S100 |
| `bm25` | Robertson, Zaragoza. The Probabilistic Relevance Framework: BM25 and Beyond. 2009; LangChain BM25Retriever with rank-bm25 | https://github.com/langchain-ai/langchain | MIT (LangChain), Apache-2.0 (rank-bm25) | the BM25 baseline, following MemoryAgentBench's handler | `baselines/bm25/agent.py` |
| `triad` | TRIAD (our own earlier project) | https://github.com/MohamedKhalidmk/TRIAD | own | the assertion-record format | `my_method/base_graph.py` |
| `flotilla` | Flotilla (our own sister project) | https://github.com/MohamedKhalidmk/Flotilla | own | the Qwen quantisation, the leakage check, the LongMemEval runs, the session-docs test | `scripts/dnli_triples.py`, `tests/test_session_docs.py` |

## Datasets

| Key | Citation | Link | Licence | Where (files, IDs) |
|---|---|---|---|---|
| `factconsolidation` | FactConsolidation (Conflict_Resolution split of MemoryAgentBench, built from MQuAKE-CF facts) | https://huggingface.co/datasets/ai-hyz/MemoryAgentBench | check | `data/download.py`, `eval/benchmark.py`; S01-S101; tests 01-09 |
| `t-rex` | Elsahar et al. T-REx: A Large Scale Alignment of Natural Language with Knowledge Base Triples. LREC 2018 (copy: relbert/t_rex) | https://huggingface.co/datasets/relbert/t_rex | check | `my_method/base_graph.py`, `scripts/trex_guide.py`, `my_method/guide.py`; base graph G26-G29, G36, G37; structure guide G35, G38-G43, G46-G48 |
| `wikidata` | Wikidata property labels and aliases (fetched once from the Wikidata API) | https://www.wikidata.org | CC0 (check) | `my_method/wikidata_property_labels.json` and the 250-property files; same IDs as T-REx |
| `dialogue-nli` | Welleck, Weston, Szlam, Cho. Dialogue Natural Language Inference. ACL 2019 (PersonaChat sentences) | https://huggingface.co/datasets/xksteven/dialogue_nli | check (unknown, research use) | `scripts/dnli_triples.py`; G44 (designed) |
| `rog` | Luo, Li, Haffari, Pan. Reasoning on Graphs: Faithful and Interpretable Large Language Model Reasoning. ICLR 2024 (RoG-WebQSP, RoG-CWQ Freebase subgraphs) | https://huggingface.co/datasets/rmanluo/RoG-webqsp | check | `my_method/base_graph.py`, `my_method/gnn/data_subgraphrag.py`; G24, G25; test 03 |

## Code and libraries

| Key | Source | Link | Licence | Where |
|---|---|---|---|---|
| `networkx` | NetworkX (PageRank) | https://networkx.org | BSD-3-Clause | `my_method/retrieval.py`, `my_method/gnn/features.py` |
| `pyg` | Fey, Lenssen. Fast Graph Representation Learning with PyTorch Geometric. 2019 | https://github.com/pyg-team/pytorch_geometric | MIT | `my_method/gnn/` |
| `gcn` | Kipf, Welling. Semi-Supervised Classification with Graph Convolutional Networks. ICLR 2017 (arXiv 1609.02907) | https://arxiv.org/abs/1609.02907 | paper | the GCN used by GOAt's GCN_NC; every GNN candidate |
| `sentence-transformers` | Reimers, Gurevych. Sentence-BERT. EMNLP 2019; sentence-transformers library | https://github.com/UKPLab/sentence-transformers | Apache-2.0 | the embedder wrapper |
| `nltk-stopwords` | NLTK English stopword list (copied as text) | https://www.nltk.org | Apache-2.0 | `my_method/graph_store.py`, `scripts/fir/clean_base.py`, `scripts/fir/stopword_links.py`; G27-G29 |
| `vllm` | Kwon et al. PagedAttention / vLLM. SOSP 2023 | https://github.com/vllm-project/vllm | Apache-2.0 | serving Qwen (`scripts/*/run_qwen_graft*.sbatch`) |
| `anthropic-sdk` | anthropic Python SDK | https://github.com/anthropics/anthropic-sdk-python | MIT | `baselines/claude_llm.py`, `baselines/claude_gateway/server.py` |

## Models

| Key | Model | Link | Licence | Where |
|---|---|---|---|---|
| `claude-haiku` | Anthropic Claude Haiku 5.5 (API) | https://www.anthropic.com | Anthropic commercial terms | writes, links and answers in S08-S101; LongMemEval judge S163-S167 |
| `qwen3.8` | Qwen3.8-27B, Flotilla's W4A16 build | https://huggingface.co/Qwen/Qwen3.8-27B | Apache-2.0 | tests 08, 09, LongMemEval; S18, S19, S50-S72, S163-S167 |
| `bge-small` | Xiao et al. C-Pack. arXiv 2309.07597, 2023 (BAAI/bge-small-en-v1.5) | https://huggingface.co/BAAI/bge-small-en-v1.5 | MIT | every real run's embedder; the GNN checkpoints; entity linking; the T-REx guide's relation mapping; S78 |

## Open points (before publishing)

- The bundled letta, mem0, cognee and HippoRAG copies inside the MemoryAgentBench submodule carry no licence file of
  their own; their upstream licences need checking.
- No dataset-card licences are recorded; every dataset licence is "check".
- `my_method/writer.py`'s update operations (ADD, MERGE, SUPERSEDE, IGNORE) resemble Mem0's; the prompt is our own
  wording, but the resemblance should be credited in the paper.
