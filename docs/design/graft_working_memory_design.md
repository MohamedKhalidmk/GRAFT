# GRAFT working memory: design (before coding)

> IDs ([registry](../reference/REGISTRY.md), 2026-11-21): arm A = G08, arm B = G30, arm C = G31 (v1) and G33 (v2), arm C- = G32 (v1) and G34 (v2). Later combined with the guide as G38.

Status: design for review, 2026-11-20. Nothing is coded yet. Test in GRAFT alone, on the GRAFT questions
(FactConsolidation 262k, multi-hop, 100 questions), before anything goes into Flotilla's Memory routes.

## Idea

Today GRAFT answers in one step: retrieve a region of the graph, put its facts in the prompt, ask once.
With working memory the agent answers in several steps and keeps its work **in the graph**: the question, its
sub-steps, short notes and partial results become nodes linked to the facts they used. Each next step reads that
chain back, both in its prompt and through the graph walk (retrieval starts from what the agent has found so far).

## What gets written

Per question, a small "work" layer (`layer="work"`), attached to the memory graph while that question is answered:

| Node | Content | Written when |
|---|---|---|
| Question `W:q` | the question text | at the start |
| Step `W:s1..sK` | one sub-question, e.g. "sport played by Christian Abbiati -> ?A" | after the plan call |
| Result `W:r1..rK` | the step's partial answer, e.g. "football" | after each step call |
| Note `W:n1..nK` | the step's reasoning note, at most 40 words | after each step call |
| Answer `W:a` | the final answer | after the final call |

| Edge | From -> to | Meaning |
|---|---|---|
| `has_step` | q -> s_i | the plan |
| `next` | s_i -> s_(i+1) | step order |
| `about` | s_i -> entity, or s_i -> r_(i-1) | what the step asks about (a graph entity, or the previous result) |
| `used_fact` | s_i -> fact | each fact the step's call cited by its number |
| `answer` | s_i -> r_i, q -> a | the step's result, the final answer |
| `note` | s_i -> n_i | the note |
| `same_as` | r_i -> entity | the result linked to a graph entity (same top-10 + Haiku linking as the question layer) |

Work nodes are never returned as retrieved facts (`_is_fact` already skips `query` nodes), and stored facts are
never changed. After the question is answered the work layer is removed from the graph and saved, whole, to
`working_memory.jsonl` (one record per question) for inspection. Nothing carries over between questions in this
test (that would leak answers across questions).

## When, and how it is read back

1. **Plan** (1 call). The question layer's parse, already in GRAFT, gives the chain with unknowns:
   (Christian Abbiati, plays sport, ?A), (?A, country of origin, ?B). Each edge becomes a step. If the parse fails,
   one step = the whole question (falls back to today's behaviour).
2. **Each step i** (1 call per step).
   - Retrieval: mode C as today, but seeded from the step's `about` node (the question entity for step 1,
     `same_as` of r_(i-1) after that) plus every fact already marked `used_fact`. The work nodes are in the graph,
     so the PageRank walk passes through the chain built so far.
   - Prompt: the working memory serialized as text (question, steps done with their results, notes and cited fact
     numbers), then this step's retrieved facts, then the step. Reply as JSON: result, cited fact numbers, note.
   - Write r_i, n_i and the edges; link r_i to a graph entity.
3. **Final** (1 call). The benchmark's own answer prompt, with the facts cited across all steps (latest version
   only, as today) and the working memory chain. The answer is scored exactly as today.

At most 1 + K + 1 calls per question (K = number of steps, capped at 4).

## Test

Graph: the empty-start document graph first (mode C 38% there, fast, cheap), then the full T-REx graph once its
fixed run is in. Haiku, 3 repeats per arm, same 100 questions, same scoring.

| Arm | What | Isolates |
|---|---|---|
| A | mode C, one call (today) | baseline |
| B | question layer (today's option) | the plan as retrieval seeds only |
| C | working memory, full | the method |
| C- | same steps and calls, but nothing written to the graph: the chain lives only in the prompt, and each step retrieves from the question alone | whether writing to the graph matters, or only answering in steps |

Reported per arm: accuracy (mean and spread over 3 repeats), gold fact in the final facts, calls, tokens and time
per question, cost. Plus 10 questions traced by hand: the chain each arm wrote, and where it went right or wrong.

Kept only if C beats A by more than its repeat spread **and** beats C-; if C only matches C-, the gain is from
answering in steps, not from the graph, and that is what goes into the Memory routes instead.

Cost estimate: a one-call pass costs about $0.03 per 100 questions; C and C- make about 5 calls, so about $0.15 per
repeat, about $1 for all arms and repeats on one graph, cap $3.

## Implementation notes

- New `my_method/working_memory.py` (the loop, writing and reading the work layer); `agent.py` calls it when
  `method_config.working_memory: true` (arm C) or `"prompt_only"` (arm C-).
- Questions run in forked workers, each with its own copy of the graph, so work layers never mix.
- The no-facts stop check applies to every step's retrieval.
