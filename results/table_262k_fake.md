## Selective Forgetting, FactConsolidation 262k, Claude Haiku 5.5

**FAKE LLM: pipeline test only. Accuracy is meaningless; tokens and cost are rough estimates.**

Accuracy in %, substring exact match (the paper's metric). ± is the standard deviation over repeats. Answer in retrieved: share of questions whose gold answer appears in the memory handed to the model (methods that report it).

| Method | Family | FC-SH | FC-MH | Avg | Tokens / question | Memory build time (s) | Query time (s) | API cost ($) | Questions (SH/MH) | Repeats | Answer in retrieved (SH/MH) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 5.5 (1M, full history) | Long-Context Agents | 0.0 | 0.0 | 0.0 | 305940 | 0.4 | 0.01 | 30.595 | 100/100 | 1 |  |
| Claude Haiku 5.5 (newest 128K) | Long-Context Agents | 0.0 | 0.0 | 0.0 | 121921 | 0.3 | 0.00 | 12.193 | 100/100 | 1 |  |
| BM25 | Simple RAG Agents | 0.0 | 0.0 | 0.0 | 5985 | 0.1 | 0.00 | 0.120 | 100/100 | 1 | 91/32 |
| HippoRAG-v2 (benchmark copy) | Structure-Augmented RAG Agents | 0.0 | 0.0 | 0.0 | 6409 | 16.9 | 0.04 | 0.449 | 100/100 | 1 |  |
| HippoRAG-v2 (upstream) | Structure-Augmented RAG Agents | 0.0 | 0.0 | 0.0 | 6398 | 16.9 | 0.03 | 0.449 | 100/100 | 1 |  |
| Mem0 (benchmark copy) | Structure-Augmented RAG Agents | 0.0 | 0.0 | 0.0 | 2042 | 959.8 | 0.09 | 0.381 | 100/100 | 1 |  |
| Mem0 (upstream) | Structure-Augmented RAG Agents | 0.0 | 0.0 | 0.0 | 1988 | 1323.6 | 0.80 | 0.196 | 100/100 | 1 |  |
| MemGPT / Letta (benchmark copy) | Agentic Memory Agents | 0.0 | 0.0 | 0.0 | 46784 | 7.6 | 0.19 | 0.939 | 100/100 | 1 |  |
| Letta server 0.16.8 (last MemGPT-lineage release) | Agentic Memory Agents | 0.0 | 0.0 | 0.0 | 25659 | 24.4 | 0.67 | 0.516 | 100/100 | 1 |  |
| total-agent-memory (supersede) | Agentic Memory Agents | 0.0 | 0.0 | 0.0 | 489 | 301.0 | 0.64 | 0.010 | 100/100 | 1 |  |
| SGAR (ours) [gnn_checkpoint=results/checkpoints/gnn_bge_400w, max_facts=50, retrieval=gnn_goat, retrieval_workers=32] | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 1399 | 15.4 | 0.42 | 0.638 | 100/100 | 1 | 98/57 |
| SGAR (ours) [gnn_checkpoint=results/checkpoints/gnn_bge_400w, max_facts=50, retrieval=gnn_topk, retrieval_workers=32] | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 1399 | 36.0 | 0.30 | 0.638 | 100/100 | 1 | 98/55 |
| SGAR (ours) [gnn_checkpoint=results/checkpoints/gnn_bge_400w, max_facts=50, retrieval=ppr, retrieval_workers=32] | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 1407 | 8.7 | 0.56 | 0.638 | 100/100 | 1 | 98/49 |
| SGAR (ours) [gnn_checkpoint=results/checkpoints/gnn_bge_400w, retrieval=gnn_goat, retrieval_workers=32] | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 4512 | 6.3 | 0.51 | 0.700 | 100/100 | 1 | 99/66 |
| SGAR (ours) [gnn_checkpoint=results/checkpoints/gnn_bge_400w, retrieval=gnn_topk] | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 4512 | 8.8 | 0.80 | 0.700 | 100/100 | 1 | 99/66 |
| SGAR (ours) [retrieval=gnn_goat] | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 6459 | 3.2 | 22.26 | 0.739 | 100/100 | 1 | 98/53 |
| SGAR (ours) [retrieval=gnn_topk] | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 6446 | 2.8 | 0.03 | 0.739 | 100/100 | 1 | 99/53 |
| SGAR (ours) [retrieval=ppr] | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 7286 | 3.1 | 0.08 | 0.755 | 100/100 | 1 | 99/68 |

## Reference only: paper's Table 3 (GPT-4o-mini backbone, 262K, not a reproduction)

Source: arXiv 2507.05257v4, extracted by data/paper_reference.py.

| System | Family | FC-SH | FC-MH | Avg |
|---|---|---|---|---|
| GPT-4o (128K) | Long-Context Agents | 60.0 | 5.0 | 32.5 |
| GPT-4o-mini (128K) | Long-Context Agents | 45.0 | 5.0 | 25.0 |
| Claude-3.7-Sonnet (200K) | Long-Context Agents | 43.0 | 2.0 | 22.5 |
| GPT-5-mini (400K) | Long-Context Agents | 78.0 | 28.0 | 53.0 |
| GPT-4.1-mini (1M) | Long-Context Agents | 36.0 | 5.0 | 20.5 |
| Gemini-2.0-Flash (1M) | Long-Context Agents | 30.0 | 3.0 | 16.5 |
| GPT-4o-mini | Long-Context Agents | 45.0 | 5.0 | 25.0 |
| BM25 | Simple RAG Agents | 48.0 | 3.0 | 25.5 |
| Contriever | Embedding RAG Agents | 18.0 | 7.0 | 12.5 |
| Text-Embed-3-Small | Embedding RAG Agents | 28.0 | 3.0 | 15.5 |
| Text-Embed-3-Large | Embedding RAG Agents | 28.0 | 4.0 | 16.0 |
| Qwen3-Embedding-4B | Embedding RAG Agents | 29.0 | 3.0 | 16.0 |
| RAPTOR | Structure-Augmented RAG Agents | 14.0 | 1.0 | 7.5 |
| GraphRAG | Structure-Augmented RAG Agents | 14.0 | 2.0 | 8.0 |
| MemoRAG | Structure-Augmented RAG Agents | 21.0 | 7.0 | 14.0 |
| HippoRAG-v2 | Structure-Augmented RAG Agents | 54.0 | 5.0 | 29.5 |
| Mem0 | Structure-Augmented RAG Agents | 18.0 | 2.0 | 10.0 |
| Cognee | Structure-Augmented RAG Agents | 28.0 | 3.0 | 15.5 |
| Zep | Structure-Augmented RAG Agents | 7.0 | 3.0 | 5.0 |
| Self-RAG | Agentic Memory Agents | 19.0 | 3.0 | 11.0 |
| MemGPT | Agentic Memory Agents | 28.0 | 3.0 | 15.5 |
| MIRIX | Agentic Memory Agents | 14.0 | 2.0 | 8.0 |
| MIRIX (4.1-mini) | Agentic Memory Agents | 20.0 | 3.0 | 11.5 |
