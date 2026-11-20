"""Offline tests of the core: no API calls anywhere (every run uses llm.mode: fake).

    .venv/bin/python -m pytest tests -q
"""

import json
import random
from pathlib import Path

import pytest
import yaml

from baselines.claude_gateway.translate import anthropic_to_openai, openai_to_anthropic
from eval.benchmark import answer_in_text, build_task, score
from eval.cost import token_cost
from my_method.graph_store import GraphStore, Provenance
from my_method.writer import RuleWriter, split_numbered_facts

REPO = Path(__file__).resolve().parent.parent


def test_translate_drops_sampling_and_maps_tools():
    body = {"model": "gpt-4o-mini", "temperature": 0.7, "seed": 1, "max_tokens": 50,
            "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"},
                         {"role": "assistant", "content": None, "tool_calls": [
                             {"id": "c1", "type": "function", "function": {"name": "f", "arguments": "{\"a\": 1}"}}]},
                         {"role": "tool", "tool_call_id": "c1", "content": "result"}],
            "tools": [{"type": "function", "function": {"name": "f", "parameters": {"type": "object"}}}],
            "tool_choice": "required"}
    params, dropped = openai_to_anthropic(body, "claude-haiku-5-5")
    assert set(dropped) == {"temperature", "seed"} and "temperature" not in params
    assert params["system"] == "sys" and params["thinking"] == {"type": "disabled"}
    assert params["messages"][1]["content"][0] == {"type": "tool_use", "id": "c1", "name": "f", "input": {"a": 1}}
    assert params["messages"][2]["content"][0]["type"] == "tool_result"
    assert params["tool_choice"] == {"type": "any"}
    reply = anthropic_to_openai({"content": [{"type": "tool_use", "id": "t", "name": "f", "input": {}}],
                                 "stop_reason": "tool_use", "usage": {"input_tokens": 3, "output_tokens": 2}}, "x")
    assert reply["choices"][0]["finish_reason"] == "tool_calls"
    assert reply["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "f"


def test_cost_uses_long_prompt_rate_above_100k():
    assert token_cost("claude-haiku-5-5", 1_000_000, 0) == pytest.approx(0.50)  # >100K prompt: long card
    assert token_cost("claude-haiku-5-5", 50_000, 0) == pytest.approx(0.005)


def test_scoring_is_the_benchmarks_substring_match():
    assert score("Pesäpallo.", ["pesäpallo"])["substring_exact_match"] == 1.0
    assert score("ice hockey", ["pesäpallo"])["substring_exact_match"] == 0.0
    assert answer_in_text(["Rodez"], "450. Olga of Kiev died in the city of Rodez.")


def test_graph_store_supersede_chain_and_roundtrip(tmp_path):
    store = GraphStore()
    ids = [store.add_fact("X", "capital", obj, Provenance(0, store.take_arrival(), i, f"s{i}"))
           for i, obj in enumerate(["A", "B", "C"])]
    store.supersede(ids[1], ids[0])
    store.supersede(ids[2], ids[1])
    assert store.current(ids[0]) == ids[2] and store.is_superseded(ids[1])
    store.save(tmp_path / "g.json")
    loaded = GraphStore.load(tmp_path / "g.json")
    assert loaded.current(ids[0]) == ids[2] and loaded.stats() == store.stats()


def test_rule_writer_supersedes_newer_fact_and_keeps_old():
    store, writer = GraphStore(), RuleWriter(revisions=True)
    writer.write_chunk(0, "Here is a list of facts:\n1. The capital of Papal States is Rome. "
                          "2. The capital of Papal States is Watertown.", store)
    old, new = store.facts_with_key("Papal States", "capital")
    assert store.current(old) == new and store.fact(new)["object"] == "Watertown"
    assert split_numbered_facts("tail of a fact. 7. A is married to B.") == [(None, "tail of a fact."), (7, "A is married to B.")]


def test_features_have_one_edge_per_node_pair():
    """GOAt indexes edges by (a, b), so parallel edges crash it (subject == object facts make them)."""
    from baselines.claude_gateway.embeddings import load_embedder
    from my_method.gnn.features import TextEmbedder, build_features
    store = GraphStore()
    store.add_fact("X", "same as", "X", Provenance(0, store.take_arrival(), 0, "X same as X"))
    t = build_features(store, list(store.g.nodes), ["e:x"], "X?", TextEmbedder(load_embedder("hash:16")))
    pairs = t.edge_index.t().tolist()
    assert len(pairs) == 2 and len({tuple(p) for p in pairs}) == 2


def test_subgraph_selection_reaches_past_a_hub():
    """Nearest-first selection fills up on a hub's neighbours; PPR must still reach the chain's end."""
    from my_method.gnn.features import select_subgraph
    store = GraphStore()

    def fact(s, o):
        store.add_fact(s, "linked to", o, Provenance(0, store.take_arrival(), None, f"{s} {o}"))
    fact("Start", "Hub")
    for i in range(200):
        fact("Hub", f"Noise {i}")
    fact("Start", "Middle")
    fact("Middle", "Answer")
    assert "e:answer" in select_subgraph(store, ["e:start"], 12)


def test_sh_and_mh_share_one_context():
    task, golds = build_task("6k", ["sh", "mh"], 512, "Simple_rag_bm25", 2)
    assert [g.split for g in golds] == ["sh", "sh", "mh", "mh"] and len(task.chunks) == 12
    assert all("answers" not in q.__dict__ for q in task.questions)  # gold answers never reach a method


@pytest.mark.parametrize("config", ["bm25_fake_6k", "long_context_fake_6k", "long_context_128k_fake_6k",
                                    "graft_ppr_fake_6k", "graft_goat_fake_6k"])
def test_fake_run_end_to_end(config, tmp_path, monkeypatch):
    if "goat" in config and not (REPO / "results/checkpoints/gnn_default/model.pt").exists():
        pytest.skip("no GNN checkpoint at results/checkpoints/gnn_default")
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    from eval.run import run
    summary = json.loads((run(REPO / "configs" / "runs" / f"{config}.yaml") / "summary.json").read_text())
    assert summary["unanswered"] == 0 and summary["llm_mode"] == "fake"
    assert summary["n_questions"] == {"sh": 3, "mh": 3}
    usage = [json.loads(line) for line in open(next(tmp_path.glob("runs/*/repeat_0/usage.jsonl")))]
    assert {u["phase"] for u in usage} >= {"query"} and all(u["q_index"] is not None for u in usage if u["phase"] == "query")


def test_synthetic_training_data_has_no_benchmark_entities():
    from my_method.gnn.data_synthetic import synthetic_examples
    task, _ = build_task("6k", ["sh"], 512, "Simple_rag_bm25", None)
    world = synthetic_examples(seed=random.randint(0, 999), n_worlds=1, questions_per_world=5)[0]
    names = {world[0].store.fact(e)["name"] for e in world[0].store.entities()}
    context = " ".join(task.chunks)
    assert not any(f" {n} " in context for n in names)


def test_registry_configs_are_valid():
    from eval.methods import METHODS
    for path in (REPO / "configs" / "runs").glob("*.yaml"):
        assert yaml.safe_load(path.read_text())["method"] in METHODS, path


def test_nearest_nodes_is_breadth_first_and_capped():
    from my_method.gnn.features import nearest_nodes
    store = GraphStore()
    for i in range(30):
        store.add_fact("Hub", "linked to", f"Leaf {i}", Provenance(0, store.take_arrival(), None, f"hub {i}"))
    nodes = nearest_nodes(store, ["e:hub"], 10)
    assert nodes[0] == "e:hub" and len(nodes) == 10
    assert all(store.fact(n)["type"] == "Fact" for n in nodes[1:])  # hop 1 = the hub's facts


@pytest.mark.parametrize("mode,region", [("goat_ppr", "nearest"), ("goat_ppr", "full"), ("ppr_goat_ppr", "nearest")])
def test_experiment_b_and_c_modes_return_newest_facts(mode, region):
    """B and C run end to end with an untrained GCN, and the latest-version rule still applies."""
    from baselines.claude_gateway.embeddings import load_embedder
    from my_method.gnn.features import TextEmbedder, feature_dim
    from my_method.gnn.train import make_model
    from my_method.retrieval import RetrievalConfig, Retriever
    store = GraphStore()
    old = store.add_fact("Pee Wee King", "country of citizenship", "United States", Provenance(0, store.take_arrival(), 1, "1. a"))
    new = store.add_fact("Pee Wee King", "country of citizenship", "France", Provenance(1, store.take_arrival(), 2, "2. b"))
    store.supersede(new, old)
    store.add_fact("France", "official language", "Hebrew", Provenance(2, store.take_arrival(), 3, "3. c"))
    for i in range(20):
        store.add_fact(f"Person {i}", "country of citizenship", "France", Provenance(3, store.take_arrival(), 10 + i, f"x {i}"))
    texts = TextEmbedder(load_embedder("hash:16"))
    model = make_model(feature_dim(16), 8).eval()
    cfg = RetrievalConfig(mode=mode, region=region, max_nodes=12, max_facts=10)
    region_ = Retriever(store, cfg, texts, model).retrieve("What language does Pee Wee King's country speak?")
    assert region_.linked_entities == ["e:pee wee king"] and region_.facts
    assert old not in region_.facts  # superseded versions are swapped for the newest
    assert region_.subgraph_nodes == (store.g.number_of_nodes() if region == "full" else 12)


def test_extend_mode_starts_from_synthetic_graph_and_prompts_its_pattern():
    """Experiment D: the writer starts from the synthetic graph and the prompt lists its relations."""
    from my_method.gnn.data_synthetic import synthetic_start_graph
    from my_method.schema import Schema
    from my_method.writer import EXTRACT_FIXED, LLMWriter, graph_pattern
    seed = synthetic_start_graph()
    assert seed.stats()["facts"] > 100 and seed.stats()["supersedes_edges"] > 0
    pattern = graph_pattern(seed)
    assert "country of citizenship" in pattern or "official language" in pattern

    class Echo:  # records the system prompt instead of calling Claude
        def complete(self, system, user, max_tokens):
            self.system = system
            return type("R", (), {"text": '{"facts": []}'})()
    llm = Echo()
    LLMWriter(llm, Schema.load(), "fixed", True, pattern=pattern).extract("1. A is a citizen of B.")
    assert llm.system.startswith("SGAR-EXTRACT fixed") and "you only extend it" in llm.system
    assert "you only extend it" not in EXTRACT_FIXED.format(schema="s", pattern="")


def test_shared_graph_is_built_once_then_loaded(tmp_path):
    from baselines.common.protocol import Task
    from my_method.agent import GraftAgent
    cfg = {"model": "claude-haiku-5-5", "writer": "rule", "revisions": True, "embedding_model": "hash:16",
           "work_dir": str(tmp_path / "w"), "retrieval": "ppr", "max_facts": 5, "max_tokens": 5120,
           "include_outdated": False, "goat_targets": 3, "goat_topk": 12, "shared_graph": str(tmp_path / "g.json")}
    gw = type("G", (), {"anthropic_base_url": "http://unused"})()
    task = Task(sub_datasets=["factconsolidation_mh_6k"], chunk_size=512, chunks=["1. A is a citizen of B."], questions=[])
    first = GraftAgent(cfg, gw, task).memorize(task.chunks)
    second = GraftAgent(cfg, gw, task).memorize(["2. A is a citizen of C."])
    assert first["graph"]["facts"] == 1 and second["writer"] == {"reused_graph": str(tmp_path / "g.json")}


def _small_store():
    store = GraphStore()
    store.add_fact("Pee Wee King", "country of citizenship", "France", Provenance(0, store.take_arrival(), 1, "1. a"))
    store.add_fact("France", "official language", "Hebrew", Provenance(1, store.take_arrival(), 2, "2. b"))
    for i in range(20):
        store.add_fact(f"Person {i}", "country of citizenship", "France", Provenance(2, store.take_arrival(), 10 + i, f"x {i}"))
    return store


@pytest.mark.parametrize("explainer", ["goat", "eig"])
def test_embedding_linking_and_hybrid_on_mode_c(explainer):
    """link_embed_k keeps the exact matches first and adds k more entities; hybrid interleaves the mode's ranking
    with embedding search, without duplicates, and still returns only newest facts within the budget."""
    from baselines.claude_gateway.embeddings import load_embedder
    from my_method.gnn.features import TextEmbedder, feature_dim
    from my_method.gnn.train import make_model
    from my_method.retrieval import RetrievalConfig, Retriever
    store = _small_store()
    texts = TextEmbedder(load_embedder("hash:16"))
    model = make_model(feature_dim(16), 8).eval()
    q = "What language does Pee Wee King's country speak?"
    base = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=12, max_facts=10, explainer=explainer), texts, model)
    linked = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=12, max_facts=10, explainer=explainer,
                                              link_embed_k=3), texts, model)
    assert base.link(q) == ["e:pee wee king"]
    got = linked.link(q)
    assert got[0] == "e:pee wee king" and len(got) == 4 and len(set(got)) == 4
    both = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=12, max_facts=10, explainer=explainer,
                                            link_embed_k=3, hybrid=True), texts, model)
    region = both.retrieve(q)
    assert region.facts and len(region.facts) == len(set(region.facts)) <= 10
    ranked = ["f:a", "f:b", "f:c"]
    both._similar_facts = lambda question: ["f:b", "f:x", "f:y"]
    assert both._merge(q, ranked) == ["f:a", "f:b", "f:x", "f:c", "f:y"]  # one from each in turn


def test_hybrid_labels_sources_and_embed_mode_needs_no_gnn():
    from baselines.claude_gateway.embeddings import load_embedder
    from eval.attribution import classify
    from my_method.gnn.features import TextEmbedder, feature_dim
    from my_method.gnn.train import make_model
    from my_method.retrieval import RetrievalConfig, Retriever
    store = _small_store()
    texts = TextEmbedder(load_embedder("hash:16"))
    q = "What language does Pee Wee King's country speak?"
    model = make_model(feature_dim(16), 8).eval()
    hyb = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=12, max_facts=6, hybrid=True), texts, model).retrieve(q)
    assert len(hyb.sources) == len(hyb.facts) and set(hyb.sources) <= {"graph", "embed", "both"}
    emb = Retriever(store, RetrievalConfig(mode="embed", max_facts=5), texts, None).retrieve(q)
    assert len(emb.facts) == 5 and emb.sources == ["embed"] * 5
    row = {"answers": ["Hebrew"], "answer_in_retrieved": True, "fact_sources": ["graph", "embed"],
           "retrieved_text": "Memory 1:\nFrance official language Hebrew\n\nMemory 2:\nsomething else\n"}
    assert classify(row) == "only_graph"
    row["fact_sources"] = ["both", "embed"]
    assert classify(row) == "both"


def test_hybrid_k_keeps_graph_head_and_adds_k_new_embedding_facts():
    from baselines.claude_gateway.embeddings import load_embedder
    from my_method.gnn.features import TextEmbedder, feature_dim
    from my_method.gnn.train import make_model
    from my_method.retrieval import RetrievalConfig, Retriever
    store = _small_store()
    texts = TextEmbedder(load_embedder("hash:16"))
    model = make_model(feature_dim(16), 8).eval()
    r = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=12, max_facts=6, hybrid_k=2, explainer="eig"), texts, model)
    r._similar_facts = lambda q: ["f:a", "f:x", "f:y", "f:z"]
    merged = r._merge("q", ["f:a", "f:b", "f:c", "f:d", "f:e", "f:f"])
    assert merged[:4] == ["f:a", "f:b", "f:c", "f:d"] and merged[4:6] == ["f:x", "f:y"]  # f:a already in the head
    region = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=12, max_facts=6, hybrid_k=2, explainer="eig"),
                       texts, model).retrieve("What language does Pee Wee King's country speak?")
    assert len(region.facts) <= 6 and len(region.sources) == len(region.facts) and set(region.sources) <= {"graph", "embed"}


def test_question_graph_is_attached_used_and_removed():
    """query_graph: parsed edges become temporary nodes linked through matched entities; they seed PPR and enter the
    GNN subgraph, never appear among retrieved facts, and leave the graph unchanged afterwards."""
    from baselines.claude_gateway.embeddings import load_embedder
    from my_method.gnn.features import TextEmbedder, feature_dim
    from my_method.gnn.train import make_model
    from my_method.retrieval import RetrievalConfig, Retriever
    store = _small_store()
    nodes_before, edges_before = store.g.number_of_nodes(), store.g.number_of_edges()
    simple_before = store.simple_graph().number_of_nodes()
    texts = TextEmbedder(load_embedder("hash:16"))
    model = make_model(feature_dim(16), 8).eval()
    q = "What language does Pee Wee King's country speak?"
    r = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=12, max_facts=6, explainer="eig", query_graph=True),
                  texts, model)
    r.prepare_queries([q], lambda question: [("Pee Wee King", "country of citizenship", "?A"),
                                              ("?A", "official language", "?B")])
    region = r.retrieve(q)
    assert region.query_graph["matched"] == ["e:pee wee king"]
    assert region.facts and not any(f.startswith("qf:") for f in region.facts)
    assert store.g.number_of_nodes() == nodes_before and store.g.number_of_edges() == edges_before
    assert store.simple_graph().number_of_nodes() == simple_before
    assert not any(str(n).startswith(("q:", "qf:")) for n in store.g)


def test_question_graph_needs_no_embedding_after_prepare():
    """Workers are forked and cannot embed: after prepare_queries, retrieval must only read cached vectors."""
    from baselines.claude_gateway.embeddings import load_embedder
    from my_method.gnn.features import TextEmbedder, feature_dim
    from my_method.gnn.train import make_model
    from my_method.retrieval import RetrievalConfig, Retriever
    store = _small_store()
    texts = TextEmbedder(load_embedder("hash:16"))
    model = make_model(feature_dim(16), 8).eval()
    q = "What language does Pee Wee King's country speak?"
    texts.embed_texts([n if not n.startswith(("e:", "f:")) else __import__("my_method.gnn.features", fromlist=["node_text"]).node_text(store, n)
                       for n in store.g.nodes] + [q])  # what the agent embeds before forking
    r = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=12, max_facts=6, explainer="eig", query_graph=True),
                  texts, model)
    r.prepare_queries([q], lambda question: [("Pee Wee King", "Country Of Citizenship", "?A"),
                                              ("?A", "official language", "?B"), ("Unknown Person", "spouse", "?A")])

    class NoEmbed:
        dim = texts.dim
        def embed(self, batch):
            raise AssertionError(f"embedding after prepare: {batch}")
    texts.embedder = NoEmbed()
    region = r.retrieve(q)
    assert region.facts
