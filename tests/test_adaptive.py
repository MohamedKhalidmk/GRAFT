"""Adaptive retrieval (G39 drop cutoff, G40 ask for more; docs/design/graft_adaptive_retrieval_design.md). Offline."""
from types import SimpleNamespace as NS

from baselines.claude_gateway.embeddings import load_embedder
from my_method.agent import ASK_RULE, GraftAgent, wants_more
from my_method.gnn.features import TextEmbedder, feature_dim
from my_method.gnn.train import make_model
from my_method.graph_store import GraphStore, Provenance
from my_method.retrieval import Region, RetrievalConfig, Retriever, drop_cut


def test_drop_cut_is_the_largest_ratio_drop_within_bounds():
    """Checks that drop_cut cuts at the largest score ratio drop between the lo and hi bounds, including zero-score, flat and short lists.
    Guards against: the answering model being shown a long tail of weak facts, or too few facts, because the cut misses the clear score gap."""
    s = [10, 9, 8, 1, 0.9, 0.8, 0.7, 0.6]
    assert drop_cut(s, 2, 6) == 3                       # 8 -> 1 is the largest drop
    assert drop_cut(list(reversed(s)), 2, 6) == 3       # order of the input does not matter
    assert drop_cut(s, 4, 6) == 5                       # the cut may not come before lo: largest drop after it, 0.9 -> 0.8
    assert drop_cut([5, 4, 3, 0, 0], 2, 5) == 3         # unreached facts (score 0): an infinite drop
    assert drop_cut([5, 4], 3, 10) == 2                 # fewer facts than lo: all of them
    assert drop_cut([1.0] * 30, 10, 20) == 10           # flat scores: no drop, the first candidate cut
    assert drop_cut([0, 0, 0, 0], 2, 4) == 2            # nothing scored: the minimum


def _store():
    store = GraphStore()
    store.add_fact("Pee Wee King", "country of citizenship", "France", Provenance(0, store.take_arrival(), 1, "1. a"))
    store.add_fact("France", "official language", "Hebrew", Provenance(1, store.take_arrival(), 2, "2. b"))
    for i in range(40):
        store.add_fact(f"Person {i}", "country of citizenship", "France", Provenance(2, store.take_arrival(), 10 + i, f"x {i}"))
    return store


def test_drop_cutoff_keeps_g35_order_and_only_changes_the_count():
    """Checks that the adaptive drop cutoff keeps the fixed-count retriever's fact ranking and only changes how many facts are shown, also on the fallback.
    Guards against: turning on the cutoff silently reordering the retrieved facts, so the comparison with the fixed-count run measures two changes at once."""
    store = _store()
    texts = TextEmbedder(load_embedder("hash:16"))
    model = make_model(feature_dim(16), 8).eval()
    q = "What language does Pee Wee King's country speak?"
    base = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=30, max_facts=30, max_tokens=40000), texts, model)
    full = base.retrieve(q)
    ad = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=30, max_facts=30, max_tokens=40000,
                                          adaptive="drop", min_facts=3, drop_max=20), texts, model).retrieve(q)
    assert ad.pool == full.facts                         # same ranking as the fixed-count retriever
    assert 3 <= ad.shown <= 20 and ad.facts == ad.pool[:ad.shown]
    assert set(ad.fact_scores) >= set(ad.facts)
    fb = Retriever(store, RetrievalConfig(mode="ppr_goat_ppr", max_nodes=30, max_facts=30, max_tokens=40000,
                                          adaptive="drop", min_facts=3, drop_max=20), texts, model).retrieve("zzz qqq")
    assert fb.fallback and fb.facts == fb.pool[:fb.shown] and all(f in fb.fact_scores for f in fb.facts)


def test_wants_more_only_on_the_ask_phrase():
    """Checks that wants_more fires only when the reply ends with the exact NEED MORE MEMORIES phrase.
    Guards against: a real answer that merely mentions needing more memories being thrown away and treated as a request for another batch."""
    assert wants_more("NEED MORE MEMORIES") and wants_more("Step 1: ...\nNEED MORE MEMORIES.")
    assert not wants_more("Answer: Hebrew") and not wants_more("") and not wants_more("I need more memories to be sure, but Hebrew")
    assert "NEED MORE MEMORIES" in ASK_RULE


def test_ask_loop_adds_batches_within_the_limits(monkeypatch):
    """Checks that each NEED MORE MEMORIES reply adds the next batch of pool facts, and that the ask limit and the end of the pool stop the loop.
    Guards against: a model that keeps asking for more memories looping past the ask limit or past the end of the retrieved pool."""
    import my_method.agent as ag
    replies = iter(["NEED MORE MEMORIES", "NEED MORE MEMORIES", "Answer: Hebrew"])
    shown = []

    def fake_answer(llm, store, region, query, sub, mt):
        shown.append(len(region.facts))
        assert ASK_RULE in query
        return NS(text=next(replies), stop_reason="end_turn"), "memory"
    monkeypatch.setattr(ag, "answer", fake_answer)
    agent = GraftAgent.__new__(GraftAgent)
    agent.config = {"ask_more": True, "ask_batch": 50, "ask_max": 3, "ask_cap": 200, "answer_max_tokens": 1024}
    agent.store, agent.llm, agent.sub_dataset = None, None, "x"
    pool = [f"f:{i}" for i in range(180)]
    region = Region(pool[:20], pool=pool, shown=20)
    call, _, log = agent._answer_asking(region, NS(query="q"))
    assert shown == [20, 70, 120] and call.text == "Answer: Hebrew" and log["asks"] == 2 and log["calls"] == 3
    # the cap and the pool end stop the asking
    replies = iter(["NEED MORE MEMORIES"] * 10)
    shown.clear()
    region = Region(pool[:150], pool=pool, shown=150)
    call, _, log = agent._answer_asking(region, NS(query="q"))
    assert shown == [150, 180] and log["asks"] == 1 and log["still_asking"]  # pool used up after one batch of 30


def test_user_node_links_first_person_questions():
    """Checks that with user_node on, first-person questions (I, my, me) also link the writer's user entity, and other questions link as before.
    Guards against: a chat question like 'What did I buy?' linking no entity, so the user's own facts are never reached."""
    store = GraphStore()
    store.add_fact("user", "bought", "a bike", Provenance(0, store.take_arrival(), None, "I bought a bike"))
    store.add_fact("Paris", "capital of", "France", Provenance(1, store.take_arrival(), None, "Paris is the capital"))
    texts = TextEmbedder(load_embedder("hash:16"))
    off = Retriever(store, RetrievalConfig(mode="ppr"), texts, None)
    on = Retriever(store, RetrievalConfig(mode="ppr", user_node=True), texts, None)
    assert off.link("What did I buy last week?") == []
    assert on.link("What did I buy last week?") == ["e:user"]
    assert on.link("Where is my bike from Paris?") == ["e:user", "e:paris"]
    assert on.link("What is the capital of France?") == ["e:france"]            # no first person: unchanged
    assert on.link("Tell me about Mimi") == ["e:user"]                          # "me" counts
    assert on.link("Timing of the immigration") == []                          # "i" only as a whole word
