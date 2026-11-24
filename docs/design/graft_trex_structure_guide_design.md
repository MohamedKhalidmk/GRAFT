# T-REx as a structure guide, not an answer source (design, for review)

> IDs ([registry](../reference/REGISTRY.md), 2026-11-21): arm A = G08, arm B (the guide) = G35, arm C (bridge) = G36, arm D (background) = G37, arm E (guide + working memory) = G38.

Test 06 in GRAFT alone. No code yet.

## Why

Test 04: with T-REx facts in the graph, two thirds of the 50 fact slots went to T-REx sentences. The edited document facts were
crowded out, and a few T-REx facts contradicted the gold (test 04 run-02 analysis). The idea: keep what T-REx knows about how
facts connect, and never let a T-REx fact reach the answering model.

## What gets extracted from T-REx (once, a CPU job, no LLM, $0)

From the original full T-REx base already on Fir (1,215,416 facts, 45 Wikidata properties), one file `trex_guide.json`. It holds
only properties, types and counts, no (subject, object) pairs:

1. **Relation list.** The 45 property IDs, labels and Wikidata aliases (e.g. P413 "position played on team / speciality", aliases
   "plays the position of", "position").
2. **Type signatures.** For each property, the most common entity types of its subjects and objects, from P31 instance of and
   P279 subclass of, rolled up to about 30 coarse types (human, sport, country, city, organisation, creative work, language,
   religion...). Example: P413 goes from human to position; P641 goes from anything to sport; P495 goes from work or sport to
   country.
3. **Chain statistics.** Counts of 2-hop and 3-hop property chains, where the object of one fact is the subject of the next
   (P413 then P641, P641 then P495). They are stored as P(next property | property, type of the middle entity), with the top
   chains per starting type.
4. **Relation shape.** Whether each property usually has one value per subject (P27 citizenship, P19 birthplace: one) or many
   (P161 cast member). Inverse pairs (P150 contains / P131 located in, P527 has part / P361 part of).
5. **Name to type, for linking only.** For each T-REx entity name, its coarse types. This is the only entity-level part. It
   says what kind of thing a name is, never what it relates to.

**Step 0, coverage check (free, before anything else).** FactConsolidation uses some relations outside the 45 kept in the base:
continent, author, founder, religion, chief executive, manufacturer, original broadcaster, notable work, official language.
Step 0 parses the 100 questions with the existing question parser (test 05 arm B's logged parses if they are complete, otherwise one parse pass, about $0.01) and maps each
relation to a property. It reports how many chains the guide covers. If coverage is low, the counts in 2 to 4 are redone over
the raw T-REx dump for those extra properties (CPU job, still free).

## Where it is used

**Linking (while the document graph is built).** GRAFT builds its graph from the documents only, as in arm A. The guide is a
post-pass over that graph, with no LLM:

- **Relation canonicalisation.** Each relation label the writer produced ("origianl broadcaster", "original network") is mapped
  to one property by embedding similarity to the property labels and aliases. The type signature of its subjects and objects
  then confirms or rejects the match. Labels with no confident match stay as written. Then revisions are recomputed on
  (subject, property). Two versions of one fact written with different labels now become one chain, and "the newer fact wins"
  holds.
- **Same-entity decisions.** Two document names are merged only if their types agree. The type comes from the T-REx name lookup
  or from the relation signatures (a name that is the subject of P413 is a human). Merges with conflicting types are refused, and
  every merge is logged.

**Planning (at question time).** The question parser runs as in the question layer (one Haiku call per question, already in
test 05 arm B). Its relation labels are mapped to properties the same way. The guide then:

- scores the parsed chain: type agreement between hops, and how common the chain is in T-REx. If the parse is unlikely (e.g. a
  middle hop type that never starts the next relation), it picks the most common chain that starts from the question entity's
  type and ends in the type the question asks for ("which continent", "what language").
- **follows the plan through the document graph.** From the question entity, it takes the current (newest) document fact with
  the first property, moves to its object, takes the current fact with the second property, and so on. These chain facts go
  first in the 50 slots. The rest are filled by mode C retrieval as now. Facts on the planned properties get a higher
  PageRank weight.

**Never.** No T-REx fact, sentence or entity is added to the graph or the prompt. The answering model sees only document facts,
with the same prompt as arm A. The guide's relation names go only into the internal plan, never to the answering call.

## Arms (the same 100 FactConsolidation multi-hop questions, Haiku, 256-token answers, 3 repeats each)

| Arm | Graph | Guide | Facts returned |
|---|---|---|---|
| A | empty start, documents only | none | documents (mode C) |
| B | empty start, documents only | linking post-pass + planning | documents: planned chain first, then mode C |
| C | the full T-REx graph from test 04 (original) | none | documents only |

Arm C is the bridge test. T-REx edges stay in the PageRank walk at weight 0.2 (document edges 1.0), and only document facts can
be selected. It reuses the test 04 graph and saved node vectors, so no rebuild.

A is rerun in the same job as B (same code) rather than reusing 34.7, because retrieval varies from run to run
(baseline_check.md in test 05). Optional, about $0.10 each: B-link (post-pass only) and B-plan (planning only), to see which part
helps.

Keep rule: B (or C) is kept if it beats A by more than the repeat spread.

## Cost and time

| Step | Where | API cost | Time |
|---|---|---|---|
| Guide extraction + step 0 | Fir CPU | $0 to $0.01 | 30 to 60 min |
| Code (guide, post-pass, planner, weighted walk, document-only filter) + unit tests | Mac (small tests only) | $0 | 4 to 6 h |
| A and B, 3 repeats each | Fir CPU | about $0.08 (A) + $0.12 (B, parser + answer) | about 30 min each |
| C, 3 repeats | Fir CPU (1.58M-node graph) | about $0.08 | 3 to 5 h, with a 6 h limit |
| Total | | about $0.30, with a $1 cap per job (about $0.50 with both optional arms) | about a day |

All spend is logged in docs/reference/run_log.md. Keep the halt check (stop if most questions get no facts) in every job.

## Risks

- The guide may barely change the documents' graph. FactConsolidation labels are fairly regular, so canonicalisation may merge
  little; step 0 and the post-pass log show this before any paid run.
- Planning that follows a wrong chain could push correct facts out. The planned chain takes at most the first 10 slots, and
  mode C fills the rest.
- The T-REx type lookup is real-world knowledge about names. It says what kind of thing a name is, never a relation value, so
  it cannot contradict an edited fact.
