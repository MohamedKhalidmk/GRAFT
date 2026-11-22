# Test 09: adaptive retrieval on FactConsolidation (G39, G40 against G35)

Question: can GRAFT show fewer facts (G39, a cutoff at the largest score drop) or let Qwen ask for more (G40) without
losing accuracy against G35's fixed 50 facts? Design and keep rule: [graft_adaptive_retrieval_design.md](../../docs/design/graft_adaptive_retrieval_design.md).

Keep rule (user, 2026-11-22, before any result): keep a candidate if it beats G35 by more than the repeat spread, or
matches it (within the spread) with clearly fewer facts; "clearly fewer" = at least 30% fewer facts shown per question
(proposed in the design, still to be confirmed by the user).

Setup: FactConsolidation multi-hop 262k, 100 questions, Haiku-built graph (2026-11-13; 1 parse failure, not affected by
the bare-list writer bug); answers by Qwen3.8-27B W4A16 on a 3g.40gb H100 slice (Nibi), 1,024-token cap, one repeat per
job, all on 2026-11-22. Results: [runs/run-01](runs/run-01/).
