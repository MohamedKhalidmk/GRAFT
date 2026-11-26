# Ideas

Every idea the user has asked for, GRAFT and Flotilla, one row each. Started 2026-11-26 from STATUS.md, the GRAFT test
index and the run log.

Rules (user, 2026-11-26):
- Nothing is removed unless the user says drop it. A parked idea stays parked.
- Status is one of: running, waiting, not started, answered, dropped. Parked ideas are "waiting (parked)".
- Every finished experiment ends with a one-line answer and a "MK decides" cell: keep, drop or more testing. A cell that
  still reads "keep / drop / more testing" is waiting for the user's call.
- Every report starts with the rows of this file that changed since the last report.
- STATUS.md keeps the detailed rows (row numbers in the last column); this file is the one-line view.

## GRAFT

| # | Idea | Date asked | Status | Result in one line | MK decides | Next step and date | STATUS row |
|---|---|---|---|---|---|---|---|
| 1 | Read order and starting graph (modes A, B, C, empty vs synthetic start; test 01) | 2026-11-13 | answered | mode C (G08, PPR then GOAt then PPR) is best on Haiku; 256-token answer cap needed (16 tokens cut answers) | keep (G08 default) | none | |
| 2 | Retrieval variants on mode C (top-10 hybrid, top-5 and others, G10-G23; test 02) | 2026-11-19 | answered | none beats G08 (best 31.0 against 38; not the same day) | drop (none kept) | none | |
| 3 | Base graph from RoG Freebase (test 03) | 2026-11-20 | answered | a small off-domain base adds hub noise; not adopted | drop | revisited by idea 21 (multi-graph) | |
| 4 | Base graph from full T-REx, with Haiku linking and a question layer (test 04) | 2026-11-20 | answered | halves accuracy (17-19% against 34.7%) | drop | revisited by idea 21 | |
| 5 | Working memory in the graph (G31, G33; test 05) | 2026-11-21 | answered | about 1 point over G08 at 3 times the cost, inside the spread | drop on Haiku | none | |
| 6 | T-REx as a structure guide, bridge or background facts (G35-G37; test 06) | 2026-11-21 | answered | the guide G35 wins (45.7 against 34.7, same day); bridge and background 17 | keep G35 | none | |
| 7 | Haiku drift check (test 07) | 2026-11-21 | answered | G08's same prompts score about 34 now; Haiku changed, not us; compare within one day | keep (check opens every paid batch) | none | |
| 8 | GRAFT on Qwen (test 08) | 2026-11-21 | answered | G35 holds on Qwen: 48.3 against G08 44.0 at 1,024 tokens | keep G35 | none | |
| 9 | 1,024-token rerun of all arms, arm E included (test 08 run-02) | 2026-11-22 | answered | G08 44.0, G35 48.3, G33 34.0, G34 32.7, G38 (arm E) 46.7 | keep (1,024 cap then; 4,096 since test 10) | none | 6 |
| 10 | Arm E: guide plus working memory (G38) | 2026-11-21 | waiting (parked) | 46.7, level with G35 at twice the cost | parked, not dropped | none until you unpark it | 7 |
| 11 | Adaptive retrieval: drop cutoff G39, ask for more G40 (test 09) | 2026-11-22 | answered | G35 48.3, G39 47.3 with 34% fewer facts, G40 47.7 with 36% more facts | keep / drop / more testing (both went on to idea 17) | decide after idea 17 | 5 |
| 12 | Writer v2 on 76 LongMemEval dev histories (G41; G42 thinking on dropped) | 2026-11-22 | running | free counts: gold answer in the graph 44 of 65 (old 28), sessions with no facts 80 (old 936); Memory accuracy waits for idea 17's judge | keep / drop / more testing | your writer v2 call after the retrieval judge, 2026-11-27 at the earliest | 1, 2 |
| 13 | History pre-build of the other 424 LongMemEval histories with the writer v2 | 2026-11-24 | running | started 26 Nov 01:24 on Fir; 93 of 424 done, about 16 an hour | n/a (approved) | done about 2026-11-27 04:00 | 43 (step 5) |
| 14 | Supersede check on chat histories (newer fact wins) | 2026-11-22 | running | 3 of 4 toy cases pass; the fourth failed on a writer bug, now fixed | keep / drop / more testing | rerun the toys with the fixed writer | 23 |
| 15 | User node: first-person questions link the user's node | 2026-11-22 | not started | free linking check: embedding fallback 34% to 0% | n/a | build on the writer v2 graphs after your writer v2 call | 3 |
| 16 | Chat guide from Dialogue NLI against no guide and the T-REx guide | 2026-11-22 | not started | guide built (7,081 triples, 59 relations), leakage check done | n/a | same-day comparison on the writer v2 graphs | 4 |
| 17 | Retrieval comparison on LongMemEval dev: fixed 50, 100, 200, cutoff G39, ask-for-more G40 | 2026-11-22 | running | first repeat, free substring check: f50 33, f100 36, f200 38, g39 30, g40 30 of 76 (not judged) | keep / drop / more testing | repeats 2 and 3 on Fir, then the Haiku judge (approved at about $0.09, hard stop $0.15), 2026-11-26 evening at the earliest | 24 |
| 18 | Bitemporal facts (said time for supersede, event time for temporal questions) | 2026-11-22 | not started | design written | n/a | build on the writer v2 graphs | 8 |
| 19 | GRAFT past the context window (FactConsolidation 6k to 262k, LongMemEval M) | 2026-11-22 | not started | design written | n/a | after your writer v2 call | 10 |
| 20 | Passage index on FactConsolidation: G49, G52 budget control, G50 HippoRAG 2-style, G51 BM25, G53 reading (test 10) | 2026-11-22 | answered | G52 56.7, G35 51.3, G53 47.7, G49 46.7, G50 24.0, G51 18.3; G49 not kept by the rule set before results | G49 drop (by your rule); G52 more testing | same-day rerun of G35, G52 and G52 at an 8,192 answer cap, 3 repeats each with seeds, Fir 6331772-6331780 (submitted 2026-11-26); test 10 run-01 (1,024 cap) to pull from Nibi | 41, 42, 47 |
| 21 | Multi-graph: guided, mixed, layered and wrong-base arms, built on G52, against G52 and G35 | 2026-11-26 | waiting | MedMemoryBench approved and downloaded (NC-SA, research only; results kept out of the Flotilla model card); 100 questions from 10 patients selected; 59 jobs, about 58 to 72 slice GPU-hours | n/a | your yes on Hetionet (16.1 MB) and the job count; arms only if the row 47 rerun keeps G52 ahead | 48 |
| 22 | Relation-name mismatches in LongMemEval misses | 2026-11-22 | not started | check written | n/a | run on idea 17's retrievals | 25 |
| 23 | FactConsolidation retest of every GRAFT change, same day as G35 | 2026-11-22 | running | standing rule; test 10's G35 broke it (one day apart), rerun submitted | n/a | with every candidate | 14 |

## Flotilla

| # | Idea | Date asked | Status | Result in one line | MK decides | Next step and date | STATUS row |
|---|---|---|---|---|---|---|---|
| 24 | Strategy routers on run-04 labels, with the learning curve | 2026-11-21 | answered | four routers trained; learning curve done | keep (retrain after the relabel) | idea 33 | 16 |
| 25 | LLM verifier as a route (test 06, F33 and F34) | 2026-11-22 | dropped | Fast + check 76.3 against Fast 81.1; Deep + check 84.2 against Deep 92.5; retries break more than they fix | drop (you, 2026-11-22) | none | 11 |
| 26 | Reasoning-graph route pilot (maths and GPQA-style against Deep and Fast) | 2026-11-22 | not started | design written, keep-rule numbers set | n/a | after the Memory work | 9 |
| 27 | Live RL from the chosen router | 2026-11-22 | waiting | held until the relabel and router retrain | n/a | 2026-11-29 at the earliest | 12, 43 |
| 28 | F36 USC tie rule for the free-text vote | 2026-11-22 | answered | on 9 Vote+Tools losses: old pick 0 right, USC 3, best single sample 5 ($0.011) | keep / drop / more testing | cost of a wider run, then your call | 28 |
| 29 | F37-F40: forced code, forced sympy, forced rules, self-check routes | 2026-11-22 | running | corrected 2026-11-26 (math grading was broken in the first count): of 153, forced_code 142, deep 141, deep_tools 141, forced_rules 138, self_check 132, forced_sympy 129; no unique wins; all four add 3 to the 10-column oracle of 148 | more testing (you, 2026-11-26: not dropped, none in the relabel) | 500-question run, waiting for your yes on 4 jobs, about 3.5 slice GPU-hours | 32, 53 |
| 30 | Memory-route diagnosis and what Qwen did with the facts | 2026-11-22 | answered | misses: 10 facts never written, 7 written but not shown, Qwen ignored a shown needed fact 0 times | keep (led to writer v2) | recheck on the G41 graphs | 15, 36 |
| 31 | Tool use by task type, per tool, answer length on memory questions | 2026-11-22 | answered | reports in run-04 (tool_by_tool.md, tool_use.md) | keep | none | 26, 29, 30, 31 |
| 32 | Haiku judge consistency (majority of 3, Sonnet tiebreak) | 2026-11-22 | answered | adopted for all LongMemEval judging | keep | none | 27 |
| 33 | Single full relabel with the held fixes, then router retrain | 2026-11-22 | waiting | fixes held: reasoning kept across tool rounds, ground-truth instruction grading, overrides | n/a | after your writer v2 call, 2026-11-28 at the earliest | 2, 37 |
| 34 | Wrong-gold review (20 questions) | 2026-11-24 | waiting | files built in reports/gold_review | your call in each file | you fill in MK's call | 44 |
| 35 | Package reorganization (core, routers, memory, data, research, legacy) | 2026-11-24 | answered | merged into restructure; suite 126 passed | keep | copy to the clusters after every job is done and your yes | 46 |
| 36 | Error stages and reasoning_error sub-types | 2026-11-22 | answered | tagged at scoring; hand check of 50 | keep | none | 33, 39 |
| 37 | Grader audit: every result graded with the old regex instruction grader | 2026-11-26 | waiting | on the 153 pilot questions only instruction verdicts change (run-04 routes drop 8 to 17 questions, oracle 151 to 145); run-03 and run-04 tables, routers F30 and F31 and rows 26, 29, 31 not yet regraded | n/a | sanity check added 2026-11-26: every grading run first grades 11 known-right and known-wrong answers and stops if any is off; your yes to fetch RLVR-IFeval's ground truth, then a free regrade | 51 |
| 38 | 4,096 tokens as the standard Qwen answer cap | 2026-11-26 | answered | set by you; G52 at 8,192 tested in the same-day rerun | keep | none | 52 |
