# Test 07 · Haiku drift and the fixed Haiku check

| Test | Date | Status | Current run |
|---|---|---|---|
| 07 | 2026-11-21 | done; the check runs in every paid Haiku batch | [run-01](runs/run-01) |

## Candidates and setups

IDs from the [registry](../../docs/reference/REGISTRY.md) (frozen 2026-11-21). A candidate is the method, a setup is the candidate plus model,
answer cap, benchmark and scoring; old run folders keep their names.

| Candidate | Setup | Row in this test |
|---|---|---|
| G08 | S17 | 2026-11-13 run (mode C) |
| Haiku check (replay) | S101 | Replay of the 2026-11-13 facts, today |

## Question

Mode C scored 38 on 2026-11-13 and about 34.7 a week later on the same graph. Did something on our side change (code,
prompt, grader, settings, data), or did Haiku's answers change?

## Setup

The same day (2026-11-21), Haiku, 3 repeats each: the exact 2026-11-13 commit (28d4fd5) with its config; today's code
(test 05 arm A); and a replay, where today's Haiku re-answers the exact facts the 2026-11-13 run retrieved, with no
retrieval at all (`replay_retrieved`). Then everything outside the code was compared, request by request:
[baseline_check.md](baseline_check.md).

## Result

| Run | Per repeat | Mean |
|---|---|---|
| 2026-11-13 run | 38 | 38 |
| The 2026-11-13 commit, today | 36 / 36 / 36 | 36.0 |
| Today's code (arm A) | 36 / 33 / 35 | 34.7 |
| Replay of the 2026-11-13 facts, today | 34 / 36 / 33 | 34.3 |

Given identical prompts (identical input token counts on 100 of 100 questions), today's Haiku scores about 34. Model
string, max_tokens, thinking, endpoint, SDK (anthropic 2.8.0, installed before the 38 run), data and grader are the
same. Only Haiku's answer choices differ, on about 13 coin-flip questions. Across runs the shift may be real (four
2026-11-13 modes averaged 37.3; today's mode C runs average 35.0, about 2 standard errors); it can only come from the
API side.

## Decision

Compare methods only within the same day. Every paid Haiku batch starts with the replay as a fixed check (1 repeat,
about $0.027; history: [haiku_canary.md](haiku_canary.md), `scripts/haiku_canary.py`), and the gateway logs each
call's request hash, message ID, API request ID and reply hash.

## Revisions

- 2026-11-21: test created from test 05's baseline check; the check and its history moved here.
