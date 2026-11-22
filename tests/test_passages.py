import zlib

import numpy as np

from my_method.graph_store import GraphStore, Provenance
from my_method.passages import (PassageConfig, bm25_passages, guided_passages, hipporag_passages, link_facts, render,
                                split_passages)

CHUNKS = [
    "[Chat session s1, date 2023/05/01 (Mon) 09:00]\n"
    "user: I live in Lyon, France and work as a nurse.\n"
    "assistant: " + "Lyon is a lovely city with great food. " * 60 + "\n"
    "user: I have read 10 books this year.",
    "[Chat session s2, date 2023/06/01 (Thu) 10:00]\n"
    "user: Big news, I moved to Toronto last week!\n"
    "user: I have now read 50 books this year.",
]


def toy_store():
    st = GraphStore()
    lyon = st.add_fact("user", "lives in", "Lyon", Provenance(0, st.take_arrival(), None, "I live in Lyon, France"))
    job = st.add_fact("user", "works as", "nurse", Provenance(0, st.take_arrival(), None, "work as a nurse"))
    b10 = st.add_fact("user", "books read", "10", Provenance(0, st.take_arrival(), None, "read ten books this year so far"))
    tor = st.add_fact("user", "moved to", "Toronto", Provenance(1, st.take_arrival(), None, "I moved to Toronto last week!"))
    b50 = st.add_fact("user", "books read", "50", Provenance(1, st.take_arrival(), None, "I have now read 50 books this year."))
    lost = st.add_fact("user", "likes", "jazz", Provenance(7, st.take_arrival(), None, "I like jazz"))
    st.supersede(tor, lyon)
    st.supersede(b50, b10)
    return st, dict(lyon=lyon, job=job, b10=b10, tor=tor, b50=b50, lost=lost)


def fake_embed(texts):
    """Bag of words hashed into 64 dimensions, unit norm: enough to make related texts close."""
    out = []
    for t in texts:
        v = np.zeros(64)
        for w in t.lower().split():
            v[zlib.crc32(w.strip(".,!?").encode()) % 64] += 1
        out.append(v / (np.linalg.norm(v) or 1))
    return np.stack(out)


def test_passages_are_turns_with_session_and_date_and_long_turns_split():
    """Checks that each turn becomes a passage carrying its chunk, session and date, and that a turn longer than the passage size is cut at sentence ends under the limit.
    Guards against: whole sessions shown as one passage, or passages without the date that time tracking needs."""
    ps = split_passages(CHUNKS, passage_tokens=64)
    first = ps[0]
    assert (first.chunk_id, first.session, first.date) == (0, "s1", "2023/05/01 (Mon) 09:00")
    assert first.text.startswith("user: I live in Lyon")
    long = [p for p in ps if p.chunk_id == 0 and "lovely city" in p.text]
    assert len(long) > 1 and all(p.tokens() <= 64 for p in long)
    assert {p.session for p in ps} == {"s1", "s2"}


def test_facts_link_to_their_passage_exactly_approximately_or_not_at_all():
    """Checks that a fact whose source sentence is in a passage of its chunk links exactly, a reworded one links to the best-overlapping passage of its chunk (approximate), and one whose chunk does not exist links to none.
    Guards against: facts pointing at passages of another session, or a silently missing link counted as found."""
    st, F = toy_store()
    where, how = link_facts(st, split_passages(CHUNKS))
    assert how[F["lyon"]] == "exact" and how[F["tor"]] == "exact"
    assert how[F["b10"]] == "approximate" and where[F["b10"]].startswith("p:0:")
    assert how[F["lost"]] == "none" and F["lost"] not in where


def test_guided_arm_follows_the_fact_ranking_marks_outdated_and_keeps_the_budget():
    """Checks that the guided arm takes passages in the order of the ranked facts without duplicates, stays within the token budget, marks the passage of a superseded fact outdated, and lists the facts behind the shown passages.
    Guards against: passages that ignore the guide's ranking, an outdated Lyon passage shown as current, or a budget overrun."""
    st, F = toy_store()
    ps = split_passages(CHUNKS)
    cfg = PassageConfig(budget_tokens=60)
    res = guided_passages(st, ps, [F["tor"], F["lyon"], F["job"], F["b50"]], set(), cfg)
    assert res.passages[0].text.startswith("user: Big news") and res.tokens() <= 60
    assert len({p.pid for p in res.passages}) == len(res.passages)
    lyon_pid = next(p.pid for p in res.passages if "Lyon" in p.text)
    assert F["lyon"] in res.outdated_notes[lyon_pid]
    assert F["tor"] in res.summary and F["job"] in res.summary
    block = render(st, res)
    assert "OUTDATED: contains a fact later updated (user lives in Lyon)" in block and "FACTS FOUND" in block
    assert "2023/06/01" in block


def test_hipporag_arm_ranks_passages_by_ppr_from_question_seeds():
    """Checks that the HippoRAG 2-style arm (no guide) reaches the passage of the question's best-matching fact through PageRank, keeps the budget, and carries the outdated mark from the graph.
    Guards against: a passage arm that ignores the graph, or one that differs from the guided arm in anything but the ranking."""
    st, F = toy_store()
    ps = split_passages(CHUNKS)
    res = hipporag_passages(st, ps, "Where did the user move to?", fake_embed, PassageConfig(budget_tokens=60))
    assert res.passages and res.tokens() <= 60
    assert any("Toronto" in p.text for p in res.passages)
    res = hipporag_passages(st, ps, "Where does the user live in Lyon?", fake_embed, PassageConfig(budget_tokens=400))
    lyon = [p.pid for p in res.passages if "Lyon, France" in p.text]
    assert lyon and F["lyon"] in res.outdated_notes.get(lyon[0], [])


def test_bm25_arm_and_equal_budgets():
    """Checks that the BM25 arm puts the lexically matching passage first with no graph marks, and that all three arms stay within one shared passage budget.
    Guards against: an arm compared on a larger budget than the others."""
    st, F = toy_store()
    ps = split_passages(CHUNKS)
    cfg = PassageConfig(budget_tokens=50)
    b = bm25_passages(st, ps, "How many books have I read this year?", cfg)
    assert "books" in b.passages[0].text and not b.outdated_notes
    g = guided_passages(st, ps, [F["b50"], F["tor"], F["lyon"]], set(), cfg)
    h = hipporag_passages(st, ps, "books read this year", fake_embed, cfg)
    assert max(b.tokens(), g.tokens(), h.tokens()) <= 50


def test_passage_retrieval_entry_point_for_the_bridge():
    """Checks the bridge's entry point: each arm returns a rendered block, its passages with dates and tokens, the total within the budget, and the fact-to-passage link counts; an unknown arm is an error.
    Guards against: the Memory route receiving a block from a different arm than its preset names, or no link statistics to report."""
    import pytest
    from my_method.passages import passage_retrieval
    st, F = toy_store()
    for arm in ("guided", "hipporag", "bm25"):
        out = passage_retrieval(st, CHUNKS, [F["tor"], F["lyon"]], set(), "Where does the user live?",
                                {"arm": arm, "budget_tokens": 80}, embed=fake_embed)
        assert out["passage_arm"] == arm and out["passage_tokens"] <= 80 and out["passage_block"].endswith("END OF MEMORY")
        assert out["passage_links"]["exact"] >= 2 and out["passages_total"] > 3
    with pytest.raises(ValueError):
        passage_retrieval(st, CHUNKS, [], set(), "q", {"arm": "dense"})
