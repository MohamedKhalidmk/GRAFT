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

## Arms (built on G52, against G52 and G35)

Changed 2026-11-26 (user): the arms build on G52 (G35's guided facts up to 4,096 tokens), since G52 leads test 10.
G35 and G52 on patient facts only are the two baselines, run on the same MedMemoryBench questions, the same day, the same
seeds, mean of 3, 4,096-token answer cap. If the same-day G35 against G52 rerun (Flotilla STATUS row 47) shows G35 ahead
of G52, the user is told before any arm runs.

| Arm | Graph | Base facts | Conflict rule | What it tests |
|---|---|---|---|---|
| G35 | user facts, general guide, 50 fact lines | none | newest user fact wins (as today) | baseline |
| G52 | user facts, general guide, facts up to 4,096 tokens | none | as G35 | baseline the arms build on |
| a. Guided | user facts, written with a domain guide (e.g. a medical relation schema in place of the general T-REx guide) | none | as G35 | does a domain guide alone help |
| b. Mixed | domain base + user facts in one graph | yes, ranked like user facts | none, all facts equal | does background knowledge help when nothing marks it |
| c. Layered | same base + user facts | yes, a separate layer | user facts always win; base facts are read only for entities or relations no user fact covers, and are labelled "background" in the prompt | does the layer rule keep the gain and remove the harm |
| d. Wrong base | layered, with an off-topic base of the same size | yes, off-topic | as c | how much the base costs as clutter |

Fixed across arms: same writer (G41's fixed writer), G52's 4,096-token fact budget for arms a to d, Qwen W4A16,
thinking off, answer cap 4,096 (the standard Qwen cap from 2026-11-26), 3 repeats with vLLM seeds 20261119+k set per
job (VLLM_SEED), all arms submitted together the same day.

## Test sets

1. **Domain set, where background should help.** Options, best first:
   - **MedMemoryBench (2026; arXiv 2605.11814; data on Hugging Face, Cyan27/MedMemoryBench, commit 8fff0b9).** Licence
     checked 2026-11-26: the data is **CC BY-NC-SA 4.0** (research only, no commercial use, derived data shared under the
     same licence), not CC BY 4.0 as first reported; the code is Apache 2.0. Download held for the user's call. Size 1.30 GB
     in all, about 748 MB for English (dialogues 386 MB, dialogues with noise 359 MB, queries 2.2 MB); fits in Fir scratch
     (19 TiB, 353 GB used). 20 chronic-disease
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

An arm is kept only if it beats G52 on the domain set by more than the larger repeat spread of the two, and its
FactConsolidation mean is not below G52's by more than G52's repeat spread. G35 is reported beside them.

## MedMemoryBench as downloaded (2026-11-26)

- Approved by the user 2026-11-26: CC BY-NC-SA 4.0 is fine for GRAFT thesis research (non-commercial). Results on it are
  tagged NC-SA and kept out of the Flotilla model card. The data stays on Fir scratch and is never committed.
- Downloaded on Fir: English only, pinned to commit 8fff0b9, 714 MB, sizes match the Hugging Face listing
  (/scratch/khaledmk/sgar/data/medmemorybench/8fff0b9).
- Shape: 20 patients (all "chronic"), 101 sessions each, about 800k tokens of dialogue per patient (about 7 times a
  LongMemEval-S history); 1,939 questions asked at checkpoints after sessions 10, 20, ..., 100, each seeing only the
  sessions before it. Types: multiple choice 398 (traps: temporal state 138, allergy cross-reaction 72,
  contraindication 67, preference 61, drug interaction 56; most have 2 correct options), entity 400, date 374,
  inference 381, state update 195, multi-hop 191.
- Selection (seed 20261126; test11_questions.jsonl and test11_selection.json next to the data): 10 patients
  (2, 3, 4, 5, 10, 11, 12, 14, 18, 19), checkpoints 10 and 20, gradable types only: all 40 multiple-choice questions,
  plus 20 state-update, 20 entity and 20 date questions drawn from the 136 available; 49 at checkpoint 10, 51 at 20.
  Inference and multi-hop answers are free text and would need a judge, so they are left out of the Qwen step.
- Grading (free, MedMemoryBench's own rules): multiple choice right only if the chosen option set equals the correct
  set; state update and entity by match to the short gold; date by the target date.
- Graphs: each patient's first 20 sessions (median about 150k tokens), with a snapshot after session 10 so checkpoint-10
  questions never see sessions 11 to 20.

## Jobs and GPU-hours (estimate, 3g.40gb slices; nothing submitted)

| Step | Jobs | Slice GPU-hours |
|---|---|---|
| Patient graphs: 10 patients x 2 guides (general guide for G35, G52, b to d; domain guide for a), 20 sessions each, snapshot at 10 (G41 took about 1 h per 115k-token history) | 20 (40 if the writer cannot snapshot and the first 10 sessions are built separately) | 26 to 40 |
| Domain base and domain guide from Hetionet (CC0, 16.1 MB, github.com/hetio/hetionet; download needs your yes): structured triples, no LLM | 1 CPU | 0 |
| Off-topic base for arm d: the T-REx slice from tests 04 and 06 (exists) | 0 | 0 |
| Fake-answer smoke on both sets, all arms | 2 CPU | 0 |
| Qwen answer runs, MedMemoryBench: 6 arms (G35, G52, a, b, c, d) x 3 repeats | 18 | about 14 |
| Qwen answer runs, FactConsolidation: 6 arms x 3 repeats, the same day | 18 | about 18 |
| Total | 59 (79) | about 58 to 72 |

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
