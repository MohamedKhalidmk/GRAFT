# Tests (GRAFT)

56 tests in 17 files, in plain words. Generated from each test's docstring by `scripts/make_tests_doc.py`; to change a line, edit the docstring and rerun the script. `tests/test_tests_doc.py` fails if a test is missing here or a line is out of date. The Gaps section at the end is written by hand.

## [tests/test_adaptive.py](../../tests/test_adaptive.py)

Adaptive retrieval (G39 drop cutoff, G40 ask for more; docs/design/graft_adaptive_retrieval_design.md). Offline.

| Test | What it checks | Guards against |
|---|---|---|
| `test_drop_cut_is_the_largest_ratio_drop_within_bounds` | Checks that drop_cut cuts at the largest score ratio drop between the lo and hi bounds, including zero-score, flat and short lists. | the answering model being shown a long tail of weak facts, or too few facts, because the cut misses the clear score gap. |
| `test_drop_cutoff_keeps_g35_order_and_only_changes_the_count` | Checks that the adaptive drop cutoff keeps the fixed-count retriever's fact ranking and only changes how many facts are shown, also on the fallback. | turning on the cutoff silently reordering the retrieved facts, so the comparison with the fixed-count run measures two changes at once. |
| `test_wants_more_only_on_the_ask_phrase` | Checks that wants_more fires only when the reply ends with the exact NEED MORE MEMORIES phrase. | a real answer that merely mentions needing more memories being thrown away and treated as a request for another batch. |
| `test_ask_loop_adds_batches_within_the_limits` | Checks that each NEED MORE MEMORIES reply adds the next batch of pool facts, and that the ask limit and the end of the pool stop the loop. | a model that keeps asking for more memories looping past the ask limit or past the end of the retrieved pool. |
| `test_user_node_links_first_person_questions` | Checks that with user_node on, first-person questions (I, my, me) also link the writer's user entity, and other questions link as before. | a chat question like 'What did I buy?' linking no entity, so the user's own facts are never reached. |

## [tests/test_bridge.py](../../tests/test_bridge.py)

Bridge option (test 06 arm C): outside-base facts walk at a lower weight and are never returned.

| Test | What it checks | Guards against |
|---|---|---|
| `test_bridge_weights_only_base_edges` | Checks that bridge_weight lowers the walk weight only on edges touching base-layer facts, and that no weights exist when it is off. | document-to-document edges being down-weighted too, or the default walk changing when the bridge option is not used. |
| `test_document_facts_only` | Checks that document_facts_only drops base-layer facts from the returned facts, and that turning it off returns them again. | outside-base knowledge facts being shown to the answering model as if they came from the documents. |
| `test_background_facts` | Checks that background_facts keeps base facts out of the memories but returns them separately, rendered under the background conflict rule. | base facts being lost entirely, or shown without the label saying the documents' knowledge pool wins a conflict. |

## [tests/test_chat_guide.py](../../tests/test_chat_guide.py)

Chat guide input (G44): Dialogue NLI triples -> facts for scripts/trex_guide.py --triples. Offline, toy data.

| Test | What it checks | Guards against |
|---|---|---|
| `test_dnli_triples_keeps_clean_sentences_and_types` | Checks that dnli_triples.py keeps only triples whose sentence passed the leakage check, maps 'i' to user and relations to labels, and adds type lines. | triples from sentences that overlap a test set leaking into the chat guide, or the guide getting raw relation names it cannot match. |

## [tests/test_core.py](../../tests/test_core.py)

Offline tests of the core: no API calls anywhere (every run uses llm.mode: fake).

| Test | What it checks | Guards against |
|---|---|---|
| `test_translate_drops_sampling_and_maps_tools` | Checks that OpenAI-format requests become Anthropic requests with sampling dropped, thinking off and tool calls mapped, and that tool replies map back. | baselines that send OpenAI tool calls getting broken requests, or settings like temperature slipping through to the model. |
| `test_cost_uses_long_prompt_rate_above_100k` | Checks that token_cost charges the long-prompt rate above 100K prompt tokens and the short rate below it. | long-context runs being reported at the cheaper short-prompt price. |
| `test_scoring_is_the_benchmarks_substring_match` | Checks that scoring uses the benchmark's normalized substring match and that answer_in_text finds a gold answer in retrieved text. | a correct answer with different case or trailing punctuation being scored wrong, making results incomparable with the benchmark. |
| `test_graph_store_supersede_chain_and_roundtrip` | Checks that a chain of SUPERSEDES edges resolves to the newest fact and survives saving and loading the graph. | a reloaded graph losing its revision links, so an older fact is shown to the answering model as current. |
| `test_rule_writer_supersedes_newer_fact_and_keeps_old` | Checks that the rule writer marks a later fact with the same subject and relation as superseding the earlier one, keeping both, and splits numbered facts. | a revised fact sitting next to its old version with no SUPERSEDES edge, so retrieval can return the outdated value. |
| `test_features_have_one_edge_per_node_pair` | Checks that the GNN features hold one edge per node pair, even for a fact whose subject and object are the same entity. | GOAt crashing on parallel edges, since it indexes edges by (a, b) and subject == object facts create them. |
| `test_subgraph_selection_reaches_past_a_hub` | Checks that subgraph selection still reaches the end of a chain when a hub entity on the way has hundreds of neighbours. | nearest-first selection filling the node budget with the hub's neighbours, so PPR never reaches the answer node. |
| `test_sh_and_mh_share_one_context` | Checks that the single-hop and multi-hop splits are built over one shared context and that the questions carry no gold answers. | a method seeing gold answers in its questions, or building a separate memory per split. |
| `test_fake_run_end_to_end` | Checks that each listed config runs end to end in fake LLM mode, answers every question, and logs a question index on every query call. | a pipeline break that leaves questions unanswered or query usage untraceable being found only on a paid cluster run. |
| `test_synthetic_training_data_has_no_benchmark_entities` | Checks that no entity name from the synthetic GNN training worlds appears in the benchmark context. | the GNN being trained on benchmark entities, which would leak test content into its training. |
| `test_registry_configs_are_valid` | Checks that every run config under configs/runs names a method registered in eval.methods. | a run config with a misspelled or removed method failing only after it is submitted to the cluster. |
| `test_nearest_nodes_is_breadth_first_and_capped` | Checks that nearest_nodes starts at the seed, takes its one-hop facts first, and stops at the node cap. | the GNN subgraph growing past its node budget or skipping the seed entity's own facts. |
| `test_experiment_b_and_c_modes_return_newest_facts` | Checks that the B and C retrieval modes run end to end with an untrained GCN and return only the newest version of a revised fact. | the GNN modes returning a superseded fact, so an older fact is shown to the answering model as current. |
| `test_extend_mode_starts_from_synthetic_graph_and_prompts_its_pattern` | Checks that in extend mode (experiment D) the writer starts from the synthetic graph and its prompt lists that graph's relations. | the extend arm silently running as the plain writer, or the extend instruction leaking into the default prompt. |
| `test_shared_graph_is_built_once_then_loaded` | Checks that the first agent builds and saves the shared graph and a second agent loads it instead of writing its own chunks. | every repeat rebuilding the shared graph, paying for extraction again and possibly getting a different graph. |
| `test_embedding_linking_and_hybrid_on_mode_c` | Checks that link_embed_k keeps exact entity matches first and adds k more, and that hybrid interleaves graph and embedding facts without duplicates. | embedding links pushing out the exact match, or hybrid merging returning duplicate facts or more facts than the budget. |
| `test_hybrid_labels_sources_and_embed_mode_needs_no_gnn` | Checks that hybrid retrieval labels each fact with its source, embed mode runs without a GNN, and attribution classifies answers by source. | the attribution table crediting the graph or the embedding search for answers it did not find. |
| `test_hybrid_k_keeps_graph_head_and_adds_k_new_embedding_facts` | Checks that hybrid_k keeps the graph's top facts and fills the last k slots with new embedding facts, skipping ones already in the head. | embedding facts displacing the graph's best facts, or a duplicate embedding fact wasting one of the k slots. |
| `test_question_graph_is_attached_used_and_removed` | Checks that query_graph attaches parsed question edges as temporary nodes linked through matched entities, and removes them after retrieval. | temporary question nodes staying in the shared graph, or being returned to the answering model as retrieved facts. |
| `test_question_graph_needs_no_embedding_after_prepare` | Checks that after prepare_queries, question-graph retrieval reads only cached vectors and never calls the embedder. | forked retrieval workers, which cannot embed, failing mid-run on a question-graph name that was not embedded up front. |
| `test_entity_linker_maps_names_to_base_entities_and_logs` | Checks that the entity linker maps a new name to the base entity the LLM picks, caches it, asks only about unseen names, and logs every decision. | 'USA' and 'United States of America' becoming separate entities, or the linker paying to ask about the same name twice. |
| `test_question_layer_uses_llm_links_not_the_embedding_threshold` | Checks that with LLM query linking, question names link only where the LLM picked an entity, with no embedding-threshold fallback. | a name the LLM judged new being linked anyway to a lookalike entity by embedding similarity. |
| `test_build_resumes_from_checkpoint_after_a_cut_off` | Checks that a build cut off mid-way resumes from the last checkpoint without rewriting earlier chunks, and deletes the checkpoint once saved. | a job that hits its time limit paying to rewrite every chunk, or a stale checkpoint being picked up by a later build. |

## [tests/test_eig.py](../../tests/test_eig.py)

EiG-Search attribution: the batched version matches EiG-Search's own per-edge loop (main.py, NC branch).

| Test | What it checks | Guards against |
|---|---|---|
| `test_batched_matches_eig_loop` | Checks that the batched EiG edge attributions give the same top-k scores and edges as EiG-Search's own per-edge loop. | the faster batched version ranking different edges than the published method, so results labelled EiG are not EiG's. |

## [tests/test_gateway_trace.py](../../tests/test_gateway_trace.py)

Gateway usage log traceability: request hash (same request -> same hash), message and request IDs, reply hash;

| Test | What it checks | Guards against |
|---|---|---|
| `test_trace_fields` | Checks that the gateway usage log records request and message IDs, a request hash that ignores dropped params, a reply hash, and the dropped params. | a logged call that cannot be traced back to its API request, or the internal request ID leaking into the client's reply. |

## [tests/test_guide.py](../../tests/test_guide.py)

T-REx structure guide (my_method/guide.py) on a toy graph: relation mapping adds missed revisions, same-entity merges

| Test | What it checks | Guards against |
|---|---|---|
| `test_link_pass` | Checks that the guide's link pass adds a revision missed across relation spellings and merges same-entity names only when their types agree. | an old citizenship shown as current because two spellings of one relation hid the revision, or a planet merged with a newspaper. |
| `test_plan_direct_and_bridged` | Checks that planning follows a chain of direct facts, and bridges a hop through the document relation when no fact has the planned one. | a multi-hop question failing because the documents spell a relation differently from the planned T-REx relation. |

## [tests/test_hipporag_fake.py](../../tests/test_hipporag_fake.py)

Both HippoRAG-v2 variants run end to end through eval.run in fake LLM mode.

| Test | What it checks | Guards against |
|---|---|---|
| `test_fake_run_answers_every_question` | Checks that each HippoRAG-v2 variant runs end to end in fake mode, answers every question, and makes one NER and one triple call per chunk. | a broken HippoRAG install or adapter leaving questions unanswered or building an empty graph, found only on a paid run. |

## [tests/test_knowl_tam_fake.py](../../tests/test_knowl_tam_fake.py)

Knowl and total-agent-memory run end to end through eval.run in fake LLM mode.

| Test | What it checks | Guards against |
|---|---|---|
| `test_fake_run_answers_every_question` | Checks that Knowl and total-agent-memory each run end to end through eval.run in fake mode and answer every question. | a broken baseline environment or adapter leaving questions unanswered, found only on a paid run. |

## [tests/test_letta_fake.py](../../tests/test_letta_fake.py)

Both MemGPT / Letta variants run end to end through eval.run in fake LLM mode.

| Test | What it checks | Guards against |
|---|---|---|
| `test_fake_run_answers_every_question` | Checks that each Letta variant runs end to end in fake mode, stores every chunk, searches then answers per question, and returns the fake answer. | a Letta failure turning into the benchmark's 'Error' answer and being scored as a normal wrong answer instead of failing. |

## [tests/test_mem0_fake.py](../../tests/test_mem0_fake.py)

Both Mem0 variants run end to end on the fake gateway (no API calls).

| Test | What it checks | Guards against |
|---|---|---|
| `test_mem0_fake_run` | Checks that each Mem0 variant runs end to end on the fake gateway, stores memories, and records ADD events, plus UPDATE events for the bundled one. | Mem0 silently storing nothing, or the bundled version's update path never running, while still answering questions. |

## [tests/test_queue.py](../../tests/test_queue.py)

eval.queue runs several configs in one job; a failed run must fail the job (Nibi, 2026-11-22).

| Test | What it checks | Guards against |
|---|---|---|
| `test_queue_runs_every_config_and_fails_if_one_failed` | Checks that the queue still runs the configs after a failed one, then exits with an error naming the failed run. | a Slurm job reported COMPLETED although one of its runs died, so a missing repeat goes unnoticed. |
| `test_qwen_job_scripts_use_a_port_of_their_own` | Checks that the Fir and Nibi Qwen job scripts serve vLLM on a free port chosen per job, never a fixed one. | two jobs on one node sharing a server, so a run dies when the other job ends and shuts it down. |

## [tests/test_run_owner.py](../../tests/test_run_owner.py)

Run folders are owned by one job: only the same Slurm job (a requeue) resumes its unfinished folder. A rerun never

| Test | What it checks | Guards against |
|---|---|---|
| `test_own_folder` | Checks that a run folder counts as this job's own only when its owner file names the current Slurm job. | a rerun resuming another job's folder, dead or alive, or a run outside Slurm resuming anything. |
| `test_rerun_gets_a_new_folder` | Checks that a new Slurm job gets a new run folder even when a failed job left an unfinished folder of the same config. | a rerun writing its results into a dead job's run folder. |
| `test_requeue_resumes_its_own_folder` | Checks that a requeued job resumes its own unfinished folder, and starts a new one once that folder is finished. | a requeued job redoing its finished repeats, or a later attempt writing into an already finished folder. |

## [tests/test_session_docs.py](../../tests/test_session_docs.py)

Copied from Flotilla (keep both the same). The session documents (docs/session/) must match scripts/SHA256SUMS, which scripts/sync_session_docs.py

| Test | What it checks | Guards against |
|---|---|---|
| `test_session_docs_match_their_manifest` | Checks that the docs/session files match scripts/SHA256SUMS, with no file missing, extra or changed. | a session document edited in GRAFT alone drifting from Flotilla's copy. |
| `test_status_open_experiments_table` | Checks that STATUS.md's Open experiments table has the fixed columns, only the six states, a date on every row, and rows numbered 1..n. | an experiment row being deleted instead of having its state changed, so its record is lost. |

## [tests/test_tests_doc.py](../../tests/test_tests_doc.py)

docs/reference/TESTS.md lists every test, generated from the docstrings (scripts/make_tests_doc.py).

| Test | What it checks | Guards against |
|---|---|---|
| `test_tests_doc_lists_every_test_and_is_up_to_date` | Checks that every test has a two-line docstring and that TESTS.md matches what the docstrings generate. | a new or changed test that TESTS.md does not describe, so the plain-words list drifts from the code. |

## [tests/test_working_memory.py](../../tests/test_working_memory.py)

Working memory (my_method/working_memory.py) on a toy graph with a scripted LLM: steps chain through placeholders,

| Test | What it checks | Guards against |
|---|---|---|
| `test_graph_mode_chains_steps_and_links_work_layer` | Checks that graph-mode working memory fills each step's placeholder from the previous result, links a work layer, and removes it afterwards. | the second step asking about ?A instead of Bob, or work-layer nodes left behind in the shared graph. |
| `test_prompt_only_writes_nothing` | Checks that prompt_only working memory still chains the steps but adds no work nodes or edges to the graph. | the prompt-only arm writing work nodes into the graph, so it no longer differs from graph mode. |
| `test_guide_plan_is_cited_from_the_start` | Checks that with the guide and working memory together (test 06), the guide's planned facts reach every step prompt and the final facts. | the guide's planned chain being dropped when working memory runs, so the steps and the final answer never see it. |

## [tests/test_writer_v2.py](../../tests/test_writer_v2.py)

Writer v2 (G41/G42, docs/design/graft_longmemeval_plan_design.md): reply log, salvage of cut-off replies, the chat

| Test | What it checks | Guards against |
|---|---|---|
| `test_salvage_keeps_complete_facts_before_the_cut` | Checks that salvage_facts recovers every complete fact before the cut in a truncated reply, and returns None when there is none. | a writer reply cut off at the token cap losing every fact it already listed. |
| `test_reply_log_retry_and_salvage` | Checks that the writer retries an unparseable reply, salvages a cut-off one on the first try, and logs every attempt with its outcome. | failed or truncated writer replies vanishing without a trace in the reply log or the writer stats. |
| `test_chat_prompt_only_when_asked` | Checks that the chat writer rules go into the system prompt, before the JSON instruction, only for the chat_v2 prompt. | the chat rules leaking into the default writer prompt and changing results on the other benchmarks. |
| `test_gateway_thinking_switch` | Checks that the local OpenAI backend sends enable_thinking false by default and true only when thinking is switched on. | Qwen thinking by default as the writer and spending its token cap on reasoning instead of facts. |
| `test_bare_list_of_facts_is_read` | Checks that an extraction reply given as a bare JSON list of facts, whole or cut off, is read as the facts list. | a session's facts thrown away because Qwen answered [...] instead of {"facts": [...]}. |

## Gaps

Things nothing tests yet (written by hand; the generator keeps this section).

- **Supersede on chat histories with a real model.** The SUPERSEDES logic is tested on toy facts; whether Qwen's
  writer extracts both versions of a changed fact from real chat sessions, and retrieval puts the newer first, is a
  cluster check run from Flotilla (`flotilla/supersede_check.py`, status row 23).
- **Writer v2 on real Qwen replies.** Salvage and the reply log are tested on sample replies; parse-failure and
  empty-session rates come only from runs (G41).
- **Bitemporal facts (G46).** Designed, not built, so not tested.
- **Haiku drift.** The fixed Haiku check (canary) is a paid run before each batch, not a test.
- **IDs across documents.** Nothing checks that every run config names a candidate or setup that exists in the
  registry.
