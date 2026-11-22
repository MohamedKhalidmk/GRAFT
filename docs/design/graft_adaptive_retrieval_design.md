# Adaptive retrieval: how many facts to show (design, 2026-11-22)

> IDs ([registry](../reference/REGISTRY.md)): baseline **G35** (the T-REx guide on mode C, fixed 50 facts). New candidates
> **G39** (drop cutoff) and **G40** (drop cutoff, then Qwen asks for more). Idea and keep rule from the user, 2026-11-22.

## Question

G35 always shows the answering model 50 facts. On some questions 10 would do, on others the gold sits past 50. Does a
fact count chosen per question, from the shape of the ranking or by asking the model, answer better, or as well with
fewer facts?

## G39: drop cutoff

1. Rank exactly as G35 does (guide plan first, then mode C), but keep a pool of up to 200 facts instead of 50.
2. Give each pooled fact a score from the ranking itself, so the order is G35's and only the count changes:
   - graph questions: the fact's mass in mode C's second PageRank walk (the walk from GOAt's picks); facts the walk
     never reached score 0;
   - fallback questions (no entity linked: embedding search): the fact's cosine similarity to the question.
3. Sort the pooled scores in descending order and cut at the largest drop between neighbours, measured as a ratio
   (the largest `log s[i] - log s[i+1]`), searched between position `min_facts` and `drop_max`. No threshold to tune.
4. Show the first k facts of G35's order, where k is that cut (never below the number of guide-planned facts).
5. Bounds, set now: `min_facts` 10, `drop_max` 100. Pool 200.

## G40: drop cutoff, then Qwen asks for more

1. Start from G39's k facts.
2. The answer prompt gains one rule: if the memories lack a fact needed to answer, reply exactly
   `NEED MORE MEMORIES` and nothing else; if no memory could hold the answer, say that the memory does not hold it.
3. On `NEED MORE MEMORIES`, add the next 50 facts of the pool and ask again.
4. Limits: at most 3 asks; at most 200 facts shown; stop when a batch adds nothing new (pool used up). A reply that is
   still `NEED MORE MEMORIES` after the limits is the final answer (scored wrong).
5. Logged per question: asks, facts shown, LLM calls, LLM seconds.

## Parts (registry columns)

Same as G35 in every column, plus a new column **Fact count**: G35 fixed 50; G39 drop cutoff (10-100, pool 200);
G40 drop cutoff + asks (up to 3 x 50, cap 200).

## Test (GRAFT test 09)

- **Benchmark:** FactConsolidation multi-hop 262K, 100 questions, the empty-start graph (the gold is in the graph for
  almost every question, so the count is what varies).
- **Free first:** gold-in-facts (`answer_in_retrieved`) for G35 at 50, G39, and G35's pool at 200 (the ceiling), in
  fake mode on a CPU node. G40's asks need a real model, so its free check is G39's set plus the pool ceiling.
- **Then Qwen** (Qwen3.8-27B W4A16, local vLLM, free), 1,024-token answers, 3 repeats each, one repeat per job:
  G39, G40, and G35 the same day (the queued test 08 run-02 G35 jobs count if they run the same day).
- **Reported:** accuracy (mean, spread over repeats), facts shown per question (mean, distribution), asks per question
  (G40), and GPU-seconds (job GPU time per question, plus LLM seconds from the gateway logs).

## Keep rule (user, set 2026-11-22, before any result)

Keep a new candidate if it beats G35 by more than the repeat spread, or matches it with clearly fewer facts. "Matches"
= within the repeat spread; "clearly fewer" = at least 30% fewer facts shown per question on average (proposed here,
to confirm with the user before the result).

## Order

Runs in parallel with the LongMemEval writer fix ([graft_writer_fix_design.md](graft_writer_fix_design.md)); the
writer fix goes first if GPUs are short.
