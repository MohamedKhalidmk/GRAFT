# GRAFT registry: candidates, setups, runs

Approved by the user 2026-11-21. **IDs are frozen** (user, 2026-11-21): once applied, an ID is never renumbered or reused. New candidates and setups get the next free number; a dropped item keeps its ID with a status. Next free IDs: see the last row of each table.

Three layers (user, 2026-11-21):

- **Candidate** (G01, G02...): the method, defined by its parts (section 2). Two runs with identical parts share one ID.
- **Setup** (S01, S02...): a candidate plus the answering model, answer cap, benchmark, scoring and benchmark settings.
  Every result points to a setup. Setup IDs are one sequence across both repos (GRAFT S01-S101, Flotilla from S102).
- **Run**: one execution of a setup (a run folder such as `exp_c_real_mh_262k_ans256_20261113-115012`). Raw run folders
  and recorded configs keep their old names; this registry maps them.

Built from every config in `configs/runs/`, every recorded run in `experiments/`, and every run folder on Fir and Nibi
(304 configs). IDs are fixed and never reused. Outside systems keep their own names: BM25, Embedding RAG (bge-small),
HippoRAG 2 (bundled, upstream), Mem0 (bundled, upstream), Letta (bundled, upstream), Knowl, Total Agent Memory, Long
context (full, 128K). Flotilla's candidates are F01, F02... ([Flotilla registry](https://github.com/MohamedKhalidmk/Flotilla/blob/restructure/docs/reference/REGISTRY.md)).

Status: **scored** (a real or local run with accuracy), **free check only** (run only in fake mode: scripted replies,
code path checked, no accuracy), **cancelled** (started, stopped before an answer), **never run**.

History: draft 1 numbered Embedding RAG (bge-small) as a candidate; it is a baseline, so draft-1 G25-G39 became G24-G38 before approval.

## 1. Candidates

| ID | What it is | Old names | Tests | Status | Why |
|---|---|---|---|---|---|
| G01 | read order A (GNN + GOAt), 300 facts | "goat", `graft_goat_bge_262k`, `sgar_goat_bge_262k`, `graft_goat_fake_6k`, `dryrun_graft_gnn_goat_262k`, `ui_sgar_6k_fake` | before test 01 | free check only | replaced by the 50-fact budget (G04) before any paid run |
| G02 | GNN top-k, 300 facts | "topk", `graft_topk_bge_262k`, `sgar_topk_bge_262k`, `graft_topk_fake_6k`, `dryrun_graft_gnn_topk_262k` | before test 01 | free check only | the GNN's top nodes alone, superseded by GOAt explanations before any paid run |
| G03 | PageRank only, 300 facts | "ppr", `graft_ppr_fake_6k`, `dryrun_graft_ppr_262k` | before test 01 | free check only | a code-path check; PageRank went into read orders B and C instead |
| G04 | read order A (GNN + GOAt), 50 facts | **mode A**, `exp_a_real_mh_262k`, `exp_a_real_mh_262k_ans256`, `exp_a_fake_262k`, `graft_goat_budget50_262k`, `sgar_goat_budget50_262k` | 01 | scored | 37 at 256 tokens; level with C, C chosen as default (38) |
| G05 | GNN top-k, 50 facts | `graft_topk_budget50_262k`, `sgar_topk_budget50_262k` | before test 01 | free check only | as G02 |
| G06 | PageRank only, 50 facts | `graft_ppr_budget50_262k`, `sgar_ppr_budget50_262k` | before test 01 | free check only | as G03 |
| G07 | read order B (GOAt, then PageRank) | **mode B**, `exp_b_real_mh_262k`, `exp_b_real_mh_262k_ans256`, `exp_b_fake_262k` | 01 | scored | 37; not the default |
| G08 | read order C (PageRank, GNN + GOAt, short PageRank) | **mode C**, `ppr_goat_ppr`, "plain C", "arm A" in tests 05, 06 and 08, preset `plain_c`; `exp_c_real_mh_262k`, `exp_c_real_mh_262k_ans256`, `..._rerun28d4fd5`, `exp_wm_empty_a_modec`, `exp_real_wm_empty_a_modec_rerun1121`, `exp_real_tg_a_sameday`, `exp_qwen_empty_a_modec`, `exp_qwen1024_a_modec_r0..2`, `exp_c_fake_262k` | 01, 05, 06, 07, 08 | scored | default read order since test 01 (38); every later candidate builds on it |
| G09 | G04 on a synthetic start graph | **experiment D**, "mode D", "extend", `exp_d_extend_real_mh_262k`, `..._ans256`, `exp_d_extend_fake_mh_262k` | 01 | scored | 37; extending a ready-made graph not adopted |
| G10 | G04 with EiG instead of GOAt | "EiG variant A", `exp_a_real_mh_262k_ans256_eig`, `exp_a_fake_mh_262k_eig_check` | 02 | scored | 36 vs GOAt's 37, 3x faster; rule 4.3 needed 37 and faster, or 40, so GOAt stays |
| G11 | G08 with EiG | "C + EiG", `exp_c_fake_mh_262k_base_eig` | 02 | free check only | the base for the EiG variants; its paid EiG check ran on read order A (G10) |
| G12 | G11 + interleaved embedding search | "50/50 hybrid, EiG", `exp_c_real_mh_262k_ans256_hybrid_eig`, `exp_c_fake_mh_262k_hybrid_eig`, `..._n400`, `..._src` | 02 | scored | no gain over mode C on 3 repeats; not adopted |
| G13 | G08 + interleaved embedding search | "50/50 hybrid, GOAt", `exp_c_real_mh_262k_ans256_hybrid_goat`, `exp_c_fake_mh_262k_hybrid_goat`, `..._src` | 02 | scored | as G12 |
| G14 | G12 with an 800-node subgraph | `exp_c_fake_mh_262k_hybrid_eig_n800` | 02 | free check only | not paid for once the hybrid itself brought no gain |
| G15 | G12 with a 1,600-node subgraph | `exp_c_fake_mh_262k_hybrid_eig_n1600` | 02 | free check only | as G14 |
| G16 | G11 + top-10 embedding facts | "top-10 hybrid", `exp_c_real_mh_262k_ans256_topk10_eig`, `exp_c_fake_mh_262k_topk10_eig` | 02 | scored | 33 / 31 / 29; below mode C, not adopted |
| G17 | G11 + top-5 embedding facts | `exp_c_fake_mh_262k_topk5_eig` | 02 | free check only | top-10 was the one paid for |
| G18 | G11 + embedding entity linking (k=5) | "embedding linking", `exp_c_fake_mh_262k_link_eig` | 02 | free check only | only 1 of 100 questions hit the no-link fallback, under the user's bar ("more than a few") |
| G19 | G08 + embedding entity linking (k=5) | `exp_c_fake_mh_262k_link_goat` | 02 | free check only | as G18 |
| G20 | G11 + embedding linking + interleaved search | "both", `exp_c_fake_mh_262k_both_eig` | 02 | free check only | as G18 |
| G21 | G08 + embedding linking + interleaved search | `exp_c_fake_mh_262k_both_goat` | 02 | free check only | as G18 |
| G22 | G11 with the 1,600-node GNN checkpoint | "gnn1600", "retrained GNN", `exp_c_fake_mh_262k_gnn1600_eig` | 02 | free check only | the retrained GNN was rejected in the free check |
| G23 | G11 + question layer (embedding matching) | "question graph", "qgraph", `exp_c_real_mh_262k_ans256_qgraph_eig`, `exp_c_fake_mh_262k_qgraph_eig` | 02 | scored | 39 / 37 / 35, mean 37; no gain, not adopted |
| G24 | G11 on a RoG (Freebase) base, exact-name linking | "RoG exact-name build", `exp_c_real_mh_262k_ans256_rog_build_eig` | 03 | cancelled | exact names matched 13% of entities; build stopped at chunk 51 ($0.168) for Haiku linking (G25) |
| G25 | G11 on a RoG base, Haiku linking | "RoG base", "RoG Haiku-linking", `exp_c_real_mh_262k_ans256_rog_link_build_eig`, `exp_c_fake_mh_262k_rog_link_eig` | 03 (Flotilla 05) | scored | 21 vs 38; hub entities pulled in noise; not adopted |
| G26 | G11 on the T-REx dense core, Haiku linking | "T-REx core", "dense core", `exp_c_real_mh_262k_ans256_trex_link_build_eig`, `exp_c_fake_mh_262k_trex_link_eig` | 04 | cancelled | the core matched 11.6% of document entities; replaced by full T-REx (G27) before any answer |
| G27 | G11 on full T-REx (45 properties), Haiku linking | "full T-REx", "trexfull eig (pprfix)", `exp_c_real_mh_262k_ans256_trexfull_link_build_eig`, `..._trexfull_eig_pprfix`, `..._pprfix_check5`, `exp_c_qwen_mh_262k_ans256_trexfull_eig` | 04 (Flotilla 05) | scored | 17-19 vs 34.7; the base crowds out the documents' edited facts; not adopted |
| G28 | G08 on full T-REx, Haiku linking | "full T-REx, GOAt", `..._trexfull_goat`, `..._trexfull_goat_pprfix`, `exp_c_qwen_mh_262k_ans256_trexfull_goat` | 04 | scored | as G27 |
| G29 | G27 + question layer, Haiku question linking | "full T-REx question layer", `..._trexfull_qgraph_eig`, `..._pprfix`, `exp_c_qwen_mh_262k_ans256_trexfull_qgraph_eig` | 04 | scored | as G27 |
| G30 | G08 + question layer | test 05 **arm B**, "question layer", `exp_wm_empty_b_qlayer` | 05 | scored | 33.7 vs 34.7; not adopted |
| G31 | G08 + working memory written into the graph, step prompt v1 | test 05 **arm C**, `exp_wm_empty_c_wm_graph`, `exp_wm_fake_check_c_wm_graph` | 05 | scored | 35.3, inside the spread at 3x the cost; replaced by v2 (G33) |
| G32 | G08 + the same steps in the prompt only, v1 | test 05 **arm C-**, `exp_wm_empty_cm_wm_prompt` | 05 | scored | 32.7; the control for G31 |
| G33 | G08 + working memory in the graph, step prompt v2 (newer-fact rule) | **C v2**, `exp_wm_empty_c_wm_graph_v2`, `exp_qwen_empty_c_wm_graph_v2`, `exp_qwen1024_c_wm_graph_v2_r0..2` | 05, 08 | scored | Haiku 35.7, not kept (inside the spread, 3x cost); Qwen at 1,024 tokens running |
| G34 | G08 + the same steps in the prompt only, v2 | **C- v2**, `exp_wm_empty_cm_wm_prompt_v2`, `exp_qwen_empty_cm_wm_prompt_v2`, `exp_qwen1024_cm_wm_prompt_v2_r0..2` | 05, 08 | scored | Haiku 33.0, the control for G33; Qwen at 1,024 running |
| G35 | G08 + the T-REx structure guide (linking + planning) | test 06 **arm B**, "the guide", "guide alone", preset `guide_b`, `exp_real_tg_b_guide`, `..._sameday`, `..._sameday2`, `exp_qwen_empty_b_guide`, `exp_qwen_empty_b_guide_sameday`, `exp_qwen1024_b_guide_r0..2` | 06, 08; Flotilla Memory routes | scored | **GRAFT default** (user): Haiku 45.7, 46.0, 46.7 vs mode C 34-35 |
| G36 | G08 on full T-REx, T-REx edges walk-only at weight 0.2 | test 06 **arm C**, "bridge", `exp_real_tg_c_bridge` | 06 | scored | 17.3; T-REx hurts even walk-only; not adopted |
| G37 | G36 + 5 labelled background facts | test 06 **arm D**, "background", `exp_real_tg_d_background` | 06 | scored | 17.7; not adopted |
| G38 | G35 + working memory in the graph (v2), the guide's chain cited from the first step | test 06 **arm E**, "guide + working memory", `exp_real_tg_e_guide_wm_v2`, `exp_qwen_empty_e_guide_wm_v2`, `exp_qwen1024_e_guide_wm_v2_r0..2` | 06, 08 | scored | Haiku 46.7, level with the guide at 2x cost: **parked, not dropped** (user); Qwen at 1,024 running |

| G39 | G35 with a drop cutoff: G35's ranking, first k facts, k at the largest score drop (10-100, pool 200) | (new, 2026-11-22) | 09 | scored: 47.3 vs G35 48.3 with 33.1 facts (34% fewer), lost by 1 in every same-day pair, gold in facts 56% vs 59%; undecided (30% bar not confirmed), into the LongMemEval retrieval comparison | design: [graft_adaptive_retrieval_design.md](../design/graft_adaptive_retrieval_design.md) |
| G40 | G39, then Qwen may ask for 50 more facts (at most 3 asks, cap 200, stop when nothing new) | (new, 2026-11-22) | 09 | scored: 47.7 vs G35 48.3 with 67.9 facts and 2.8 calls; undecided, into the LongMemEval retrieval comparison | as G39 |
| G41 | G35 on graphs from writer v2 (chat prompt, reply log, salvage), thinking off | (new, 2026-11-22) | LongMemEval dev | running | design: [graft_longmemeval_plan_design.md](../design/graft_longmemeval_plan_design.md) |
| G42 | G41 with Qwen thinking on in the build, writer cap 16,384 | (new, 2026-11-22) | LongMemEval dev | dropped | dropped by the user 2026-11-22: 336 of 358 extraction calls stopped at the 16,384-token cap with an empty reply (the thinking used the budget); jobs Fir 5133097-5133100 cancelled after 1 h 49 min, no graph finished. G43 and G46 build on G41 |
| G43 | the better of G41/G42 with the user node (first-person questions link "user") | (new, 2026-11-22) | LongMemEval dev | designed | as G41 |
| G44 | G43 with a chat guide instead of the T-REx guide | (new, 2026-11-22) | LongMemEval dev | designed | Dialogue NLI (user, 2026-11-22); leakage check and guide build done (Flotilla run log 2026-11-22) |
| G45 | G43 without any guide (mode C alone) | (new, 2026-11-22) | LongMemEval dev | designed | the no-guide control for G43/G44 |
| G46 | the better of G41/G42 with bitemporal facts: said time (session date or serial) for supersede, event time (resolved from the text) for temporal questions | (new, 2026-11-22) | LongMemEval temporal dev | designed | design: [graft_bitemporal_design.md](../design/graft_bitemporal_design.md); built after writer v2's results |
| G47 | G35 with 100 facts shown instead of 50 (fixed count, G35's ranking) | (new, 2026-11-22) | LongMemEval dev retrieval comparison | designed | named by the user's retrieval comparison on the writer-v2 graphs |
| G48 | G35 with 200 facts shown (fixed count, G35's ranking) | (new, 2026-11-22) | LongMemEval dev retrieval comparison | designed | as G47 |
Not a candidate: the **Haiku check** (`exp_real_replay38`, `exp_real_canary_replay38`) re-answers G08's saved
2026-11-13 facts with no retrieval; it checks Haiku, not a method. It keeps its name and has a setup (S101).

## 2. Candidate parts

Columns are the settings that vary across the 304 configs; "-" means off. All use the 3-layer GNN trained on synthetic
graphs and bge-small embeddings. Read order: A = `gnn_goat`, B = `goat_ppr`, C = `ppr_goat_ppr`.

| ID | Read order | Explainer | Subgraph nodes | GNN | Facts | Start graph | Base linking | Base role | Guide | Entity linking | Embedding mix | Question layer | Working memory |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G01 | A | GOAt | 400 | 400-node | 300 | empty | - | - | - | exact | - | - | - |
| G02 | GNN top-k | GOAt | 400 | 400-node | 300 | empty | - | - | - | exact | - | - | - |
| G03 | PageRank | - | - | - | 300 | empty | - | - | - | exact | - | - | - |
| G04 | A | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | - |
| G05 | GNN top-k | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | - |
| G06 | PageRank | - | - | - | 50 | empty | - | - | - | exact | - | - | - |
| G07 | B | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | - |
| G08 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | - |
| G09 | A | GOAt | 400 | 400-node | 50 | synthetic | - | - | - | exact | - | - | - |
| G10 | A | EiG | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | - |
| G11 | C | EiG | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | - |
| G12 | C | EiG | 400 | 400-node | 50 | empty | - | - | - | exact | interleave | - | - |
| G13 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | interleave | - | - |
| G14 | C | EiG | 800 | 400-node | 50 | empty | - | - | - | exact | interleave | - | - |
| G15 | C | EiG | 1,600 | 400-node | 50 | empty | - | - | - | exact | interleave | - | - |
| G16 | C | EiG | 400 | 400-node | 50 | empty | - | - | - | exact | top-10 | - | - |
| G17 | C | EiG | 400 | 400-node | 50 | empty | - | - | - | exact | top-5 | - | - |
| G18 | C | EiG | 400 | 400-node | 50 | empty | - | - | - | exact + embedding k=5 | - | - | - |
| G19 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact + embedding k=5 | - | - | - |
| G20 | C | EiG | 400 | 400-node | 50 | empty | - | - | - | exact + embedding k=5 | interleave | - | - |
| G21 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact + embedding k=5 | interleave | - | - |
| G22 | C | EiG | 400 | 1,600-node | 50 | empty | - | - | - | exact | - | - | - |
| G23 | C | EiG | 400 | 400-node | 50 | empty | - | - | - | exact | - | embedding match | - |
| G24 | C | EiG | 400 | 400-node | 50 | RoG (Freebase, 20K facts) | exact name | facts | - | exact | - | - | - |
| G25 | C | EiG | 400 | 400-node | 50 | RoG | Haiku (top 10) | facts | - | exact | - | - | - |
| G26 | C | EiG | 400 | 400-node | 50 | T-REx dense core | Haiku (top 10) | facts | - | exact | - | - | - |
| G27 | C | EiG | 400 | 400-node | 50 | T-REx full (45 properties) | Haiku (top 10) | facts | - | exact | - | - | - |
| G28 | C | GOAt | 400 | 400-node | 50 | T-REx full | Haiku (top 10) | facts | - | exact | - | - | - |
| G29 | C | EiG | 400 | 400-node | 50 | T-REx full | Haiku (top 10) | facts | - | exact | - | Haiku match | - |
| G30 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | embedding match | - |
| G31 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | graph, v1 |
| G32 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | prompt only, v1 |
| G33 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | graph, v2 |
| G34 | C | GOAt | 400 | 400-node | 50 | empty | - | - | - | exact | - | - | prompt only, v2 |
| G35 | C | GOAt | 400 | 400-node | 50 | empty | - | - | T-REx guide (248 properties): linking + planning | exact | - | - | - |
| G36 | C | GOAt | 400 | 400-node | 50 | T-REx full | Haiku (top 10) | walk only, weight 0.2 | - | exact | - | - | - |
| G37 | C | GOAt | 400 | 400-node | 50 | T-REx full | Haiku (top 10) | walk only, weight 0.2, + 5 labelled background facts | - | exact | - | - | - |
| G38 | C | GOAt | 400 | 400-node | 50 | empty | - | - | T-REx guide: linking + planning | exact | - | - | graph, v2 |
| G47 | C | GOAt | 400 | 400-node | 100 | empty | - | - | T-REx guide (248 properties): linking + planning | exact | - | - | - |
| G48 | C | GOAt | 400 | 400-node | 200 | empty | - | - | T-REx guide (248 properties): linking + planning | exact | - | - | - |

Outside baseline, same table: Embedding RAG (bge-small) = embedding search over GRAFT's facts, 50 facts, no graph walk
(`exp_embed_fake_mh_262k`, free check only).

## 3. Setups

All GRAFT setups use MemoryAgentBench FactConsolidation (MAB FC) with 512-token chunks and substring exact match (the
benchmark's metric; user rule 2026-11-21: match the comparison's metric). "Scripted" = fake mode (no model; free check).
Runs lists the run names (one or more run folders each; a run folder name adds a timestamp and job id).
LongMemEval setups of G35 (one chunk per session, Qwen writing the graphs, Haiku judge) are Flotilla setups (S138-S141),
since GRAFT runs there inside a Flotilla route.

| Setup | Candidate | Answering model | Answer cap | Benchmark | Runs (run names) |
|---|---|---|---|---|---|
| S01 | G01 | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_graft_gnn_goat_262k`, `graft_goat_bge_262k`, `sgar_goat_bge_262k` |
| S02 | G01 | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `graft_goat_fake_6k` |
| S03 | G01 | scripted (fake) | 16 | MAB FC 6k sh+mh, first 5 q | `ui_sgar_6k_fake` |
| S04 | G02 | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_graft_gnn_topk_262k`, `graft_topk_bge_262k`, `sgar_topk_bge_262k` |
| S05 | G02 | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `graft_topk_fake_6k` |
| S06 | G03 | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_graft_ppr_262k` |
| S07 | G03 | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `graft_ppr_fake_6k` |
| S08 | G04 | Haiku 5.5 | 16 | MAB FC 262k mh | `exp_a_real_mh_262k` |
| S09 | G04 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_a_real_mh_262k_ans256` |
| S10 | G04 | scripted (fake) | 16 | MAB FC 262k sh+mh | `exp_a_fake_262k`, `graft_goat_budget50_262k`, `sgar_goat_budget50_262k` |
| S11 | G05 | scripted (fake) | 16 | MAB FC 262k sh+mh | `graft_topk_budget50_262k`, `sgar_topk_budget50_262k` |
| S12 | G06 | scripted (fake) | 16 | MAB FC 262k sh+mh | `graft_ppr_budget50_262k`, `sgar_ppr_budget50_262k` |
| S13 | G07 | Haiku 5.5 | 16 | MAB FC 262k mh | `exp_b_real_mh_262k` |
| S14 | G07 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_b_real_mh_262k_ans256` |
| S15 | G07 | scripted (fake) | 16 | MAB FC 262k sh+mh | `exp_b_fake_262k` |
| S16 | G08 | Haiku 5.5 | 16 | MAB FC 262k mh | `exp_c_real_mh_262k` |
| S17 | G08 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256`, `exp_c_real_mh_262k_ans256_rerun28d4fd5`, `exp_real_tg_a_sameday`, `exp_real_wm_empty_a_modec_rerun1121`, `exp_wm_empty_a_modec` |
| S18 | G08 | Qwen3.8-27B W4A16 | 256 | MAB FC 262k mh | `exp_qwen_empty_a_modec` |
| S19 | G08 | Qwen3.8-27B W4A16 | 1024 | MAB FC 262k mh | `exp_qwen1024_a_modec_r0`, `exp_qwen1024_a_modec_r1`, `exp_qwen1024_a_modec_r2` |
| S20 | G08 | scripted (fake) | 16 | MAB FC 262k sh+mh | `exp_c_fake_262k` |
| S21 | G09 | Haiku 5.5 | 16 | MAB FC 262k mh | `exp_d_extend_real_mh_262k` |
| S22 | G09 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_d_extend_real_mh_262k_ans256` |
| S23 | G09 | scripted (fake) | 16 | MAB FC 262k mh | `exp_d_extend_fake_mh_262k` |
| S24 | G10 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_a_real_mh_262k_ans256_eig` |
| S25 | G10 | scripted (fake) | 256 | MAB FC 262k mh | `exp_a_fake_mh_262k_eig_check` |
| S26 | G11 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_base_eig` |
| S27 | G12 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_hybrid_eig` |
| S28 | G12 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_hybrid_eig`, `exp_c_fake_mh_262k_hybrid_eig_n400`, `exp_c_fake_mh_262k_hybrid_eig_src` |
| S29 | G13 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_hybrid_goat` |
| S30 | G13 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_hybrid_goat`, `exp_c_fake_mh_262k_hybrid_goat_src` |
| S31 | G14 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_hybrid_eig_n800` |
| S32 | G15 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_hybrid_eig_n1600` |
| S33 | G16 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_topk10_eig` |
| S34 | G16 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_topk10_eig` |
| S35 | G17 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_topk5_eig` |
| S36 | G18 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_link_eig` |
| S37 | G19 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_link_goat` |
| S38 | G20 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_both_eig` |
| S39 | G21 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_both_goat` |
| S40 | G22 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_gnn1600_eig` |
| S41 | G23 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_qgraph_eig` |
| S42 | G23 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_qgraph_eig` |
| S43 | G24 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_rog_build_eig` |
| S44 | G25 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_rog_link_build_eig` |
| S45 | G25 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_rog_link_eig` |
| S46 | G26 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_trex_link_build_eig` |
| S47 | G26 | scripted (fake) | 256 | MAB FC 262k mh | `exp_c_fake_mh_262k_trex_link_eig` |
| S48 | G27 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_trexfull_eig_pprfix`, `exp_c_real_mh_262k_ans256_trexfull_link_build_eig` |
| S49 | G27 | Haiku 5.5 | 256 | MAB FC 262k mh, first 5 q | `exp_c_real_mh_262k_ans256_trexfull_eig_pprfix_check5` |
| S50 | G27 | Qwen3.8-27B W4A16 | 256 | MAB FC 262k mh | `exp_c_qwen_mh_262k_ans256_trexfull_eig` |
| S51 | G28 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_trexfull_goat`, `exp_c_real_mh_262k_ans256_trexfull_goat_pprfix` |
| S52 | G28 | Qwen3.8-27B W4A16 | 256 | MAB FC 262k mh | `exp_c_qwen_mh_262k_ans256_trexfull_goat` |
| S53 | G29 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_c_real_mh_262k_ans256_trexfull_qgraph_eig`, `exp_c_real_mh_262k_ans256_trexfull_qgraph_eig_pprfix` |
| S54 | G29 | Qwen3.8-27B W4A16 | 256 | MAB FC 262k mh | `exp_c_qwen_mh_262k_ans256_trexfull_qgraph_eig` |
| S55 | G30 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_wm_empty_b_qlayer` |
| S56 | G31 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_wm_empty_c_wm_graph` |
| S57 | G31 | scripted (fake) | 256 | MAB FC 262k mh, first 5 q | `exp_wm_fake_check_c_wm_graph` |
| S58 | G32 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_wm_empty_cm_wm_prompt` |
| S59 | G33 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_wm_empty_c_wm_graph_v2` |
| S60 | G33 | Qwen3.8-27B W4A16 | 256 | MAB FC 262k mh | `exp_qwen_empty_c_wm_graph_v2` |
| S61 | G33 | Qwen3.8-27B W4A16 | 1024 | MAB FC 262k mh | `exp_qwen1024_c_wm_graph_v2_r0`, `exp_qwen1024_c_wm_graph_v2_r1`, `exp_qwen1024_c_wm_graph_v2_r2` |
| S62 | G34 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_wm_empty_cm_wm_prompt_v2` |
| S63 | G34 | Qwen3.8-27B W4A16 | 256 | MAB FC 262k mh | `exp_qwen_empty_cm_wm_prompt_v2` |
| S64 | G34 | Qwen3.8-27B W4A16 | 1024 | MAB FC 262k mh | `exp_qwen1024_cm_wm_prompt_v2_r0`, `exp_qwen1024_cm_wm_prompt_v2_r1`, `exp_qwen1024_cm_wm_prompt_v2_r2` |
| S65 | G35 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_real_tg_b_guide`, `exp_real_tg_b_guide_sameday`, `exp_real_tg_b_guide_sameday2` |
| S66 | G35 | Qwen3.8-27B W4A16 | 256 | MAB FC 262k mh | `exp_qwen_empty_b_guide`, `exp_qwen_empty_b_guide_sameday` |
| S67 | G35 | Qwen3.8-27B W4A16 | 1024 | MAB FC 262k mh | `exp_qwen1024_b_guide_r0`, `exp_qwen1024_b_guide_r1`, `exp_qwen1024_b_guide_r2` |
| S68 | G36 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_real_tg_c_bridge` |
| S69 | G37 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_real_tg_d_background` |
| S70 | G38 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_real_tg_e_guide_wm_v2` |
| S71 | G38 | Qwen3.8-27B W4A16 | 256 | MAB FC 262k mh | `exp_qwen_empty_e_guide_wm_v2` |
| S72 | G38 | Qwen3.8-27B W4A16 | 1024 | MAB FC 262k mh | `exp_qwen1024_e_guide_wm_v2_r0`, `exp_qwen1024_e_guide_wm_v2_r1`, `exp_qwen1024_e_guide_wm_v2_r2` |
| S73 | BM25 | Haiku 5.5 | 16 | MAB FC 262k mh | `exp_bm25_real_mh_262k` |
| S74 | BM25 | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_bm25_real_mh_262k_ans256` |
| S75 | BM25 | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_bm25_262k` |
| S76 | BM25 | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `bm25_fake_6k` |
| S77 | BM25 | scripted (fake) | 16 | MAB FC 6k sh+mh, first 5 q | `ui_bm25_6k_fake` |
| S78 | Embedding RAG (bge-small) | scripted (fake) | 256 | MAB FC 262k mh | `exp_embed_fake_mh_262k` |
| S79 | HippoRAG 2 (bundled) | Haiku 5.5 | 16 | MAB FC 262k mh | `exp_hipporag_real_mh_262k` |
| S80 | HippoRAG 2 (bundled) | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_hipporag_real_mh_262k_ans256` |
| S81 | HippoRAG 2 (bundled) | Haiku 5.5 | 2048 | MAB FC 262k mh | `exp_hipporag_real_mh_262k_ans2048` |
| S82 | HippoRAG 2 (bundled) | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_hipporag_bundled_262k` |
| S83 | HippoRAG 2 (bundled) | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `hipporag_bundled_fake_6k` |
| S84 | HippoRAG 2 (upstream) | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_hipporag_upstream_262k` |
| S85 | HippoRAG 2 (upstream) | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `hipporag_upstream_fake_6k` |
| S86 | Knowl | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `knowl_fake_6k` |
| S87 | Letta (bundled) | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_letta_bundled_262k` |
| S88 | Letta (bundled) | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `letta_bundled_fake_6k` |
| S89 | Letta (upstream) | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_letta_upstream_262k` |
| S90 | Letta (upstream) | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `letta_upstream_fake_6k` |
| S91 | Long context (128K) | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_long_context_128k_262k` |
| S92 | Long context (128K) | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `long_context_128k_fake_6k` |
| S93 | Long context (full) | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_long_context_262k` |
| S94 | Long context (full) | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `long_context_fake_6k` |
| S95 | Mem0 (bundled) | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_mem0_bundled_262k` |
| S96 | Mem0 (bundled) | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `mem0_bundled_fake_6k` |
| S97 | Mem0 (upstream) | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_mem0_upstream_262k` |
| S98 | Mem0 (upstream) | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `mem0_upstream_fake_6k` |
| S99 | Total Agent Memory | scripted (fake) | 16 | MAB FC 262k sh+mh | `dryrun_total_agent_memory_262k` |
| S100 | Total Agent Memory | scripted (fake) | 16 | MAB FC 6k sh+mh, first 3 q | `total_agent_memory_fake_6k` |
| S101 | Haiku check (replay) | Haiku 5.5 | 256 | MAB FC 262k mh | `exp_real_canary_replay38`, `exp_real_replay38` |
| S163 | G41 (G35's rule, 50 facts) | Qwen3.8-27B W4A16 via Flotilla's Memory route (base route Fast) | 32,768 | LongMemEval dev (76), graphs from G41's fixed writer (`lme/devv2/cache_g41_fix`), Haiku 5.5 judge | `lme/devv2/ret/f50/r0..2` (Flotilla `configs/systems/lme_retrieval/f50.json`) |
| S164 | G47 (100 facts) | Qwen3.8-27B W4A16 via Flotilla's Memory route (base route Fast) | 32,768 | LongMemEval dev (76), graphs from G41's fixed writer (`lme/devv2/cache_g41_fix`), Haiku 5.5 judge | `lme/devv2/ret/f100/r0..2` (Flotilla `configs/systems/lme_retrieval/f100.json`) |
| S165 | G48 (200 facts) | Qwen3.8-27B W4A16 via Flotilla's Memory route (base route Fast) | 32,768 | LongMemEval dev (76), graphs from G41's fixed writer (`lme/devv2/cache_g41_fix`), Haiku 5.5 judge | `lme/devv2/ret/f200/r0..2` (Flotilla `configs/systems/lme_retrieval/f200.json`) |
| S166 | G39 (drop cutoff, pool 200) | Qwen3.8-27B W4A16 via Flotilla's Memory route (base route Fast) | 32,768 | LongMemEval dev (76), graphs from G41's fixed writer (`lme/devv2/cache_g41_fix`), Haiku 5.5 judge | `lme/devv2/ret/g39/r0..2` (Flotilla `configs/systems/lme_retrieval/g39.json`) |
| S167 | G40 (cutoff + up to 3 asks of 50, cap 200) | Qwen3.8-27B W4A16 via Flotilla's Memory route (base route Fast) | 32,768 | LongMemEval dev (76), graphs from G41's fixed writer (`lme/devv2/cache_g41_fix`), Haiku 5.5 judge | `lme/devv2/ret/g40/r0..2` (Flotilla `configs/systems/lme_retrieval/g40.json`) |

## 4. Runs

A run is one run folder (`<run name>_<timestamp>[_j<job>]`). Its setup is the row above whose run names hold its run
name; `experiments/test-NN-*/runs/run-NN/` records which runs each test used. After approval each test's table gains a
setup column.

## 5. Pre-fix runs marked invalid (under each test's Revisions, 2026-11-21)

| Runs | Setup | Bug (fixed, no config switch) | Why invalid |
|---|---|---|---|
| `exp_c_real_mh_262k_ans256_trexfull_link_build_eig` (answer pass), `exp_c_real_mh_262k_ans256_trexfull_goat`, `exp_c_real_mh_262k_ans256_trexfull_qgraph_eig` (GRAFT test 04 run-01) | S48, S51, S53 | NetworkX PageRank's stop rule grows with graph size: on 1.58M nodes it stopped after one step and returned 0 facts; also the all-caps entity "THE" linked to "the" in 89 of 100 questions | answers came from no or wrong facts; the pprfix runs (test 04 run-02) replace them |
| test 06 run-01 Haiku checks (B and D batches) | S101 | two jobs of one config shared a run folder (fixed in `eval/run.py` with job ids in folder names) | the two checks overwrote each other; no clean check that round |
| `exp_qwen_empty_*_j28252727` (GRAFT test 08 run-01) | S18, S60, S63, S66 | not invalid: a rerun (28263641) resumed the failed job's empty folders (fixed, `eval/run.py`) | results are valid, only the folder names point to the wrong job; noted under test 08 Revisions |

## 6. Conventions

- Setup IDs are one sequence across both repos (GRAFT S01-S101, Flotilla S102 onward); free-check setups have IDs too.
- Qwen setups that never finished (S50, S52, S54: Qwen on the full T-REx candidates, jobs cancelled before an answer)
  keep their IDs.
- Long-history study (design 2026-11-22, [graft_long_history_design.md](../design/graft_long_history_design.md)): no new candidate; G35, the writer-v2 winner and Flotilla's F15 get setups at run time. Flotilla's F35 (reasoning-graph route) uses GRAFT's work layer on an empty graph.
- Next free IDs: G49, S171 (S shared with Flotilla; S147-S162 and S168-S170 are Flotilla setups, S163-S167 the LongMemEval retrieval comparison). New parts from G39 on: Fact count (G39, G40), Writer (G41, G42), user node (G43), guide source (G44, G45).
