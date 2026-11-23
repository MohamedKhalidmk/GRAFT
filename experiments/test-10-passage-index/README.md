# Test 10: passage index on FactConsolidation (G49 against G35, G50, G51)

Question: does the guided graph + passage index (G49: the guided ranking's facts bring their source passages) answer
better than G35's guided fact lines, and better than passage retrieval without the guide (G50, HippoRAG 2-style) or
BM25 (G51) over the same passages? Design: [graft_passage_index_design.md](../../docs/design/graft_passage_index_design.md).

Keep rule (user, 2026-11-22, before any result): keep the index (G49) only if it beats G35 by more than the repeat
spread.

## Setup

- **Data:** MemoryAgentBench FactConsolidation multi-hop 262k, 100 questions, the Haiku-built graph (2026-11-13,
  `real_mh_262k_empty_start.json`), as test 09.
- **Answers:** Qwen3.8-27B W4A16 on a 3g.40gb H100 slice (Nibi), 1,024-token cap, 3 repeats, each its own job (vLLM seed
  20261119+k), all 12 jobs submitted together the same day. Configs `configs/runs/exp/passages/{g35,g49,g50,g51}_r{0,1,2}.yaml`.
- **Arms:**

| Candidate | Setup | What Qwen reads |
|---|---|---|
| G35 | S179 | 50 guided fact lines, as test 09 (the current default) |
| G49 | S180 | the guided ranking (up to 400 facts) brings each fact's source passage, in ranking order, cut at 4,096 tokens, then a 30-fact summary |
| G50 | S181 | HippoRAG 2-style passages on the same graph: passage nodes, PPR (damping 0.5) seeded by question-to-fact and dense passage similarity, no guide; 4,096 tokens |
| G51 | S182 | BM25 on the question over the same passages; 4,096 tokens |

- **Passages here:** FactConsolidation's chunks are numbered one-sentence facts, one per line, so a passage is one
  source line, the same sentence G35 already shows as a fact's provenance. On this benchmark G49 therefore differs from
  G35 mainly in how much it shows (as many guided lines as fit in 4,096 tokens, against 50 facts) and in its summary,
  not in the kind of text. The 4,096-token budget counts passage text; G49's summary comes on top of it, and the
  reported tokens shown include it.
- **Reported:** accuracy per repeat (mean, spread), gold in the context Qwen read (`answer_in_retrieved`), tokens shown
  per question, Qwen calls per question (G35 and G49: one question parse for the guide plan plus one answer; G50 and
  G51: one answer).

## Runs

- [run-01](runs/run-01/) (2026-11-22): submitted.
