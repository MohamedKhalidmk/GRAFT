# Test 09 run-01 (2026-11-22, Nibi, Qwen 1,024 tokens)

| Candidate | Right (of 100) per repeat | Mean | Range | Gold in facts shown | Facts shown: mean (median, min-max) | Asks per question | Qwen calls per question | Answers cut at 1,024 tokens | Query seconds per question |
|---|---|---|---|---|---|---|---|---|---|
| G35 fixed 50 | 48, 48, 49 | 48.3 | 1 | 59% | 50 | 0 | 2.0 | 21-25 | 7.1-7.8 |
| G39 drop cutoff | 47, 47, 48 | 47.3 | 1 | 56% | 33.1 (20.5, 10-91) | 0 | 2.0 | 15-17 | 5.9-7.0 |
| G40 cutoff + asks | 47, 48, 48 | 47.7 | 1 | 59% | 67.9 (43-53, 10-200) | 0.79 | 2.8 | 2-5 | 6.6-6.9 |

Jobs: G35 Nibi 28366767, 28366768, 28448320; G39 28412989, 28412991, 28412999; G40 28413001, 28413026, 28448321.
Excluded: G35 r2 28366769 and G40 r2 28413036 (killed by the port-8000 clash, no scores). Job wall time 910-1,433 s
each, model start included. G35 r0 and r1 predate the facts_shown field; G35 always shows 50. "Calls" = one question
parse for the guide plan plus one answer (all parses booked on question 0), plus G40's asks.

Decision (user, 2026-11-22): the 30% bar is not confirmed. G39 lost by 1 in every same-day pair and has lower gold
in the facts shown (56% against 59%); G40 neither beats G35 nor is cheaper. Both stay undecided and go into the LongMemEval
retrieval comparison after the G41 rebuild (fixed 50, 100, 200, G39, G40; Flotilla STATUS row 24).
