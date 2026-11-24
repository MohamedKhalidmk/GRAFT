# Writer fix for LongMemEval builds (design, 2026-11-22)

> Diagnosis behind it: Flotilla run log 2026-11-22, "Memory-route diagnosis" (LongMemEval dev items). Candidates
> ([registry](../reference/REGISTRY.md)): G35 is the method; what changes here is how its graph is written.

## What the diagnosis found

- The writer's reply failed to parse on 2,691 of 27,014 calls across the 500 LongMemEval builds (about 10%). A
  chunk whose extraction fails twice adds no facts, and one chunk is one session: 15% of the dev evidence sessions have
  zero facts.
- 504 of those calls stopped at the 8,192-token cap (cut-off JSON); the rest were malformed replies. Replies were not
  saved, so their exact form is unknown. Thinking is already off (`enable_thinking: false` in the gateway).
- Surviving facts drop details questions ask about: event dates, counts, links, and the user's own statements and
  preferences when the assistant's turns are long.
- In 20 hand-read failures, 14 were build misses (7 sessions with no facts, 7 with the detail lost).

## Part A: reliability (a code fix; same writer prompt)

1. Save every reply that fails to parse (raw text, stop reason, chunk id) to `work/parse_failures.jsonl`.
2. Salvage: from a reply cut off at the cap, keep every complete fact object before the cut.
3. Split: if extraction still fails (or the reply hit the cap), split the chunk in two at a turn boundary and extract
   each half (at most two levels), so no session is lost to one long reply.
4. Count salvaged, split and lost chunks in the build record.

Under the registry rule, a code fix with no config switch keeps the candidate's ID, and runs built before it are marked
invalid. That would mark the run-04-lme Memory-route answers invalid once the fix is applied. **To decide (user):**
rebuild all 500 graphs and rerun the four Memory routes and their judging (about 33 MIG-slice GPU-hours for the
builds, as the first build; judge about $0.05), or keep the current labels and record the fix for new builds only.

## Part B: what the writer keeps (a prompt change: a new candidate)

The extraction prompt asks, for chat histories, to keep each fact's date (the session date, or a date the speaker
gives), exact numbers and amounts, names of things recommended (titles, links), and the user's own statements and
preferences before the assistant's general advice. A changed writer prompt is a different method, so it gets a new ID
(G41: G35 with writer prompt v2) and is tested against G35 on the LongMemEval dev items before any rebuild of the rest.

## Free checks first (no rebuild of all 500)

1. Part A on 20 dev histories with the most parse failures: count sessions with zero facts before and after.
2. Part B on the same 20: gold-in-graph and gold-in-50-facts before and after, per question type.
Both are free Qwen jobs on MIG slices or Trillium. Results decide whether the full rebuild is worth its GPU time.
