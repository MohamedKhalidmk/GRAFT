# GRAFT on LongMemEval: the plan after the diagnosis (design, 2026-11-22)

> Decisions by the user, 2026-11-22. Baseline: **G35** (mode C + T-REx guide, 50 facts). Every change is a new
> candidate with a fresh ID in the [registry](../reference/REGISTRY.md). Companion designs:
> [adaptive retrieval](graft_adaptive_retrieval_design.md) (G39, G40), [writer fix](graft_writer_fix_design.md).

## What the diagnosis found (LongMemEval dev, 76 items; Flotilla run log 2026-11-22)

| Where the answer is lost | Share |
|---|---|
| gold string in the built graph (short golds) | 51% |
| ... in the 50 facts shown / 100 / 200 | 36% / 44% / 45% |
| questions that link no entity (embedding fallback) | 43% |
| writer replies that failed to parse (all 500 builds) | 10% of calls; 15% of dev evidence sessions have no facts |
| 20 hand-read failures | 14 build misses, 3 counting across sessions, 2 ranking, 1 answer error |

## New candidates

| ID | What changes against G35 | Part (registry column) |
|---|---|---|
| G39 | drop cutoff: show the first k of G35's ranking, k at the largest score drop (10 to 100, pool 200) | Fact count |
| G40 | G39, then Qwen may ask for the next 50 facts (at most 3 asks, at most 200, stop when nothing new) | Fact count |
| G41 | writer v2, thinking off | Writer |
| G42 | writer v2, thinking on, cap 16,384 | Writer |
| G43 | user node linking on the better of G41 / G42 | Entity linking |
| G44 | chat guide instead of the T-REx guide, on G43 | Guide |
| G45 | G43 without any guide (mode C alone on the new graphs) | Guide |

G08 (mode C, no guide) on the old graphs already exists; G45 is its counterpart on the writer-v2 graphs, so the
guide comparison in step 4 runs on one set of graphs.

## 1. Writer v2 (G41, G42), on the 76 dev histories first

- **Reliability:** every raw writer reply is saved (`work/writer_replies.jsonl`: chunk, call, reply, stop reason); a
  parse failure is retried once (as now); a reply cut off at the cap keeps every complete fact before the cut.
- **Arms:** thinking off (G41, cap 8,192, as G35) and thinking on with a bigger cap (G42, 16,384; the reasoning is not
  part of the JSON).
- **Prompt for chat histories:** keep the date (each fact carries its session's timestamp; a relative date such as
  "yesterday" is resolved against it), exact numbers and amounts, links and titles, and the user's own details,
  statements and preferences; extract from the assistant's turns too (lists, recommendations, named items, with
  their position when the user may ask "the 7th one").
- **Reported per arm:** parse failures, sessions with no facts, gold-in-graph and gold-in-50 per question type.

## 2. User node (G43)

The writer already writes the user as an entity named "user", but a question says "I", "my", "me", so nothing links
and 43% of questions fall back to embedding search. G43 links any first-person question to the user's node, so
"what did I buy" starts its walk there. **Reported:** fallback rate before and after (free: linking needs no LLM), then
gold-in-50 and accuracy.

## 3. Chat guide (G44)

Built like the T-REx guide (relation labels, entity types, which relations follow which, no fact ever shown to the
answering model), from a separate dialogue dataset with person-level triples, never LongMemEval. The dataset is
proposed to the user first (below). Before use: the full leakage check (13-gram and embedding, as protocol section 5)
against LongMemEval and every test set. The guide is chosen by data type before building: T-REx for
FactConsolidation, chat for LongMemEval. One merged guide comes later.

**Proposal (for the user's choice):**
1. **Dialogue NLI** (Welleck et al., 2019): PersonaChat utterances labelled with (subject, relation, object) triples
   about the speaker, e.g. (i, have_pet, dog), (i, like_activity, hiking); about 60 relation types. Closest match to
   what LongMemEval asks about the user, and it already comes as triples.
2. **Multi-Session Chat** (Xu et al., 2022): multi-session dialogues with persona summaries; no triples, so Qwen would
   extract them (more work, more noise).
3. Not usable: ShareGPT and UltraChat (LongMemEval builds its filler sessions from them), and LoCoMo (another
   long-memory benchmark we may compare against).

## 4. Same-day comparison on LongMemEval dev (after the writer fix)

On the same writer-v2 graphs, one day: G45 (no guide), G43 (T-REx guide), G44 (chat guide), with the four Memory
routes' base route Fast, judged by Haiku as the labels were. This says whether a guide helps, hurts, or depends on
which one.

## 5. Adaptive retrieval (G39, G40)

As its design: FactConsolidation first, free gold-in-facts check, then Qwen at 1,024 tokens, 3 repeats, same day as
G35.

## 6. FactConsolidation retest

Every change also runs on FactConsolidation (Qwen, 1,024 tokens, 3 repeats), the same day as G35, so a gain on
LongMemEval does not hide a loss there. The writer changes need a FactConsolidation rebuild on Qwen of the 537-chunk
graph (free).

## Keep rule (user, set 2026-11-22, before any result)

Keep a change if it beats its baseline by more than the repeat spread on its own benchmark, and does not drop
FactConsolidation by more than the spread. (For G39/G40 the earlier rule also counts: a match with clearly fewer
facts.)

## Not without the user's yes

Rebuilding all 500 histories; changing the router labels. Everything here is free on Qwen and uses every pool (Fir and
Nibi MIG slices, Trillium nodes).
