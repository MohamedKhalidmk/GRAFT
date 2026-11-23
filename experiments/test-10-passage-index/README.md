# Test 10: passage index on FactConsolidation (G49 against G35, G50, G51)

Question: does the guided graph + passage index (G49: the guided ranking's facts bring their source passages) answer
better than G35's guided fact lines, and better than passage retrieval without the guide (G50, HippoRAG 2-style) or
BM25 (G51) over the same passages? Added by the user (2026-11-22): G52, G35 at the same 4,096 tokens, to separate
"more text" from "passages"; and G53, the index with reading (Qwen may open more of the original text, at most 3 asks). Design: [graft_passage_index_design.md](../../docs/design/graft_passage_index_design.md).

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
| G52 | S183 | G35's ranking, fact lines until their source text reaches 4,096 tokens (the budget control) |
| G53 | S184 | G49's passages, then Qwen may reply `OPEN P<n> AROUND` or `OPEN P<n> SESSION` (prompt `passage_reading.v1`), at most 3 asks, 1,024 tokens per line, every opened token counted; toy check on the first 10 questions with real Qwen first (S185) |

- **Passages here:** a FactConsolidation chunk is one line of about 15 consecutive numbered facts that mostly have
  nothing to do with each other, so a passage is a slice of a chunk cut at sentence ends to at most 256 tokens (1,588
  passages for the 262k history; every one of the 18,088 facts links to one, 17,374 exactly by its source sentence).
  A shown passage therefore brings the needed fact together with its unrelated neighbours. At 4,096 tokens the passage
  arms show about 19-21 passages (roughly 250-300 fact sentences), against G35's 50 fact lines (about 1,200 tokens), so
  a G49 win can come from the larger budget as well as from the passages. The budget counts passage text; G49's
  30-fact summary and the outdated notes on passages (G49, G50) come on top, and the reported tokens shown include them.
- **Same day (user, 2026-11-22):** all six arms run together. The first 12 jobs were put on hold (Nibi, 2026-11-22)
  until G52 and G53 are ready, so nothing has to be rerun; if they had run first, G35 and G49 would be rerun beside
  G52 and G53.
- **Reported** (`make_table.py`): accuracy per repeat (mean, spread), gold in the context Qwen read (`answer_in_retrieved`), total tokens shown
  per question (the whole context on the final call: fact lines or passages, G49's summary, outdated notes, G53's
  opened text), asks and opened tokens per question (G53), Qwen calls per question (G35 and G49: one question parse for the guide plan plus one answer; G50 and
  G51: one answer).

## Runs

- [run-01](runs/run-01/) (2026-11-22): 12 jobs submitted, then held for G52 and G53. Smoke (Fir CPU 5357744, fake answers, real retrieval, 1 pass): all
  four arms run end to end; gold in the context shown G35 53, G49 59, G50 47, G51 35 of 100 (the guided arms are low
  here because fake mode scripts the guide's question parse; test 09's G35 had 59 with Qwen parsing).
