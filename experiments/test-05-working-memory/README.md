# Test 05 · Working memory in the graph

| Test | Date | Status | Current run |
|---|---|---|---|
| 05 | 2026-11-20 | planned | none |

## Question

Does answering in steps, with the question, sub-steps, notes and partial results written into the graph and read back, beat one-shot GRAFT, and does writing to the graph matter or only answering in steps?

## Setup

Design: [docs/design/graft_working_memory_design.md](../../docs/design/graft_working_memory_design.md). Arms A (mode C), B (question layer), C (working memory), C- (same steps, nothing written to the graph). Haiku, 3 repeats, empty-start graph first, then full T-REx. Starts after the fixed T-REx run (user, 2026-11-20).

## Result

Not run yet.

## Decision

Kept only if C beats A by more than its repeat spread and beats C-.

## Revisions

- 2026-11-20: test folder created from the existing runs and the Flotilla run log.
