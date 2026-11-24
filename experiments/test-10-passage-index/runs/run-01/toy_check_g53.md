# G53 toy check on real Qwen (2026-11-22, Fir 5364165, 3g.40gb slice, first 10 questions; not a result)

Run `exp_toy_passages_g53_20261122-232315_j5364165` (S185), 10.5 minutes with model start.

| Check | Result |
|---|---|
| OPEN lines parse | yes: 4 of 10 questions asked, every reply ended in a well-formed OPEN line (`P1 AROUND`, `P1 SESSION`) |
| Loop stops | yes: at most 3 asks and 4 calls; no question still asking at the end |
| Empty answers | none |
| Opened tokens | 62-307 per asking question; tokens shown 4,541-4,991 per question |
| Answers cut at 1,024 tokens | 3 of 10 (all three were asking questions; long reasoning over the opened text) |
| Right (substring) | 3 of 10; gold in the context 5 of 10 |

Found and fixed before any run: Qwen repeated the same request (`OPEN P1 AROUND` three times; 3 of the 4 asking
questions) after it had already been opened, so asks and calls were spent on text it already had. The loop now stops
asking when an ask opens nothing new and answers the plain question (as G40 stops when the pool is used up); test
`test_reading_stops_when_an_ask_opens_nothing_new`. The prompt is unchanged (v1).
