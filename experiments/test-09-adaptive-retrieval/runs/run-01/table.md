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

Keep rule: G39 is 1.0 below G35, equal to the repeat range (within the spread at its edge), with 34% fewer facts:
kept if the 30% threshold is confirmed. G40 is within the spread (-0.7) but shows 36% more facts and makes 40% more
calls: it does not beat G35 and is not cheaper, so the rule does not keep it (dropping needs the user's yes).
