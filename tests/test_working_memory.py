"""Working memory (my_method/working_memory.py) on a toy graph with a scripted LLM: steps chain through placeholders,
the work layer is linked while answering and removed afterwards, and prompt_only writes nothing to the graph."""
import json
from dataclasses import dataclass

from baselines.claude_gateway.embeddings import HashEmbedder
from my_method.gnn.features import TextEmbedder
from my_method.graph_store import GraphStore, Provenance
from my_method.retrieval import RetrievalConfig, Retriever
from my_method.working_memory import WorkingMemory


@dataclass
class Call:
    text: str
    stop_reason: str = "end_turn"


class ScriptedLLM:
    def __init__(self):
        self.prompts = []

    def complete(self, system, user, max_tokens):
        self.prompts.append((system, user))
        if system.startswith("GRAFT-STEP"):
            if "Find Ann | spouse" in user:
                return Call(json.dumps({"result": "Bob", "facts": ["1"], "note": "fact 1 names Ann's spouse"}))
            return Call(json.dumps({"result": "Paris", "facts": ["2"], "note": "fact 2 gives Bob's birthplace"}))
        return Call("Answer: Paris")


def graph():
    g = GraphStore()
    g.add_fact("Ann", "spouse", "Bob", Provenance(0, g.take_arrival(), 1, "Ann is married to Bob"))
    g.add_fact("Bob", "place of birth", "Paris", Provenance(0, g.take_arrival(), 2, "Bob was born in Paris"))
    g.add_fact("Carl", "place of birth", "Rome", Provenance(0, g.take_arrival(), 3, "Carl was born in Rome"))
    return g


def run(mode):
    g = graph()
    r = Retriever(g, RetrievalConfig(mode="ppr", max_facts=10), TextEmbedder(HashEmbedder(64)))
    before = (g.g.number_of_nodes(), g.g.number_of_edges())
    llm = ScriptedLLM()
    edges = [("Ann", "spouse", "?A"), ("?A", "place of birth", "?B")]
    text, meta = WorkingMemory(g, r, llm, mode).run("Where was Ann's spouse born?", "Q: Where was Ann's spouse born?",
                                                    edges, "factconsolidation_mh_262k", 64)
    assert (g.g.number_of_nodes(), g.g.number_of_edges()) == before  # work layer removed
    return text, meta, llm


def test_graph_mode_chains_steps_and_links_work_layer():
    """Checks that graph-mode working memory fills each step's placeholder from the previous result, links a work layer, and removes it afterwards.
    Guards against: the second step asking about ?A instead of Bob, or work-layer nodes left behind in the shared graph."""
    text, meta, llm = run("graph")
    rec = meta["working_memory"]
    assert [s["result"] for s in rec["steps"]] == ["Bob", "Paris"]
    assert rec["steps"][1]["text"] == "Bob | place of birth | ?B"  # the placeholder was filled by step 1
    assert rec["steps"][1]["about"] == "e:bob"  # step 2 is about the entity step 1's result links to
    kinds = {k for _, k, _ in rec["work_edges"]}
    assert {"has_step", "next", "about", "answer", "note", "used_fact", "same_as"} <= kinds
    assert rec["calls"] == 3 and text == "Answer: Paris"
    assert "Step 1: Ann | spouse | ?A -> Bob" in llm.prompts[1][1]  # step 2 reads the chain back


def test_prompt_only_writes_nothing():
    """Checks that prompt_only working memory still chains the steps but adds no work nodes or edges to the graph.
    Guards against: the prompt-only arm writing work nodes into the graph, so it no longer differs from graph mode."""
    _, meta, _ = run("prompt_only")
    rec = meta["working_memory"]
    assert rec["work_nodes"] == [] and rec["work_edges"] == []
    assert [s["result"] for s in rec["steps"]] == ["Bob", "Paris"]


def test_guide_plan_is_cited_from_the_start():
    """Checks that with the guide and working memory together (test 06), the guide's planned facts reach every step prompt and the final facts.
    Guards against: the guide's planned chain being dropped when working memory runs, so the steps and the final answer never see it."""
    g = graph()
    r = Retriever(g, RetrievalConfig(mode="ppr", max_facts=10), TextEmbedder(HashEmbedder(64)))
    carl = [f for f in g.facts() if g.fact(f)["subject"] == "Carl"][0]  # a fact no step would cite
    q = "Where was Ann's spouse born?"
    r.plans = {q: ([carl], {"start": "Carl", "steps": [{"how": "direct"}]})}
    llm = ScriptedLLM()
    text, meta = WorkingMemory(g, r, llm, "graph").run(q, "Q: " + q, [("Ann", "spouse", "?A"), ("?A", "place of birth", "?B")],
                                                       "factconsolidation_mh_262k", 64)
    rec = meta["working_memory"]
    assert carl in rec["final_facts"] and rec["plan"]["facts"] == [carl]
    assert all("Carl was born in Rome" in p for s, p in llm.prompts[:2])  # both steps see the planned fact
