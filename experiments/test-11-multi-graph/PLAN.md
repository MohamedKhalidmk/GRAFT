# Test 11 · Multi-graph (plan only, not started)

Status: plan for the user's review (asked 2026-11-26). Nothing is built or submitted. Candidate IDs are given when the
user approves the plan.

## Question

Does a domain knowledge graph under the user's facts help GRAFT answer questions that need background knowledge, without
hurting questions the chat history alone answers? And does it matter how the base and the user facts are combined?

## What we already know (tests 03, 04, 06)

- Test 03 (RoG Freebase base, 20,000 facts, Haiku): not adopted. A small off-domain base mostly added hub noise to PageRank.
- Test 04 (full T-REx base, 1.23M facts, Haiku): not adopted. Accuracy halved on FactConsolidation (17-19% against 34.7%).
- Test 06: T-REx as background facts the model reads (G37) scored 17.7 against G35's 45.7; T-REx as a guide to how facts
  connect (G35) is what we kept.

So arm (b) "mixed" and arm (d) "wrong base" have both been measured on FactConsolidation already, with general bases, and
both hurt. What is new here is (1) a domain base that matches the questions, (2) the layered rule where user facts win and
the base is read only when the user facts do not cover the question, and (3) a domain-specific writing guide.

## Arms (all against G35, the guided graph with 50 fact lines)

| Arm | Graph | Base facts | Conflict rule | What it tests |
|---|---|---|---|---|
| G35 | user facts, general guide | none | newest user fact wins (as today) | baseline |
| a. Guided | user facts, written with a domain guide (e.g. a medical relation schema in place of the general T-REx guide) | none | as G35 | does a domain guide alone help |
| b. Mixed | domain base + user facts in one graph | yes, ranked like user facts | none, all facts equal | does background knowledge help when nothing marks it |
| c. Layered | same base + user facts | yes, a separate layer | user facts always win; base facts are read only for entities or relations no user fact covers, and are labelled "background" in the prompt | does the layer rule keep the gain and remove the harm |
| d. Wrong base | layered, with an off-topic base of the same size | yes, off-topic | as c | how much the base costs as clutter |

Fixed across arms: same writer (G41's fixed writer), same 50-line budget for the facts read (plus a check at G52's
4,096 tokens if G52 is kept after its same-day rerun), Qwen W4A16, thinking off, answer cap 4,096, 3 repeats with vLLM
seeds 20261119+k, all arms submitted together the same day.

## Test sets

1. **Domain set, where background should help.** Options, best first:
   - **MedMemoryBench (2026; arXiv 2605.11814; data on Hugging Face, CC BY 4.0, code Apache 2.0).** 20 chronic-disease
     patients, about 100 doctor and patient sessions each, about 1,986 questions. Its multiple-choice (398),
     inference-generation (397) and multi-hop clinical (191) questions need medical knowledge plus the patient's own facts
     (allergies, contraindications); state-update (200) tests changed facts, which matches "user facts win". Short types
     grade by option or string match. Published scores: about 52% best (long context), about 34% for graph systems
     (GraphRAG, HippoRAG 2), so there is room. Proposal: about 100 questions from the multiple-choice, multi-hop and
     state-update types (option-graded, so no judge cost), English, 3 to 5 patients.
   - ColaBench (2026; arXiv 2610.30989): built for exactly this (user conditions plus a health knowledge base of 13,033
     MedlinePlus, openFDA, NCI and CDC documents), but small (10 users, 349 tasks), LLM-judge graded, and the data
     release and licence are not confirmed.
   - MedLoCoMo and ClinTraceBench need PhysioNet credentialed access (MIMIC-IV) and mostly need no outside knowledge, so a
     base would not help. LoCoMo, LongMemEval, PersonaMem and MemoryAgentBench have almost no domain questions.
   - Fallback if MedMemoryBench does not fit: inject 3 to 6 health "needle" sessions into LongMemEval-S histories (MIT),
     with later updates; about 100 questions that need a user fact and a domain fact together (e.g. a drug the user takes
     plus an interaction from openFDA), plus about 20 history-only and 20 base-only controls; short gold answers; a
     no-history and a base-only baseline to show both are needed.
   - **Base for arms b, c:** openFDA drug labels and MedlinePlus (public domain) or Hetionet (CC0), turned into triples by
     the same writer; never built from the test questions, with test 03's leakage checks (13-gram, embedding, topic
     entities). Not UMLS or SNOMED (licence), not PrimeKG's DrugBank edges (non-commercial).
   - **Base for arm d:** a T-REx slice of the same size (the general base from tests 04 and 06).
2. **FactConsolidation (MemoryAgentBench mh 262k, 100 questions), where the base must do no harm.** Same bases as above
   (a medical base is off-topic here, so arms b and c measure clutter too).

## Keep rule (set before results)

An arm is kept only if it beats G35 on the domain set by more than the larger repeat spread of the two, and its
FactConsolidation mean is not below G35's by more than G35's repeat spread.

## Order and cost

1. Benchmark check (free): download MedMemoryBench (needs your yes to download), check the English split, question
   types and grading, pick the 100 questions; build the domain guide and the base (Qwen writer, free on Fir).
2. Fake-answer smoke on both sets (free): gold in the facts shown for every arm.
3. Qwen runs: 5 arms x 2 sets x 3 repeats = 30 jobs on 3g.40gb slices, about 0.5 to 1.5 h each, free.
4. Later, Haiku on FactConsolidation only, for G35 and the arms that survive, to compare with HippoRAG 2 (15%) and BM25
   (4%). Estimate: answering only, with the 2026-11-13 Haiku graph reused, about 100 questions x 2 calls x about 2,000
   input tokens per repeat at $0.10 per million input tokens is about $0.04 to $0.06 per repeat, so about $0.15 per arm
   for 3 repeats and about $0.30 to $0.60 for G35 plus up to three arms. If arms b to d need Haiku to link the base into
   the Haiku graph (as in test 04, $1.75 for one build), add about $1.5 to $2 per base. Both are near or above the
   current credit of about $0.48, so the Haiku step waits for your yes and a top-up.
