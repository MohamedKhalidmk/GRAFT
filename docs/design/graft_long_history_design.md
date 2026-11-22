# GRAFT past the context window: accuracy against history length (design, 2026-11-22)

> Idea from the user, 2026-11-22. Status row 10 in [STATUS.md](../session/STATUS.md). Design only. **Starts only
> after the writer v2 decision** (G41/G42, [plan](graft_longmemeval_plan_design.md)), so the LongMemEval pilot uses
> the writer that wins. The truncation rule for routes that read the whole history is fixed now, before any run, in
> Flotilla's [protocol](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/PROTOCOL.md)
> section 11.

## Question

GRAFT reads a bounded set of facts however long the history is; full reading has to drop the oldest part once the
history passes the window. How does accuracy change with history length for each, and where, if anywhere, does
GRAFT overtake full reading?

## What fits today

| History | Tokens (Qwen) | Qwen's window (262,144 native) |
|---|---|---|
| FactConsolidation 6k, 32k, 64k | about as named | fits |
| FactConsolidation 262k | about 262K | at or past the window: the truncation rule decides |
| LongMemEval S | 103,555 to 114,968 | fits (test 04 served it at 163,840) |
| LongMemEval M | 1,014,629 to 1,161,703 | about 4x past the window: full reading keeps roughly the newest 20% |

(LongMemEval M counts: `$SCRATCH/flotilla/data/longmemeval/prompt_tokens_summary.json`; the M file is already
downloaded and checksummed, `raw/longmemeval_m_cleaned.json`.)

## Part 1: FactConsolidation at every length (6k, 32k, 64k, 262k)

- **GRAFT:** G35 (mode C + T-REx guide, 50 facts), each length's graph built on Qwen with the writer of test 08's
  graphs, answered by Qwen at the 1,024-token cap.
- **Full reading:** Long context (full), GRAFT's `long_context` baseline, on Qwen, served at `--max-model-len 262144`,
  with the protocol's truncation rule (only 262k can be affected).
- **Splits and scoring:** SH and MH, substring match as every FactConsolidation comparison in GRAFT (metric rule:
  match the comparison's metric). 3 repeats per arm and length, all the same day.
- **Reported:** accuracy against length for both, with the spread; for full reading, the share of the history kept;
  for GRAFT, build GPU-seconds per length and answer GPU-seconds per question.

## Part 2: LongMemEval M pilot (40 histories)

- **Items:** 40 questions from the router split's **dev** ids (the same questions as LongMemEval S dev; train and
  held-out untouched), drawn stratified by question type, seed 20261122, before any run.
- **GRAFT:** the writer-v2 winner (and the user node if G43 is kept) at 50 facts, through the Memory route's base
  route Fast. Each M history is built once (cache as for S).
- **Full reading:** route Fast (F15) on the M history under the truncation rule, served at 262,144.
- **Reference, same questions:** both arms on the S histories (S fits whole), so the drop from S to M is measured per
  arm on the same 40 questions.
- **Scoring:** Claude Haiku 5.5 with LongMemEval's official judge prompts, the fixed Haiku check first (paid, about
  $0.02 for 160 answers).
- **Reported:** accuracy per arm on S and M; for full reading, how often the evidence sessions fell outside the kept
  part (from the items' evidence session ids), and accuracy with and without its evidence kept; for GRAFT,
  gold-in-graph and gold-in-50 on M against S; GPU-seconds for builds and answers.

## Not decided here

No keep rule: this measures where each approach stands as histories grow, for the thesis. Any change it suggests
(for example a longer fact budget for long histories) becomes its own candidate with its own rule.

## Cost

Free except the judge. The large item is the M builds: about 10 times an S history's writer calls each (S: about 33
MIG-slice GPU-hours for 500), so about 25 to 30 slice GPU-hours for 40 M histories, split across Fir, Nibi and
Trillium.
