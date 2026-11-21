"""Bridge option (test 06 arm C): outside-base facts walk at a lower weight and are never returned."""
from baselines.claude_gateway.embeddings import HashEmbedder
from my_method.gnn.features import TextEmbedder, ppr_scores
from my_method.graph_store import GraphStore, Provenance
from my_method.retrieval import Region, RetrievalConfig, Retriever


def toy():
    s = GraphStore()
    doc = s.add_fact("Ann", "spouse", "Bob", Provenance(0, s.take_arrival(), 1, "Ann's spouse is Bob."))
    base = s.add_fact("Bob", "place of birth", "Paris", Provenance(-1, s.take_arrival(), None, "Bob was born in Paris."),
                      layer="base")
    return s, doc, base


def test_bridge_weights_only_base_edges():
    s, doc, base = toy()
    g = s.simple_graph()
    assert all("weight" not in g[u][v] for u, v in g.edges())  # off by default: unchanged
    s.bridge_weight, s._simple = 0.2, None
    g = s.simple_graph()
    for u, v in g.edges():
        assert g[u][v].get("weight", 1.0) == (0.2 if base in (u, v) else 1.0)
    assert ppr_scores(s, ["e:ann"] if "e:ann" in g else [next(iter(g))])  # weighted walk runs


def test_document_facts_only():
    s, doc, base = toy()
    r = Retriever(s, RetrievalConfig(mode="ppr", max_facts=10, document_facts_only=True), TextEmbedder(HashEmbedder()), None)
    assert r._finish([base, doc], Region([])).facts == [doc]
    r.cfg.document_facts_only = False
    assert r._finish([base, doc], Region([])).facts == [base, doc]
