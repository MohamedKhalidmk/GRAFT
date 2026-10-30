## Selective Forgetting, FactConsolidation 6k, Claude Haiku 5.5

**FAKE LLM: pipeline test only. Accuracy is meaningless; tokens and cost are rough estimates.**

Accuracy in %, substring exact match (the paper's metric). ± is the standard deviation over repeats. Answer in retrieved: share of questions whose gold answer appears in the memory handed to the model (methods that report it).

| Method | Family | FC-SH | FC-MH | Avg | Tokens / question | Memory build time (s) | Query time (s) | API cost ($) | Questions (SH/MH) | Repeats | Answer in retrieved (SH/MH) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Claude Haiku 5.5 (1M, full history) | Long-Context Agents | 0.0 | 0.0 | 0.0 | 7352 | 0.2 | 0.00 | 0.004 | 3/3 | 1 |  |
| BM25 | Simple RAG Agents | 0.0 | 0.0 | 0.0 | 6188 | 0.0 | 0.00 | 0.006 | 5/5 | 1 | 100/80 |
| HippoRAG-v2 (benchmark copy) | Structure-Augmented RAG Agents | 0.0 | 0.0 | 0.0 | 6737 | 5.9 | 0.02 | 0.011 | 3/3 | 1 |  |
| HippoRAG-v2 (upstream) | Structure-Augmented RAG Agents | 0.0 | 0.0 | 0.0 | 6740 | 23.1 | 0.01 | 0.011 | 3/3 | 1 |  |
| Mem0 (benchmark copy) | Structure-Augmented RAG Agents | 0.0 | 0.0 | 0.0 | 1645 | 2.2 | 0.01 | 0.007 | 3/3 | 1 |  |
| Mem0 (upstream) | Structure-Augmented RAG Agents | 0.0 | 0.0 | 0.0 | 1709 | 6.6 | 0.12 | 0.005 | 3/3 | 1 |  |
| MemGPT / Letta (benchmark copy) | Agentic Memory Agents | 0.0 | 0.0 | 0.0 | 10233 | 5.4 | 0.18 | 0.006 | 3/3 | 1 |  |
| MemGPT / Letta (upstream) | Agentic Memory Agents | 0.0 | 0.0 | 0.0 | 10985 | 18.0 | 0.66 | 0.007 | 3/3 | 1 |  |
| total-agent-memory (supersede) | Agentic Memory Agents | 0.0 | 0.0 | 0.0 | 474 | 8.2 | 0.68 | 0.000 | 3/3 | 1 |  |
| SGAR (ours) | Ours (structure-augmented + agentic) | 0.0 | 0.0 | 0.0 | 406 | 0.2 | 0.17 | 0.015 | 5/5 | 1 | 100/60 |

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
