# Project history: Flotilla and GRAFT

A study document. It goes through both projects from the first commit to 2026-11-21, in order: what each test asked,
what we expected, what happened, what broke, how it was fixed, and what we decided. Every number links to the table it
comes from. Where a number has no table yet, the link goes to the run log entry that records it.

Two repos, one story:

- [**GRAFT**](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/README.md) is the thesis project: a revision-aware graph memory for LLM agents. Facts keep their
  source and time, and a newer fact supersedes an older one instead of overwriting it.
- [**Flotilla**](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/README.md) is a compound system built on one open model (Qwen3.8-27B, 4-bit). A router picks a
  route per question: answer fast, think long, use tools, vote, or recall facts from GRAFT.

How to read the links: Flotilla paths are under `github.com/MohamedKhalidmk/Flotilla` (branch `restructure`), GRAFT
paths under `github.com/MohamedKhalidmk/GRAFT` (branch `graft-linking-hybrid`; its `main` holds the same work up to
PR #6). The run logs are Flotilla's [docs/reference/run_log.md](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/run_log.md) (decisions and API spend, from 2026-11-19)
and GRAFT's [docs/reference/experiments.md](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/reference/experiments.md) (the 2026-11-13 real runs).

**IDs (2026-11-21).** Every candidate has a frozen ID: GRAFT G01-G38, Flotilla F01-F28; every result points to a setup (S01-S146) that adds the answering model, cap, benchmark and scoring. Registries: [GRAFT](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/reference/REGISTRY.md), [Flotilla](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/REGISTRY.md). Old names below are kept as they were used at the time; the main ones: mode A = G04, B = G07, C = G08, D = G09; the guide = G35; bridge = G36; background = G37; guide + working memory (arm E) = G38; working memory C/C- = G31/G32 (v1) and G33/G34 (v2); question layer = G30; RoG = G25; full T-REx = G27-G29. Flotilla: plain Qwen (bare) = F01; Qwen alone = route Deep+Tools = F06; gpt-oss = F07; Command A+ = F08; routes Fast F15, Tools F16, Deep F17, Vote F18, Vote+Tools F19, Memory F20-F23; router A F12, router B F13, router B lite F14.

Contents

1. Timeline at a glance
2. GRAFT, test by test
3. Flotilla, test by test
4. Every decision and its reason
5. Tools and libraries
6. Clusters, jobs, scripts and configs (how to rebuild)
7. Every bug, and its fix
8. Spend by date
9. Methods in plain words
10. Mistakes and lessons
11. Interview questions, with answers
12. What is open, and the exact next steps

---

## 1. Timeline at a glance

| Date | GRAFT | Flotilla |
|---|---|---|
| 2026-10-29/30 | Test bench built (called SGAR then): MemoryAgentBench as a submodule, a Claude gateway, baselines, the graph memory, a GCN trained on synthetic worlds, GOAt explanations. Fake mode only, no API money. | |
| 2026-10-30 | The GNN's 400-node subgraph is chosen by PageRank instead of by distance (hubs were filling it). | |
| 2026-11-13 | First real runs with Claude Haiku 5.5: read orders A, B, C, D, BM25, HippoRAG 2 (test 01). Mode C is 38%. | |
| 2026-11-15 | Renamed SGAR to GRAFT, MIT license (later Apache-2.0). | |
| 2026-11-19 | EiG-Search added as a second explainer. | Protocol written and frozen (v1 to v9 in one day). Quantization test (test 01). Router pool built and leakage-checked. Router A measured. |
| 2026-11-20 | Retrieval variants (test 02), RoG base (test 03), full T-REx base (test 04) with the PageRank and "THE" bugs, working memory round 1 (test 05). | Model small test (test 02), Command A+ and gpt-oss dropped (tests 02, 03). Strategy router labels for six routes (test 04), grader and verifier bugs found and fixed, labels regraded (run-03). |
| 2026-11-21 | T-REx base not adopted. Haiku drift found (test 07). Working memory round 2. T-REx as a structure guide: 45.7 vs 34.7, then 46.0 vs 34.0 on the same day (test 06), the new default. Restyle merged to main (PR #6). | Memory-route code, router code, live-RL code. LongMemEval downloaded and leakage-checked. Labelling on LongMemEval started. |

---

## 2. GRAFT, test by test

The benchmark for all of GRAFT's tests is MemoryAgentBench's FactConsolidation multi-hop split at 262K tokens: 100
questions whose answers depend on facts that were edited later in the documents. The documents are 537 chunks of a
long list of numbered facts; a fact with a larger serial number is newer and wins. Scoring is substring exact match
(the gold answer appears in the model's answer). The answering model is Claude Haiku 5.5 (`claude-haiku-5-5`) unless
stated.

### 2.0 Before the tests: the bench and the first design fix (2026-10-29/30)

**Why.** To compare a graph memory against the systems in the MemoryAgentBench paper (long context, BM25, HippoRAG 2,
Mem0, Letta) under the same conditions.

**Setup.** The benchmark code is the authors' repo as an unmodified git submodule (commit `5380260`). A local gateway
gives every system the same Claude settings, the same embedding model, and one usage log
([USAGE.md](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/USAGE.md), "How it fits together"). Baselines run from the benchmark's bundled copies and from
upstream versions. GRAFT's GNN never trains on MemoryAgentBench or MQuAKE, because FactConsolidation contains nearly all
MQuAKE-CF facts. It trains on invented "synthetic worlds" with revisions (only the relation templates are shared) or on
WebQSP and CWQ.

**What broke.** The GNN could only look at 400 nodes, because GOAt's cost grows with graph size. Those were the 400
nodes nearest the question's entities, so hubs like "United States of America" (1,281 links) filled the slots. The
answer was inside the 400 for 42 of 100 questions, against 99 of 100 with no limit
([USAGE.md change log](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/USAGE.md)).

**Fix.** Choose the 400 nodes by Personalized PageRank (PPR) from the question's entities over the whole graph. A random
walker splits its steps across a node's links, so hubs pass on little to each neighbour. In a fake-LLM check at 50
facts, GNN + GOAt reached 57 on multi-hop against 48 for PageRank alone. That check used the gold answers to find the
cause, so it is a diagnosis, not a result.

**Decisions.** Every method answers with Claude Haiku 5.5. No API money until the user says so; everything is tested in
fake mode first.

### 2.1 Test 01: read order and starting graph (2026-11-13)

Folder: [test-01-read-order](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/README.md),
table: [table.csv](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv).

**Why.** GRAFT reads in three stages: PPR, the GNN with GOAt, and the final ranking. The order was a guess. Also: does
starting from a ready-made synthetic graph (D) help?

**Expected.** C (PPR, then GNN + GOAt, then a short second PPR from GOAt's picks) to do best, since it combines a wide
walk with the GNN's focus.

**Setup.** Haiku writes the graph once from the 537 chunks (empty start; D extends a synthetic graph). 100 questions,
50 facts per answer. BM25 and HippoRAG 2 under the same conditions.

**What happened.**

| Variant | 16-token answers | 256-token answers | Gold reached the model |
|---|---|---|---|
| A | [15](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | [37](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | [51](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) |
| B | [13](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | [37](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | 51 |
| C | [17](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | [**38**](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | 51 |
| D | [22](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | [37](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | 44 |
| BM25 | 1 | [4](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | 32 |
| HippoRAG 2 | 0 | [15](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-01-read-order/table.csv) | not recorded |

**What broke.** The first answers were capped at 16 tokens, the paper's setting. Haiku often had not reached the answer
by then, so the 16-token gaps were cut-off answers, not real differences. Rerun at 256 tokens. HippoRAG 2 at 2,048
tokens scored 14, the same within noise ([experiments.md](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/reference/experiments.md)).

**Decision.** Mode C (`ppr_goat_ppr`) is the default, answers capped at 256 tokens. A, B, C and D are within a point,
and the gold fact reaches the model on only about half the questions, so retrieval is the limit.

Note added later (test 07): the 38 is one run. Six repeats a week later give 34.7. See 2.7.

### 2.2 Test 02: retrieval variants on mode C (2026-11-19/20)

Folder: [test-02-retrieval-variants](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-02-retrieval-variants/README.md),
table: [table.csv](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-02-retrieval-variants/table.csv).

**Why.** Since retrieval is the limit, does anything added to mode C bring more gold facts and more right answers?

**Setup.** A free check first (is the gold answer in the subgraph, and in the final 50 facts, with a fake LLM), then
paid repeats only for variants that beat the baseline on the free check. This rule saved money and kept tuning honest.

**What happened.**

| Variant | Result | Decision |
|---|---|---|
| EiG-Search instead of GOAt | 36% vs 37% (one question), 2.6 times faster | GOAt stays (rule 4.3 needed 37 and faster, or 40) |
| Embedding entity linking, k=5 | gold present fell from 51% to 22-25% (free) | rejected |
| 50/50 hybrid with embedding search | 3 repeats, 32.0% vs 38% | not adopted |
| Top-10 hybrid | 3 repeats 33/31/29 vs 38 | not adopted |
| Question graph (Haiku parses the question into edges) | 3 repeats 39/37/35, mean 37.0 | not adopted |
| 800 and 1,600-node subgraphs, a retrained 1,600-node GNN | gold in final 48% vs 51% (free), 10 times slower | not adopted |

All rows: [table.csv](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-02-retrieval-variants/table.csv) and the
[run log](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/run_log.md) entries of 2026-11-20.

**What broke.** The first paid batch lost 3 of 6 jobs at start: jobs that started in the same second got the same run
folder. The first question-graph run crashed after its 100 parse calls, because texts were not embedded before the
worker processes forked. Both fixed, with a test that fails on the old code.

**Lesson inside the result.** The hybrids raised "gold present" (51 to 54-55%) and still lost accuracy. Embedding
near-misses distract the answer model. More recall is not the same as better answers.

**Decision.** Mode C with GOAt stays.

### 2.3 Test 03: base graph from RoG, Freebase (2026-11-20)

Folder: [test-03-base-graph-rog](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-03-base-graph-rog/README.md),
table: [table.csv](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-03-base-graph-rog/table.csv).

**Why.** GRAFT's design has three layers: a base of general knowledge, the documents on top, and the question and work
layer. Does a base help?

**Setup.** 20,000 leakage-checked RoG-WebQSP/CWQ Freebase facts. Leakage drops: 5,577 touching a question's topic
entity, 487 identical to a document fact. Haiku writes the documents onto the base and links each new name to the base
(the 10 nearest names by embedding, Haiku picks one or "new").

**What happened.** Haiku matched 21.9% of document names to a base entity (13.3% by exact name). 79% of document facts
touched a base entity, almost all through hubs (USA, football, Catholicism). Gold in final facts
[41%](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-03-base-graph-rog/table.csv) (42% in the free check), accuracy
[21%](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-03-base-graph-rog/table.csv), one run.

**Decision.** Not adopted: a small off-domain base mostly adds hub noise to PageRank.

### 2.4 Test 04: base graph from full T-REx, Wikidata (2026-11-20/21)

Folder: [test-04-base-graph-trex-full](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-04-base-graph-trex-full/README.md),
table: [table.csv](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-04-base-graph-trex-full/table.csv).

**Why.** RoG was small and off-domain. FactConsolidation's facts come from Wikidata, so a large Wikidata base should
overlap the documents.

**Steps and what broke along the way.**

1. A first T-REx slice was built with the columns in the wrong order: (relation, head, tail) read as (head, relation,
   tail). Caught, rebuilt with English Wikidata labels for the 45 most common properties.
2. A dense-core slice (100,000 facts) overlapped only 11.6% of document names: the core is hubs, the documents name
   long-tail entities. Not used.
3. The user chose the full T-REx base on 45 properties: 1,215,416 facts, 344,996 entities, 55.8% exact-name overlap.
4. The Haiku-linking build ran 537 chunks for $1.76 and matched 62.8% of names. The first attempt had no checkpoints and
   was cancelled at chunk 55 ($0.52); checkpoints every 75 chunks were added.
5. **Bug: every answer pass scored 0.0.** NetworkX PageRank stopped after one step on the 1.58M-node graph, so the
   subgraphs held no facts (section 7). Fixed with a stop rule that holds on big graphs.
6. **Bug: "THE".** A T-REx entity named "The" matched 89 of 100 questions (section 7). Fixed with a rule: a name that is
   a single stopword is never linked.
7. A cleaning pass was tried. The first rule was too wide (it would have dropped 130,033 facts hanging on real concepts
   like "footballer"). Narrowed, then the user chose the original, uncleaned graph: the dropped items were mostly real
   facts, and the linking rule already fixed "THE".
8. **Bug: jobs stuck at start.** Imports from Fir's project filesystem took 7 to 30 minutes (section 7). Fixed by
   copying code and an unpacked venv to the node's local disk.

**What happened** (Haiku, 3 repeats each, original graph):

| Pass | Accuracy | Gold in final facts |
|---|---|---|
| EiG | [17.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-04-base-graph-trex-full/table.csv) (18/15/20) | [33.3](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-04-base-graph-trex-full/table.csv) |
| GOAt | [19.0](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-04-base-graph-trex-full/table.csv) (2 repeats; the third hit the job limit) | 34.0 |
| Question layer + EiG | [17.0](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-04-base-graph-trex-full/table.csv) | 28.0 |
| Reference: mode C, empty start | [34.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv) | 50.7 |

**Why it failed** ([analysis](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-04-base-graph-trex-full/runs/run-02/analysis/why_accuracy_halved.md)).
T-REx facts are whole Wikipedia sentences and took about two thirds of the 50 slots. In 10 checked failures, 7 were
crowding out (the edited, newest document fact on the chain was pushed out), 2 were a T-REx fact contradicting the
gold (Sanskrit vs English for Valmiki), 1 was Haiku's real-world prior.

**Decision.** Not adopted. GRAFT keeps the empty-start document graph.

### 2.5 Test 05: working memory in the graph (2026-11-20/21)

Folder: [test-05-working-memory](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/README.md),
table: [table.csv](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv),
design: [graft_working_memory_design.md](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/design/graft_working_memory_design.md).

**Why.** The user's idea: GRAFT is not only retrieval over stored facts, it can also be the agent's working memory.
Answer in steps, write the question, sub-steps, notes and partial results into the graph, and read them back.

**Expected.** Arm C (steps written into the graph) above A (one-shot mode C) and above C- (the same steps kept in the
prompt only). Keep rule: C must beat A by more than its repeat spread, and beat C-.

**What happened.**

| Arm | Round 1 | Round 2 (newer-fact rule in the step prompt) |
|---|---|---|
| A, mode C | [34.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv) | [34.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv) (same-day rerun) |
| B, question layer | [33.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv) | |
| C, working memory in the graph | [35.3](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv) | [35.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv) |
| C-, same steps, prompt only | [32.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv) | [33.0](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-05-working-memory/table.csv) |

Traces from round 1 showed C winning on edited multi-hop chains and losing where a step took the older of two
conflicting facts. So round 2 added "the larger serial number is newer and counts" to the step prompt. It moved C by
only 0.4.

**Decision.** Not kept on Haiku: about 1 point over A, inside the spread, at about three times the cost per question.
Writing the steps into the graph beats keeping them in the prompt by 2.6 to 2.7 points in both rounds. That part is
real, and it is why arm E (2.6.1) combines it with the guide. On Qwen the gap does not show (C v2 33.3, C- v2 33.0; [test 08](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-08-graft-on-qwen/README.md)).

### 2.6 Test 06: T-REx as a structure guide, a bridge, or background (2026-11-21)

Folder: [test-06-trex-structure-guide](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/README.md),
table: [table.csv](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv),
design: [graft_trex_structure_guide_design.md](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/design/graft_trex_structure_guide_design.md).

**Why.** Test 04 showed T-REx facts crowd out the documents. The user's idea: keep what T-REx knows about how facts
connect, and never show a T-REx fact to the answering model.

**The arms.**

- **B, structure guide.** From T-REx, keep only relation labels, coarse entity types, which types each relation
  connects, how often relation chains occur, and each name's type. No (subject, object) pair. Use it for:
  - linking: map the writer's relation labels to one Wikidata relation, so versions of one fact written with different
    labels become one revision chain; merge name variants only when their types agree;
  - planning: follow the question's relation chain through the document graph, newest fact at each hop, bridging one
    hop when the documents spell it differently; those facts go first (at most 10), mode C fills the rest.
- **C, bridge.** T-REx edges stay in the PageRank walk at weight 0.2, only document facts are returned.
- **D, background.** C plus 5 T-REx facts shown apart, labelled as background, with the rule that the knowledge pool
  always wins.

**Free steps first.** The 45-property base covered only 144 of 253 question relations. Rebuilt from the raw T-REx data
with 248 properties and aliases: 244 of 253 covered. A dry check with no LLM found linking added 1,012 missed revisions
and that a 0.91 cosine match wrongly joined "founded by" with "founded in city"; labels now join only at 0.92 or above.
The planned chain held the gold answer for 44 of 100 questions.

**What broke.** The guide job died copying code (tar exit 1, "file changed as we read it", other jobs' logs being
written); the bridge job ran out of memory at 64 GB. Both fixed, both at $0 (section 7).

**What happened.**

| Arm | Run-01 | Same-day confirmation (run-02) | Gold in final facts |
|---|---|---|---|
| A, mode C | [34.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv) | [34.0](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv) (34/34/34) | 50.3 / 50.7 |
| **B, guide** | [**45.7**](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv) (47/46/44) | [**46.0**](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv) (46/43/49) | 60.3 / 60.0 |
| C, bridge | [17.3](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv) | | 32.0 |
| D, background | [17.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv) | | 33.0 |

**Decision.** The guide is GRAFT's new default (user, 2026-11-21): +11 and +12 points, about seven times the repeat
spread. T-REx as facts hurts in every role tried, even walk-only.

#### 2.6.1 Arm E: guide plus working memory (parked, not dropped)

The guide's planned chain is cited from the first working-memory step, then the steps run as C v2. Compared with a
same-day rerun of the guide alone, 3 repeats each (run-03, Fir 4874611 and 4874613): E [46.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv)
(50/45/45) against the guide alone [46.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-06-trex-structure-guide/table.csv) (48/47/45), at about twice the cost
($0.079 vs $0.036 per 100 questions); gold in the final facts 55.7 vs 60.7.

**Decision.** Parked, not dropped (user, 2026-11-21): a tie on Haiku, and in test 05 steps written into the graph beat
the same steps in the prompt by about 2.6 points in both rounds, so working memory stays a candidate. Arm E on Qwen,
against a guide rerun in the same job, is [test 08](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-08-graft-on-qwen/README.md) run-02.

#### 2.6.2 GRAFT on Qwen (test 08)

The same arms with Qwen3.8-27B W4A16 answering (local vLLM on a 3g.40gb MIG slice, Nibi 28263641, free): mode C
[39.3](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-08-graft-on-qwen/table.csv), the guide [47.0](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-08-graft-on-qwen/table.csv), C v2 33.3, C- v2 33.0.
The guide carries over (+7.7). Qwen reasons in its answers, so 35% (mode C) and 26% (guide) of them reached the
256-token cap: the one-call arms' absolute numbers are lower bounds, compared fairly within Qwen. The run folders are
named after the failed job 28252727 because the rerun resumed its empty folders; `eval/run.py` now resumes only the
same job's folder (section 7).

### 2.7 Test 07: Haiku drift and the fixed check (2026-11-21)

Folder: [test-07-haiku-drift](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-07-haiku-drift/README.md),
table: [table.csv](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-07-haiku-drift/table.csv).

**Why.** Mode C scored 38 on 2026-11-13 and 34.7 a week later on the same graph. The four modes of test 01 all scored
37-38. The user did not accept "one lucky run" and asked for the exact old commit.

**Setup.** On one day: the exact 2026-11-13 commit (28d4fd5), today's code, and a replay where today's Haiku re-answers
the exact facts the 38 run retrieved, with no retrieval at all.

**What happened.**

| Run | Mean |
|---|---|
| 2026-11-13 run | [38](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-07-haiku-drift/table.csv) |
| The 2026-11-13 commit, rerun | [36.0](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-07-haiku-drift/table.csv) |
| Today's code | [34.7](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-07-haiku-drift/table.csv) |
| Replay of the 2026-11-13 facts | [34.3](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-07-haiku-drift/table.csv) |

Then every input was compared request by request: identical input token counts on 100 of 100 questions, same model
string, max_tokens, thinking off, endpoint, SDK (anthropic 2.8.0, installed before the 38 run), data and grader. Only
Haiku's answer choices differ ([baseline_check.md](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-07-haiku-drift/baseline_check.md)).

**Decision.** Compare only within one day. A fixed Haiku check (the replay, 1 repeat, about $0.027) now opens every paid
Haiku batch, and the gateway logs each call's request hash, message ID, API request ID and reply hash
([check history](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/experiments/test-07-haiku-drift/haiku_canary.md)). The first clean check scored 36.

Honest uncertainty: four 2026-11-13 runs averaged 37.3 and today's mode C runs average about 35, about two standard
errors. A real shift on the API side is possible and cannot be inspected from here.

---

## 3. Flotilla, test by test

### 3.0 The protocol (2026-11-19)

Flotilla's goal: a compound system of quantized open models, measured on the same benchmarks and settings as published
reference numbers (GSM8K, MATH-500, AIME 2025 and 2026, GPQA-Diamond, IFEval, MMMU, OCRBench, RULER 32K and 64K,
LiveCodeBench). The [protocol](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/PROTOCOL.md) fixes, before any scored run, the benchmarks, settings, splits and
every keep-or-drop rule. It went from v1 to v10, each a git tag, each change dated and made before the result it
affected.

Key rules: a 5% small test per benchmark (at least 20 items, seed 20261119) for every choice, the full benchmarks only
for the final run; 95% bootstrap intervals; a "win" only if our lower bound is above the reference; every token and
GPU-second counted. Excluded before any run: SWE-bench Verified (needs Docker, not allowed on the clusters), CanLegal
Bench (not public), MemoryAgentBench (kept for GRAFT only).

### 3.1 Test 01: quantization (2026-11-19)

[README](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-01-quantization/README.md), [table.csv](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-01-quantization/table.csv).

**Why.** 4-bit models are cheaper to serve. Does 4-bit lose accuracy?

**Rule 4.1.** 4-bit if within 1.0 point of 8-bit on MATH-500 (all 500, greedy, 131,072-token budget).

**What happened.** Qwen3.8-27B: BF16 [0.978](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-01-quantization/table.csv), FP8 ours
[0.984](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-01-quantization/table.csv), W4A16 ours [0.984](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-01-quantization/table.csv).
Phi-4-reasoning-plus: [0.824 / 0.820 / 0.786](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-01-quantization/table.csv), and it hit its 30,000-token
cap on 379 to 398 of 500 questions.

**Decision.** Qwen runs as our W4A16 build. Calibration data (ultrachat_200k, 512 conversations) passed the leakage
check (0 of 3,132 messages flagged).

### 3.2 Router A and the router pool (2026-11-19)

The router pool is 4,856 public training questions (math, science multiple choice, instruction following, code),
leakage-checked against every test set: 96 dropped, 4,760 kept
([report](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/reports/leakage/router_pool.json)). The strict 13-gram check had first flagged 648, almost all shared
template wording; protocol-v3 made the template rule explicit. Router A (vLLM Semantic Router's decision model plus a
fixed table) scored 0.744 routing accuracy on 500 clean pool items ([report](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/legacy/router_a_pool500.json)).

### 3.3 Test 02: model small test (2026-11-20)

[README](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-02-model-small-test/README.md), [table.csv](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-02-model-small-test/table.csv).

**Why.** Which solver models earn a place?

**What changed before the test (each a protocol version).** Phi was dropped for gpt-oss-20b at medium reasoning (24/25
vs 21/25 on a MATH-500 small set at a tenth of the tokens). Command A+ first ran through Cohere's hosted API on a free
trial key; the trial's monthly calls could not cover it, so it ran locally from the official FP8 on 4 H100s. All models
moved to native tool calls after smoke checks showed text tool lines failing.

**What happened** (362 dev questions, 11 benchmarks, full loop): Qwen [0.877](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-02-model-small-test/table.csv),
gpt-oss [0.772](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-02-model-small-test/table.csv) (9 text benchmarks), Command A+
[0.773](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-02-model-small-test/table.csv). Perfect router Qwen + gpt-oss
[0.910](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-02-model-small-test/table.csv), mostly from RULER 32K.

**Decision.** Rule 4.2: Command A+ dropped (minus Qwen [−0.104](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-02-model-small-test/rule_4_2.csv),
whole 95% interval below 0, on 4 GPUs against 1).

### 3.4 Test 03: router B, Qwen vs gpt-oss (2026-11-20)

[README](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-03-router-b-models/README.md), [table.csv](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-03-router-b-models/table.csv).

**Why.** gpt-oss led RULER 32K. Does a trained router between the two models gain at least 1 point over Qwen alone? The
user set the 1-point bar before the result.

**What broke.** Run-01 labels were broken: the label prompt offered tools but no tool loop ran, so 22 of 34 checked Qwen
labels ended at a tool line with no answer; code answers kept markdown fences. Relabelled through the real loop.

**What happened** (476 held-out): Qwen alone [0.895](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-03-router-b-models/table.csv), router B
(ModernBERT) [0.899](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-03-router-b-models/table.csv), bge + logistic regression
[0.887](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-03-router-b-models/table.csv), perfect router [0.941](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-03-router-b-models/table.csv).

**Decision.** gpt-oss dropped (protocol-v10). Flotilla runs Qwen alone, and test 04 asks whether choosing a strategy per
question helps instead.

### 3.5 Test 04: strategy router (2026-11-20 to now)

[README](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/README.md), [table.csv](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv).

**Why.** One model, many ways to use it. Fast (thinking off), Tools, Deep (full thinking), Deep+Tools, Vote (5 samples
at temperature 0.6, majority), Vote+Tools, and four Memory routes (GRAFT facts in the prompt with Fast, Deep, Vote or
Deep+Tools). Can a router pick per question and beat the best fixed route, or match it for less compute?

**Keep rule, set first.** Keep a router if it is within 1 point of the best fixed route at lower compute, or more than 1
point better.

**Labels.** 1,500 pool questions (910 math, 249 science multiple choice, 249 instruction, 92 code), never the small test,
full benchmarks, router B's held-out set or GRAFT's 100 questions. Every route answers every question. Split 1,015 /
217 / 218.

**What broke: grader and verifier bugs.** The first full labels gave 0.825 to 0.899. A hand check of the 69 questions
every route got wrong found that only about 11 to 15 were Qwen's errors (section 7 lists the bugs). Fixed, 263 questions
rerun on all six routes, everything regraded (run-03).

**What happened** (run-03, 1,450 questions):

| Route | Accuracy | GPU-s per question | Cheapest correct |
|---|---|---|---|
| Fast | [0.903](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [2.6](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [1,310](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) |
| Tools | [0.925](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [4.0](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [75](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) |
| Deep | [0.952](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [7.5](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [42](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) |
| Deep+Tools | [0.943](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [12.1](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [5](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) |
| Vote | [0.967](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [16.4](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [0](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) |
| Vote+Tools | [0.963](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [20.0](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | [1](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) |
| Some route right | [0.988](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/table.csv) | | |

17 questions no route gets right: 10 wrong gold, 6 model errors, 1 grader bug
([always wrong](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/runs/run-03/audit/always_wrong.md)). GPU-seconds include the
rerun of 263 questions, so they are about 18% high for every route.

**Decisions.** All six routes kept (user): the pool is mostly easier math, and Vote and the combos may matter on hard
benchmarks. Router training waits for the Memory routes, so it trains once on all ten.

**Router code** (done, `flotilla/strategy_router.py`): label classifier and success predictor (ModernBERT-base), bge-small
+ logistic regression, and nearest neighbours. Per-question route masks, held-out never read without a flag. Compared
with Vote, with a 0.5-point safety margin in dev tuning (user). A dry run on the real labels showed the code path works;
it is not a result.

**Memory routes on LongMemEval** (in progress). See 3.6 and section 12.

### 3.6 Test 05 (Flotilla): GRAFT base graph for the Memory route

[README](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-05-graft-base-graph/README.md), [table.csv](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-05-graft-base-graph/table.csv).
This is GRAFT tests 03 and 04 seen from Flotilla. Decision: no base graph. Memory routes build each item's graph from its
own history, with the T-REx structure guide (GRAFT test 06), on Qwen.

**LongMemEval.** 500 questions, each with its own chat history of about 50 sessions. Downloaded from the authors'
cleaned release (revision `98d7416`, sha256 checked), leakage-checked against the seven test sets: 0 of 280,124 pieces
flagged, all 500 kept ([report](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/reports/leakage/longmemeval.json)). Split 350 / 76 / 74 by question type. Prompt
length with the whole history: 103,555 to 114,968 Qwen tokens. Nothing cut: served at a 163,840-token window so Deep and
Vote keep their 32,768-token answer budget (run log, 2026-11-21).

---

## 4. Every decision and its reason

Decisions by the user are marked (user). Many were given by voice or in chat; the reason is the one given at the time.

### GRAFT

| Date | Decision | Reason |
|---|---|---|
| 10-29 | Every method answers with Claude Haiku 5.5 | one answering model makes the memory the only difference |
| 10-30 | Baselines run from the benchmark's bundled copies and from upstream (user) | the paper's numbers and today's versions both matter |
| 10-30 | GNN training data: synthetic worlds and SubgraphRAG's WebQSP/CWQ, never MQuAKE or MemoryAgentBench (user) | FactConsolidation contains nearly all MQuAKE-CF facts |
| 10-30 | No API money until the user says so; fake mode first (user) | cost control |
| 10-30 | PPR picks the GNN's 400 nodes | hubs filled the nearest-400 subgraph |
| 11-13 | Mode C default, 256-token answers | A-D tie; 16 tokens cut answers off |
| 11-15 | Rename SGAR to GRAFT (user) | reason not recorded in the repos; old names kept in recorded runs so they stay reproducible |
| 11-20 | Relicense from MIT to Apache-2.0 (user) | reason not recorded; earlier versions stay MIT ([NOTICE](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/NOTICE)) |
| 11-20 | GOAt stays default, EiG optional | rule 4.3 needed 37 and faster, or 40 |
| 11-20 | Hybrids, embedding linking, question graph, bigger subgraphs: not adopted | none beat mode C on paid repeats |
| 11-20 | LLM entity linking not tested | only 1 of 100 questions hit the no-link fallback (user's bar: "more than a few") |
| 11-20 | Haiku entity linking in the writer for base graphs (user) | exact names matched only 13% |
| 11-20 | Full T-REx base (user) | RoG was small and off-domain |
| 11-20 | Never link a single-stopword name (user: "fix it at extraction, not with a stopword list on the graph") | "THE" matched 89 of 100 questions |
| 11-20 | Use the original, uncleaned T-REx graph (user) | the dropped items were mostly real facts |
| 11-20 | Heavy work never on the Mac (user) | the Mac is the user's working machine |
| 11-20 | Embed the 1.58M nodes once and load the saved vectors; run passes as GPU/CPU twins (user) | queues were slow |
| 11-20 | Working-memory design approved (user) | test the agent-memory idea in GRAFT alone first |
| 11-21 | T-REx base not adopted | 17-19 vs 34.7 |
| 11-21 | Rerun the 2026-11-13 commit before trusting the baseline (user) | four modes at 37-38 is not one lucky run |
| 11-21 | Compare only within one day; fixed Haiku check in every paid batch; log request IDs (user) | identical inputs score lower now |
| 11-21 | T-REx as a structure guide is GRAFT's default (user) | 45.7 and 46.0 vs 34.7 and 34.0 |
| 11-21 | Delete charts.py, tables and figures come only from runs (user) | no hand-typed numbers |
| 11-21 | Arm E (guide + working memory) parked, not dropped (user) | a tie with the guide on Haiku; graph-written steps beat prompt-only by about 2.6 twice |
| 11-21 | The guide stays the default on Qwen | 47.0 vs 39.3 for mode C (test 08) |
| 11-21 | A rerun never resumes another job's run folder | the Qwen rerun wrote into the failed job's folders |

### Flotilla

| Date | Decision | Reason |
|---|---|---|
| 11-19 | Protocol frozen before any scored run; every rule written first | nothing tuned on the test set |
| 11-19 | SWE-bench and CanLegal Bench excluded | Docker not allowed; CanLegal not public |
| 11-19 | Small test 5%, at least 20 per benchmark | enough to decide, small enough to keep the test clean |
| 11-19 | Verifier retry tells the model it was wrong and why (user, v2) | a bare retry repeats the mistake |
| 11-19 | Leakage check ignores template wording (v3) | the strict check flagged shared templates |
| 11-19 | Command A+ kept only if it beats Qwen clearly (user, v5); run locally from FP8 (user, v8) | trial key could not cover the screen |
| 11-19 | Phi dropped, gpt-oss-20b medium in (user, v9) | 24/25 vs 21/25 at a tenth of the tokens |
| 11-20 | Native tool calls for every model | text tool lines failed in smoke checks |
| 11-20 | Qwen served as W4A16 | 0.984 = FP8 |
| 11-20 | Command A+ dropped | rule 4.2, −0.104, CI below 0 |
| 11-20 | gpt-oss dropped (user's pre-set rule) | router gain +0.4 < 1 point |
| 11-20 | Strategy router test, ten routes (user) | one model, many strategies |
| 11-20 | "Fix and rerun" the grader and verifier bugs (user) | labels must be right before training |
| 11-20 | Keep all six routes (user) | hard benchmarks may need Vote and combos |
| 11-20 | Router training once, on all ten routes (user) | one training run, all routes |
| 11-20 | Full benchmark runs paused (user) | GPUs to labelling first |
| 11-20 | Every always-wrong question gets a cause label (user) | verifier bug, grader bug, wrong gold, or model wrong |
| 11-21 | Memory routes only on items with their own history | GRAFT has nothing for math or code once T-REx is out |
| 11-21 | Routers compare against Vote, 0.5-point tuning margin (user) | Vote is the best fixed route; margin for dev-to-held-out drop |
| 11-21 | Memory routes use the T-REx guide (user) | GRAFT's new default |
| 11-21 | Live RL also counts questions solved that every fixed route missed, minus wrong gold (user) | above zero beats the oracle |
| 11-21 | LongMemEval served at 163,840 tokens, nothing cut | histories are 103K-115K tokens; Deep needs 32,768 |
| 11-21 | "Cheapest route" judged per question from measured GPU time | Memory routes are cheap on LongMemEval, base routes cheap on the pool |

### Working rules (both repos)

Commits are authored by the user only, with no co-author lines; history is never rewritten; API keys only through a
hidden dialog, never written to a file; ask before API spend over a few dollars; log every decision with a reason and
every dollar; time limits are measured runtime plus 50%; no patient data on clusters; give a time range before each
step; decide routine things and report after.

---

## 5. Tools and libraries

| Tool | What it does | Why we picked it | What we rejected, and why |
|---|---|---|---|
| **vLLM** (0.32) | Serves open models fast, with batching, paged KV cache, tool-call and reasoning parsers | standard, fast, OpenAI-compatible API, native tool parsers (`qwen3_coder`, `openai`, `cohere_command4`) | Hugging Face generate (too slow for 1,450 x 6 runs) |
| **llm-compressor** | Quantizes models (`oneshot` with a recipe) | the vLLM team's tool; outputs load straight into vLLM | building our own GPTQ code |
| **GPTQ, W4A16** | 4-bit weights, 16-bit activations; GPTQ picks the rounding that keeps each layer's output closest | 4 times smaller weights, no accuracy loss on MATH-500 | AWQ was not needed; FP8 kept as the 8-bit reference |
| **Qwen3.8-27B** | 27B dense model, 262K context, thinking on or off, images | best on 10 of 11 small-test benchmarks | Command A+ (4 GPUs, lower), gpt-oss-20b (router gain too small), Phi-4-reasoning-plus (hit its token cap) |
| **Claude Haiku 5.5** | GRAFT's answering and writing model | cheap ($0.10/M input, $0.50/M output), strong enough, one model for every method | Qwen for GRAFT tests at first, to keep GRAFT comparable with the paper; Qwen is now the Memory route's model |
| **Anthropic SDK and our gateway** | The gateway is a local server that speaks Claude Messages and OpenAI chat, adds one embedding endpoint, and logs every call | the baselines are written for OpenAI; one gateway gives everyone the same settings and one cost log | patching each baseline |
| **NetworkX** | Graph library: the graph store, PageRank, subgraphs | simple, fits a 30K-node graph in memory; JSON save | a graph database (not needed at this size); its PageRank needed a fix at 1.58M nodes |
| **Personalized PageRank (PPR)** | A random walk that restarts at the question's entities; nodes the walker visits often are relevant | finds multi-hop neighbours, hubs pass on little | nearest-by-hops (hubs filled the subgraph) |
| **GCN (`GCN_NC` from GOAt)** | A graph neural network: each node's score uses its neighbours' features, 3 layers | GOAt can explain exactly this model | larger or different GNNs (GOAt needs this one) |
| **GOAt** (ICLR 2024) | Explains a GNN's output by splitting it into each edge's contribution | gives which edges matter, training-free; from the supervisor's group | EiG-Search as default (slightly lower, though faster) |
| **EiG-Search** (ICML 2024) | Scores edges in linear time and returns an edge-induced subgraph | faster explanations | kept as an option; rule 4.3 not met |
| **sentence-transformers, bge-small-en-v1.5** | Turns text into vectors | small, fast on CPU, good enough for names and short facts | larger embedders (slow on CPU nodes); NV-Embed-v2 kept as an option |
| **ModernBERT-base** | A modern BERT encoder, long input | router B and the two learned strategy routers | vLLM Semantic Router's model (router A, 0.744) |
| **scikit-learn** | Logistic regression, nearest neighbours | the cheap router baselines | |
| **MemoryAgentBench** | The benchmark: data, prompts, scoring | reuse, not reimplement | |
| **HippoRAG 2, BM25, Mem0, Letta** | Memory baselines from the paper | same conditions as the paper | |
| **T-REx (relbert/t_rex)** | Wikipedia sentences aligned to Wikidata triples | general, Wikidata vocabulary like FactConsolidation | RoG Freebase (off-domain) |
| **LongMemEval** | 500 questions over long chat histories, official LLM judge | long inputs for the Memory routes | `_m` set (over 1M tokens, too long) |
| **Slurm** | The clusters' job scheduler | required on Alliance clusters | |
| **math-verify, sympy** | Math answer checking, symbolic tools | standard for MATH-style answers | string match |
| **lm-eval, lmms-eval, lcb_runner** | Official harnesses for the final benchmarks | match the reference numbers' settings | |
| **MLflow** | Experiment tracking | not used yet; planned for the deployment repo | runs are logged as files and tables instead |
| **matplotlib, Nunito** | Charts and tables in one theme | built from tables only | hand-drawn charts |

---

## 6. Clusters, jobs, scripts and configs (how to rebuild)

### Clusters (Digital Research Alliance of Canada, account def-sylu)

| Cluster | Use | Notes |
|---|---|---|
| **Fir** | Main cluster: GPU (H100, `def-sylu_gpu`) and CPU (`def-sylu_cpu`) | compute nodes reach the internet (needed for Haiku); project filesystem is slow to import from, so jobs copy code and an unpacked venv to node-local disk |
| **Nibi** | GPU twins (full H100 or MIG slices 1g.10gb, 2g.20gb, 3g.40gb) and CPU | low GPU fairshare for full H100s; slices start sooner |
| **Trillium** | Flotilla labelling and quantization (4 x H100 nodes, whole-node jobs), GRAFT free CPU jobs | compute nodes have no internet, so no paid Haiku runs there; GPU jobs only from `trig-login01` |

Access: SSH with ControlMaster sockets; Fir needs a Duo login now and then. API keys go to a job through a hidden macOS
dialog piped into `ssh ... read -r ANTHROPIC_API_KEY`, then `sbatch` passes the environment on. Nothing is written to
disk.

### GRAFT scripts and configs

- `eval/run.py` runs one config (gateway, method, scoring); `eval/queue.py` runs several; `eval/table.py` builds tables.
- `scripts/fir/common.sh`: modules, scratch paths, and the local-disk copy of code and venv (`scripts/fir/pack_venv.sh`
  packs the venv once).
- `scripts/fir/run_real_guarded_cpu.sbatch` and `run_real_guarded.sbatch`: paid runs with a per-job cost cap, the fixed
  Haiku check first.
- `scripts/fir/run_qwen_graft.sbatch`: serves Qwen with vLLM in the job and runs GRAFT against it (`llm.mode: local`).
- `scripts/embed_graph.py`: embeds a graph's nodes once; `scripts/trex_guide.py`: builds the T-REx guide;
  `scripts/guide_check.py`: the free dry check; `scripts/haiku_canary.py`: the check history.
- `scripts/nibi/` and `scripts/trillium/`: the same jobs on those clusters, with `sync_code.sh`.
- `scripts/build_figures.sh`: rebuilds every table, figure and the README chart from the runs.
- Configs: `configs/runs/exp/` (`wm/` test 05, `lh/` test 04, `tg/` test 06, `qwen/` Qwen, `canary/` the fixed check).

### Flotilla scripts and configs

- `flotilla/system.py` (the loop: solver, tools, verifier, one retry), `serve.py` (starts vLLM servers and runs a batch),
  `smalltest.py`, `label_loop.py`, `strategy_items.py`, `strategy_labels.py`, `leakage.py`, `quantize.py`,
  `eval_math500.py`, `oracle.py`, `strategy_router.py`, `rl_router.py`, `memory_route.py`, `graft_bridge.py`,
  `longmemeval.py`.
- `configs/servers.json` (vLLM settings, 131,072 tokens), `configs/servers_longmemeval*.json` (163,840),
  `configs/systems/qwen_strategy_*.json` (one per route), `configs/splits/` (small-test splits).
- `scripts/trillium/job.sbatch`, `scripts/nibi/submit_*.sh`, `scripts/fir/submit_*.sh`, `scripts/fir/lme_job.sbatch`.

### Rebuild order

1. Set up the venvs on a login node (internet), cache models and datasets under scratch.
2. Quantize Qwen with `flotilla.quantize` (W4A16 GPTQ), check MATH-500.
3. Build and leakage-check the router pool; draw the strategy items; run every route; grade; split.
4. GRAFT: build the document graph with Haiku (or Qwen), embed nodes once, build the T-REx guide, run configs.
5. Rebuild tables and figures with `make_table.py` per test and `scripts/build_figures.sh`.

---

## 7. Every bug, and its fix

| Bug | Symptom | Cause | Fix |
|---|---|---|---|
| Nearest-400 subgraph (GRAFT, 10-30) | answer inside the subgraph for 42 of 100 | hubs filled the nearest nodes | choose the 400 by PPR |
| 16-token answers (GRAFT test 01) | scores 13-22 | answers cut off before the answer | 256-token cap |
| Same-second run folders (GRAFT 11-20, again 11-21) | 3 of 6 jobs died; two Haiku checks collided | folder name was the config name plus the second | folder carries the job id and an owner file; an unfinished folder is resumed only when its owner is gone |
| Question graph crash (GRAFT 11-20) | crash after 100 parse calls | texts not embedded before workers forked | embed in the parent; test fails on the old code |
| T-REx column order (GRAFT 11-20) | wrong triples | (relation, head, tail) read as (head, relation, tail) | rebuilt with labels |
| **PageRank stop rule** (GRAFT 11-20) | every T-REx answer pass 0.0, 95 of 100 empty | NetworkX stops when total change < N x 1e-6; at N = 1.58M the bound is 1.58, met after one step | bound min(N x 1e-6, 0.1); a run stops if most questions get no facts |
| **"THE" link** (GRAFT 11-20) | 89 of 100 questions linked "e:the" | the exact-name linker matches every entity name in the question; T-REx has an entity "The" | never link a single stopword, article or question word; multi-word names stay |
| Cleaning rule too wide (GRAFT 11-20) | would drop 130,033 real facts | "generic word" test hit real concepts | narrowed, then not used |
| **Fir filesystem slowdown** (GRAFT 11-20) | gateway did not start in 30 min | importing sentence-transformers from the project filesystem took 7-30+ min | copy code and an unpacked venv to node-local disk |
| Twin watcher (11-20) | cancelled the wrong twin | zsh does not split unquoted variables | bash script per pair |
| **Cost guard, first** (GRAFT 11-21) | test 05 runs never counted | it only matched folders named `*real*` | count every run of the job |
| **Cost guard, second** (GRAFT 11-21) | read $0.46 for a job that spent $0 | it counted other jobs' runs written in the same folder | count only the run names in the job's own configs |
| **git archive submodule miss** (GRAFT 11-21) | old-commit rerun failed at import | `git archive` leaves out submodules | link the unchanged submodules in |
| **OOM** (GRAFT 11-21) | bridge job killed at 64 GB | the 1.58M-node graph plus weighted edges | 200 GB |
| **tar "file changed"** (GRAFT 11-21) | guide job died before starting | other jobs' `.out` logs changed while the code was copied | skip `*.out`, accept tar's exit 1 |
| Missing `openai` in GRAFT's venv (GRAFT 11-21) | Qwen GRAFT job on Nibi ended in 10 minutes, all four configs | the gateway's local vLLM backend imports `openai`, not in GRAFT's venv | jobs install it from the Alliance wheelhouse when missing; worked on a compute node (Nibi 28263641). Repacking the venv with it is still open |
| **Run folder reuse** (GRAFT 11-21) | the Qwen rerun's results sit in folders named after the failed job | an unfinished folder was resumed whenever its owner job was gone | resume only the same Slurm job's folder; tests |
| Label prompt without a tool loop (Flotilla test 03 run-01) | 22 of 34 labels ended at a tool line | one call, no loop | label through the real loop |
| Code fences (Flotilla labels) | gpt-oss code answers all failed | fenced code run as-is | strip fences before tests |
| **A-D option bug** (Flotilla 11-20) | MMLU-Pro answers E-J rejected, retry forced to A-D (21 always-wrong) | verifier counted only A-D when no options list | count lettered options in the question; unit test |
| **Instruction checker** (Flotilla 11-20) | 19 always-wrong questions | read "Do not include keywords" as include; P.S. only; missed "* * *"; capital-word counts | fixed, 19 unit tests |
| **Float tolerance** (Flotilla 11-20) | right code answers failed on float output | exact string compare | tolerance in label grader and scorer |
| **Math formats** (Flotilla 11-20) | right answers missed | $, \text{}, unicode, thousands braces, option letter vs value, number with unit | format matches |
| Login-node Python (Flotilla 11-20) | 12 false negatives per route | system Python lacked sympy and math-verify | grade in the Flotilla env |
| Memory-route server swap (Flotilla 11-21) | routes lost thinking-off settings | replacing servers dropped the request block | merge url and model only |
| Router pickle (Flotilla 11-21) | saved router would not load | pickled as `__main__.LRRouter` under `-m` | set the class's module |
| Haiku drift (GRAFT 11-21) | 38 then about 34 on identical prompts | outside our code | same-day comparisons, fixed check, request IDs |

---

## 8. Spend by date

All API spend is Anthropic (Haiku 5.5). Qwen runs are local and free. Cohere calls used a free trial key.

| Date | What | Cost | Source |
|---|---|---|---|
| 2026-10-29/30 | Fake mode only | $0 | memory notes |
| 2026-11-13 | GRAFT real runs: read orders A-D, BM25, HippoRAG 2 (16, 256, 2,048 tokens) | $3.84 | [experiments.md](https://github.com/MohamedKhalidmk/GRAFT/blob/graft-linking-hybrid/docs/reference/experiments.md) |
| 2026-11-19/20 | EiG variant, hybrids, top-10, question graph | $0.391 | [run log spend table](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/run_log.md) |
| 2026-11-20 | RoG builds (exact-name cancelled, Haiku linking) | $1.815 | run log |
| 2026-11-20 | Full T-REx builds and first answer passes (0.0, bug) | $2.370 | run log |
| 2026-11-20 | Working memory run-01 | $0.657 | run log |
| 2026-11-21 | Full T-REx fixed answer passes | $0.574 | run log |
| 2026-11-21 | Haiku baseline check | $0.244 | run log |
| 2026-11-21 | Working memory round 2 | $0.483 | run log |
| 2026-11-21 | Test 06 B, C, D | $0.273 | run log |
| 2026-11-21 | Same-day confirmation | $0.217 | run log |
| 2026-11-21 | Test 06 arm E and guide rerun, Haiku check | $0.373 | run log |
| | **Total recorded** | **$11.23** ($3.84 + $7.39) | |

GPU time: the strategy labels used about 25.2 GPU-hours for 1,450 questions on all six routes (90,804 GPU-seconds, the
sum of the `gpu_seconds_job` figures in [summary.json](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/experiments/test-04-strategy-router/runs/run-03/graded/summary.json)),
about 18% high because of the rerun. Allocations are free to the group.

---

## 9. Methods in plain words

**A graph memory with versions.** GRAFT reads documents chunk by chunk. An LLM pulls out facts as (subject, relation,
object) with the sentence they came from. Each new fact is added, merged with an equal one, marked as replacing an older
version (a SUPERSEDES link), or ignored. Old versions stay, so the memory can show its history.

**Finding facts for a question.** Find the question's entities in the graph. Take a random walk that keeps jumping back
to them (Personalized PageRank); keep the 400 nodes the walker visits most. A small graph neural network scores those
nodes; GOAt says which edges made the score. Walk a second, short time from GOAt's picks. Follow SUPERSEDES links to the
newest version. Give the best 50 facts to the LLM.

**The T-REx guide.** A big knowledge graph is useful for its shape, not its facts. From T-REx we learn which relations
usually follow which ("plays position" then "sport" then "country of origin"), and what type each name is. We use that
to tidy the document graph (same relation written two ways becomes one) and to follow the question's chain hop by hop,
taking the newest fact each time. No T-REx fact is ever shown to the model.

**Working memory in the graph.** Answer in steps. Write the question, each step, its result and a note into the graph as
temporary nodes, and let the next step's walk start from them. Remove them after.

**Quantization.** Store each weight in 4 bits instead of 16. GPTQ picks the rounding layer by layer so each layer's
output changes as little as possible, using a small calibration set.

**Routing.** Every route tried on every training question gives labels: which routes were right, and at what cost. A
router learns from the question text which route is likely right, and picks the cheapest one it trusts.

**Live RL.** Instead of one pick, the router can take a step, see the verifier's verdict, and decide to stop or try
another route. Reward: +1 if right, minus a small cost per GPU-second.

**Leakage checks.** A training item is dropped if it shares a 13-word run with a test item, or its embedding is almost
the same (cosine 0.95), ignoring shared template wording.

---

## 10. Mistakes and lessons

1. **Single runs mislead.** The 38 baseline was one run. With repeats and a same-day rerun it is about 34-35. Every
   comparison now runs 3 repeats on the same day, with a fixed check.
2. **Free checks before paid runs.** Gold-in-facts checks with a fake model killed most variants for free. But a better
   free number did not always mean better answers (the hybrids).
3. **Check the denominator of a library's defaults.** NetworkX's stop rule scales with graph size. A speed check passed
   because it only timed PageRank and never counted facts.
4. **Look at the failures by hand.** 69 always-wrong questions were mostly our bugs, not the model's. After the fixes, 17.
5. **Test small before big.** 16-question label tests, 5-question pilots, toy graphs. Each caught something.
6. **The environment is part of the experiment.** Slow filesystems, missing submodules, packages missing from a venv,
   tar on changing folders, memory limits. Each cost time, never money, because jobs check before spending.
7. **Shell quirks matter.** zsh does not split words; a watcher cancelled the wrong job.
8. **More knowledge can hurt.** A million true facts drowned the documents' edited facts. The same source helped once it
   only shaped how facts connect.
9. **Write rules before results.** It made dropping Command A+, gpt-oss and the T-REx base easy and honest.
10. **Overshooting a fix.** The first cost-guard fix counted other jobs' runs. Test a fix against the case that broke it
    and its neighbours.

---

## 11. Interview questions, with answers

**Why a graph memory instead of a vector store?**
Facts change. A vector store returns similar text, old and new together. A graph with SUPERSEDES links knows which
version is current and where each came from, and multi-hop questions need chains, which a graph walk follows.

**Why Personalized PageRank to pick the subgraph?**
It ranks nodes by how often a walker that restarts at the question's entities visits them. Hubs spread their weight over
many links, so they pass little to any one neighbour. Nearest-by-hops let hubs fill the budget.

**What is GOAt and why use it?**
It decomposes a GCN's output into contributions from each edge, so we know which edges, and so which facts, drove a
node's score. It needs a specific GCN shape, which is why GRAFT's GNN uses GOAt's own model.

**Your T-REx base halved accuracy. Why, and what did you do?**
Its facts filled two thirds of the slots and pushed out the edited document facts, and some contradicted the gold. I
kept only T-REx's structure (relation chains, types) for linking and planning, and accuracy went from 34.7 to 45.7.

**How do you know the 45.7 is real?**
Three repeats with a spread of about 1.5, then a same-day rerun of both arms: 46.0 vs 34.0. A fixed check confirmed
Haiku was in its usual range that day.

**What was the PageRank bug?**
NetworkX stops when the total change between steps is under N times the tolerance. On 1.58 million nodes that bound was
met after one step, so scores were just the start spread one hop: hubs on top, no facts in the subgraph. I fixed the
bound and added a check that stops a run when most questions get no facts.

**How do you prevent test leakage?**
13-gram overlap and embedding similarity against every test item, ignoring template wording; GNN trained only on
synthetic or other datasets; decision rules written before results; held-out read once, behind a flag.

**Why 4-bit, and how did you decide?**
The rule was set first: 4-bit if within 1 point of 8-bit on MATH-500. Our W4A16 build scored 0.984, the same as FP8.

**Why did you drop the multi-model setup?**
Command A+ was 10 points below Qwen on the small test at four times the GPUs. A trained router between Qwen and gpt-oss
gained only 0.4 points, under the 1-point bar set beforehand.

**What does the strategy router optimise?**
Accuracy against compute. Fast is right 90% of the time at about a sixth of Vote's GPU time (2.6 vs 16.4 GPU-seconds); Vote is best at 0.967. The
keep rule: within 1 point of Vote at lower compute, or more than 1 point better.

**How would you handle a model whose behaviour drifts behind a fixed API name?**
Compare within one run window, keep a fixed replay set as a canary, log request IDs and hashes, and prefer local models
for final numbers.

**What would you do differently?**
Repeats from day one, a same-day baseline in every comparison, and a request log from the first paid call.

**How does live RL here differ from supervised routing?**
Supervised routers pick once. The RL router takes a step, sees the verifier's verdict, and decides to stop or escalate,
learning from the outcome with a cost penalty. It starts from the supervised router's estimates.

**How do you grade free-text answers on LongMemEval?**
With the benchmark's official judge prompts, using Claude Haiku 5.5 as the judge, not Qwen: Qwen makes the answers that
become the labels, so it must not grade its own work (protocol-v10 addendum). Every judge batch starts with the fixed
Haiku check and logs request IDs, and 50 verdicts are checked by hand before the labels are trusted.

---

## 12. What is open, and the exact next steps

**Running now** (see HANDOFF.md for job ids).

- GRAFT test 08 run-02: arm E (guide plus working memory) on Qwen with a guide rerun in the same job.
- LongMemEval labelling (Flotilla test 04): the six base routes and the GRAFT graph builds have run on all 20 shards;
  next the four Memory routes, the Haiku judge, and the merged labels (`run-04-lme`).

**Next steps, in order.**

1. Done: the venv fix worked and GRAFT on Qwen is test 08 (the guide 47.0 vs mode C 39.3).
2. Finish LongMemEval labels on all ten routes; hand-check 50 judge verdicts (stop if under 90% agreement).
3. Train the four supervised routers once on all ten routes (`scripts/fir/submit_strategy_router.sh train`); pick the
   best on dev under the keep rule (vs Vote, 0.5-point margin).
4. Live RL from the best router (`scripts/fir/submit_rl_router.sh`); tune the time penalty on dev; report questions
   solved that every fixed route missed, minus wrong gold, with their chains.
5. Held-out once, then the 5% small test once.
6. Final full benchmarks: the full system vs plain Qwen and the best single route, on the same questions; accuracy,
   tokens and time, against the published reference numbers.
7. GRAFT: which part of the guide carries the gain (linking only vs planning only, about $0.10 each); arm E on Qwen;
   a new benchmark beyond FactConsolidation.
8. Merge Flotilla's `restructure` branch into its `main` after review; merge GRAFT's research branch again when the next
   results are in.
9. Deployment repo (planned): API service, containers, CI, experiment tracking, monitoring, cluster and cloud jobs.
