# Guided graph + passage index (design, 2026-11-22)

> Status: design only (user, 2026-11-22); nothing built or run. New IDs: G49, G50, G51 (arms), setups S171-S178.
> Runs after the G41 rebuild (LongMemEval dev), then in the past-the-context-window test
> ([graft_long_history_design.md](graft_long_history_design.md), part 2).

## Why

Flotilla's error stages on run-04 (fact level) and the 20-case study put most Memory-route misses upstream of Qwen:
the gold answer is inside the 50 facts shown on only 165 of 440 LongMemEval questions, and in the 20 cases the needed
fact was either never written as a fact (10) or written but ranked out (7). Facts are lossy: a count, a link, a price,
one item of five often stays in the conversation and never becomes a triple. Showing the passages the found facts came
from gives Qwen the original wording around each fact, while the guided graph still decides where to look.

## What is borrowed and what is ours

- **Borrowed, HippoRAG 2** (Gutiérrez et al., "From RAG to Memory: Non-Parametric Continual Learning for Large Language
  Models", arXiv 2502.14802, 2025; https://github.com/OSU-NLP-Group/HippoRAG): passages as nodes of the knowledge
  graph, linked to the phrases (entities) they contain; Personalized PageRank over the combined graph with the
  question's matched triples as seeds and a small weight on dense passage similarity; damping 0.5; the passages,
  not the triples, go to the reader. Credited in REFERENCES.md (`hipporag`). The BM25 arm uses Robertson and
  Zaragoza's BM25 (`bm25`).
- **Ours, kept as they are:** the T-REx structure guide (question parsed into a relation chain, the walk follows the
  guided relations), the GNN + GOAt ranking (mode C), supersede (the newest version replaces a fact; outdated
  versions are marked), and time (each fact's session date; event time if G46 is kept). New and ours: the
  fact-to-passage link through the fact's source sentence, passages ordered by the guided ranking of their facts, and
  outdated marks carried from facts to passages.

## Passages

- **Unit:** one turn of a session, split at sentence boundaries into pieces of at most 256 tokens when longer
  (assistant turns often are); every passage starts with its session id, date and speaker. HippoRAG 2's passages are
  paragraphs of about this size; a whole session (GRAFT's chunk, about 2,300 tokens in LongMemEval S) would fill the
  budget with two or three sessions.
- **Fact to passage:** each fact already keeps `chunk_id` (its session chunk) and `span` (its source sentence). The
  passage is the one inside that chunk that contains the span; when the writer reworded the span, the passage with the
  largest word overlap with it, and the link is marked approximate. The link rate (exact, approximate, none) is
  reported per arm.
- **Built without any model call** from the stored histories and the G41 graphs; passage embeddings (bge-small, the
  embedder of every GRAFT run) only for G50's dense seed.

## Arms (same passage token budget)

| ID | Arm | What Qwen sees | Ranking |
|---|---|---|---|
| G41 (G35's rule) | current guided facts | 50 facts (subject, relation, object, source sentence, date, outdated mark), as row 24's fixed-50 arm | guide plan, then mode C (GNN + GOAt) |
| G49 | guided + passages | the passages of the found facts, up to the passage budget, in the order of their best fact; each passage dated, with "contains an outdated fact: ..." when one of its facts is superseded; then a short fact summary: the facts behind the shown passages (at most 30, with dates and outdated marks) | the same guided ranking as G41; passages taken in fact order, duplicates dropped |
| G50 | HippoRAG 2-style passages, no guide | passages up to the budget, dated, with the same outdated marks (from GRAFT's supersede edges) | HippoRAG 2 on GRAFT's G41 graph: passage nodes added, linked to the entities of their facts; seeds from the question matched to facts by embedding (top 5, HippoRAG 2's query-to-triple step) and to passages by dense similarity (weight 0.05); PPR damping 0.5; passages ranked by PPR. No guide, no GNN |
| G51 | BM25 over the same passages | passages up to the budget, dated, no marks | BM25 on the question |

G49 against G50 measures the guide (and GOAt) with passages; G50 against G51 the graph against plain lexical search;
G49 against G41 the passages themselves. G50 keeps GRAFT's outdated marks so that only the ranking differs from G49;
a strict HippoRAG 2 (its own OpenIE graph, no supersede) is the existing GRAFT baseline (S79-S85) and can be added
later as a reference if wanted.

## Reading (G53, user 2026-11-22)

G49's passages are the starting point, with the same 4,096-token starting budget. While asks remain, the benchmark's
question is followed by the reading rule (`my_method/prompts/passage_reading.v1.md`): if a passage seems cut off or
something is missing, Qwen may reply with only `OPEN P<n> AROUND` (the passages just before and after P<n> in its
chunk or session) or `OPEN P<n> SESSION` (the rest of that chunk or session, in order), at most 3 lines per reply.
Each line adds at most 1,024 tokens, never repeats a shown passage, and the added passages are numbered on after the
shown ones (so they can be opened in turn) and carry outdated marks like the rest. At most 3 asks; after the third,
or after a reply that is not a request, the plain question is answered. A reply is a request only when its last
non-empty line is an OPEN line. Every added token is counted: the log keeps each ask's lines, passages and tokens, and
the tokens shown are those of the context on the final call. Tests with scripted replies; a toy check on real Qwen
(first 10 FactConsolidation questions) before any run.

On FactConsolidation a chunk is about two passages, so AROUND and SESSION mostly add the same neighbouring slice; on
LongMemEval, AROUND is the neighbouring turns and SESSION the rest of the session.

The budget control G52 (G35's fact lines until their source text reaches 4,096 tokens) separates "more text" from
"passages" when G49 is compared with G35.

## Budget (proposed)

- **Passages:** 4,096 tokens for G49, G50 and G51 (16 passages of at most 256 tokens; fewer when longer passages
  fill it). G49 adds its fact summary (at most 30 facts, about 900 tokens), reported apart.
- **G41:** 50 facts as today (its 5,120-token cap; about 2,000-3,000 tokens in practice).
- **Why 4,096:** about twice what 50 facts take, small next to the 110,000-token full history, and large enough to hold
  the evidence of a multi-session question (2-4 sessions' worth of turns). If gold-in-context stays low at 4,096, an
  8,192 run of the best passage arm is the follow-up, as its own candidate.

## Runs and reporting

1. **LongMemEval S dev (76 questions), after the G41 rebuild:** the four arms through Flotilla's Memory route with base
   route Fast (as row 24), on the G41 graphs, 3 repeats each, all the same day. Haiku judge with the official prompts,
   majority of 3, the fixed Haiku check first. Setups S171-S174.
2. **Past the context window (LongMemEval M pilot, 40 dev questions, part 2 of the long-history design):** the same four
   arms on the M graphs that design builds, against full reading under the truncation rule, and the same 40 questions
   on S as the reference. Setups S175-S178.
3. **Reported per arm:** accuracy with the spread; gold-in-context (the normalised gold inside what Qwen saw, the
   fact-level rule of Flotilla's error stages, and the evidence-session coverage); tokens shown (passages, summary,
   total); the fact-to-passage link rate; compute: retrieval seconds, Qwen prompt and output tokens, GPU-seconds per
   question; and the error stages (PROTOCOL 7.1) per arm.

No keep rule is set here; it is set with the user before the first result, as for every candidate.

## Cost

- **Building:** no model calls (passages from the stored histories, links from the stored spans); embeddings for G50
  about a minute per history on a GPU.
- **Answering (free, our GPUs):** LongMemEval S: 12 runs (4 arms x 3 repeats) of 76 questions; prompts grow from about
  3,000 to about 5,000 tokens, so about 1 slice GPU-hour per run with retrieval, about 12 slice GPU-hours in all. The M
  pilot adds about 4 slice GPU-hours on top of the M builds already in the long-history design (25-30).
- **Judge (paid):** S: 912 answers x 3 Haiku calls, about $0.08, plus the Haiku check $0.03; M: 480 answers x 3 calls,
  about $0.05. **About $0.16 in all**, the only extra money.
