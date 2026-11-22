# Status

Same file in both repos (Flotilla's copy is the source; `scripts/sync_session_docs.py` copies it to GRAFT).

## Open experiments

Rules (user, 2026-11-22): updated every time Claude reports. A row is never deleted: a finished or dropped item
changes state and keeps its reason. Every report starts with "Status changes" (each row that changed since the last
report: old state to new state, with the reason, one line each; or "no changes"). No row changes state without being
listed in the next report. Dropping, parking or reverting anything needs the user's yes first and is logged in the run
log with its reason. States: queued, running, waiting on me, done, parked, dropped ("me" is the user).

| # | Experiment | IDs | State | Result (one line) | Next step | Last changed |
|---|---|---|---|---|---|---|
| 1 | Writer v2 on the 76 LongMemEval dev histories, thinking off (G41) and on (G42) | G41, G42 | running | G41: 40 of 76 graphs built, 93% of extraction calls parsed. G42 dropped (user, 2026-11-22): 336 of 358 extraction calls hit the 16,384-token cap with no reply; jobs cancelled, no graph | finish G41; report parse failures, sessions with no facts, gold-in-graph and Memory accuracy against the old writer | 2026-11-22 |
| 2 | Decision after writer v2: rebuild all 500 histories, relabel the four Memory routes, rejudge, retrain the routers | G41; F20-F23; F29-F32 | queued | needs row 1 (G42 dropped, so G41 is the only writer-v2 arm) | if one arm passes the keep rule, propose it and wait for the user's yes | 2026-11-22 |
| 3 | User node: first-person questions link the user's node | G43 | queued | free linking check: embedding fallback 34% to 0% on dev questions | build on the better writer-v2 graphs; gold-in-50 and accuracy | 2026-11-22 |
| 4 | Chat guide from Dialogue NLI; same-day comparison with no guide and the T-REx guide (Fast base route, Haiku judge) | G44, G45 (vs G43) | queued | leakage check done: 106 of 98,229 DNLI units flagged and dropped (Fir 5133851); guide built: 7,081 triples, 59 relations (Fir 5133880) | compare G45, G43 and G44 on the writer-v2 graphs, same day | 2026-11-22 |
| 5 | Adaptive retrieval on FactConsolidation (test 09) | G39, G40 | queued | free check, gold in the facts shown: G35 53/100 at 50 facts, G39 49/100 at 33 on average | Qwen 1,024-token runs, 3 repeats each (pending on Fir, Nibi, Trillium), same day as G35; then record test 09 | 2026-11-22 |
| 6 | Qwen 1,024-token rerun of all GRAFT arms, arm E included (test 08 run-02) | G08, G35, G33, G34, G38 | running | 14 of 15 runs done; arm E repeat 2 still queued | record test 08 run-02 when the last repeat finishes | 2026-11-22 |
| 7 | Arm E (guide + working memory) | G38 | parked | not kept at the 256-token cap; parked, not dropped (user) | its 1,024-token result comes with row 6 | 2026-11-22 |
| 8 | Bitemporal facts (said time for supersede, event time for temporal questions) | G46 | queued | design written (GRAFT `docs/design/graft_bitemporal_design.md`) | build on the better writer-v2 arm; temporal-reasoning dev items and FactConsolidation, same day | 2026-11-22 |
| 9 | Reasoning-graph route pilot (maths and GPQA-style against Deep and Fast) | F35 | queued | design written (`docs/design/reasoning_graph_route_design.md`); keep-rule numbers confirmed: similar compute within 25% of Deep, clearly less at most 75%, matches within 1 point | build and pilot when its turn comes (never ahead of the Memory work); full results either way: accuracy with spread, GPU-seconds, per type | 2026-11-22 |
| 10 | GRAFT past the context window: accuracy against history length, LongMemEval M pilot | G35 and the writer-v2 winner; F15 (setups at run time) | queued | design written (GRAFT `docs/design/graft_long_history_design.md`); truncation rule set in protocol section 11 | after the writer v2 decision: FactConsolidation 6k to 262k, then 40 LongMemEval M dev histories, GRAFT against full reading | 2026-11-22 |
| 11 | LLM verifier check (test 06); as routes if kept | F33, F34 (S159-S162) | queued | 12 runs submitted (Fir 5143762-5143791, Nibi twins), none started | answers, then the Haiku judge (needs the user's key), then the keep rule | 2026-11-22 |
| 12 | Live RL from the chosen router | F28 policy, started from F30; compared with F31 and Vote | queued | held until the Memory decision (row 2) | start once on the final router and graphs; dev only, held-out untouched | 2026-11-22 |
| 13 | Docs, reports and prompts cleanup | none | done | reports/ keeps leakage only; audits in tests 02 and 03; `experiments/legacy/`, `prompts/legacy/`; links fixed (Flotilla 1d12780) | none | 2026-11-22 |
| 14 | FactConsolidation retest of every GRAFT change, same day as G35 | G39-G46 | queued | none yet | runs alongside each candidate (G39/G40 in row 5) | 2026-11-22 |
| 15 | Memory-route diagnosis on LongMemEval dev | F20-F23, G35 | done | gold in the graph 51%, in the 50 facts shown 36%; 14 of 20 hand-read failures were build misses | led to rows 1, 3, 4, 5 | 2026-11-22 |
| 16 | Strategy routers on run-04-lme, plus the learning curve | F29-F32 | done | F30 0.959 at 72% of Vote's compute and F31 0.963 kept; F29, F32 dropped; curve not climbing, so no more labels | retrain all four if row 2 relabels | 2026-11-22 |
| 17 | LongMemEval route labels and Haiku judge (run-04-lme) | F15-F23 | done | 1,950 questions merged (1,365 / 293 / 292); judge $0.182 | none | 2026-11-22 |
| 18 | F06 check: one candidate or two | F06 | done | same build, vLLM settings and temperature in tests 02, 03 and Deep+Tools; stays one | none | 2026-11-22 |
| 19 | Qwen answer-cap check and the metric rule | G08, G35 | done | the 256-token cap cut 35% of mode C answers, so the 1,024 rerun (row 6); metric: match the comparison's | none | 2026-11-22 |
| 20 | Pipeline diagram: Verifier card shows what is built | none | done | "exact checks: maths, letters, code tests, instructions"; re-rendered (Flotilla 9f19f0d) | update if row 11 is kept | 2026-11-22 |
| 21 | Session docs refresh (HANDOFF) | none | queued | not done since the restructure | refresh HANDOFF from this table and the queues | 2026-11-22 |
| 22 | Format tests for every dataset (benchmarks, RULER, router pool, label items) | none | done | 11 sources, real rows in `tests/data/formats/`, core fields, type extras and round trips; 8 tests in 0.1 s on the Mac (Flotilla a79ebba) | none | 2026-11-22 |
| 23 | Supersede check on chat histories: extract both facts, SUPERSEDES edge, newer fact retrieved first | G41 (writer v2, thinking off) | running | checker and 4 toy histories written (`flotilla/supersede_check.py`, 4 unit tests); toy build queued (Fir 5173465, Nibi 28429303) | run the checker on the toy cache, then on the Crash Course item (lme-72e3ee87, 10 to 50) once G41 builds it | 2026-11-22 |
