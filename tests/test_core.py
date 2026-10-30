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
                                    "sgar_ppr_fake_6k", "sgar_goat_fake_6k"])
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
