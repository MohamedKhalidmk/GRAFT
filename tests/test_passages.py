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


def test_passage_index_matches_the_per_question_functions():
    """Checks that the cached PassageIndex (built once per history) chooses the same passages as the per-question functions for all three arms.
    Guards against: the FactConsolidation runs (one index, 100 questions) showing different passages than the tested functions would."""
    from my_method.passages import PassageIndex
    st, F = toy_store()
    ps = split_passages(CHUNKS)
    cfg = PassageConfig(budget_tokens=80)
    idx = PassageIndex(st, CHUNKS, cfg, embed=fake_embed)
    pids = lambda r: [p.pid for p in r.passages]
    assert pids(idx.guided([F["tor"], F["lyon"]], set())) == pids(guided_passages(st, ps, [F["tor"], F["lyon"]], set(), cfg))
    q = "Where did the user move to?"
    assert pids(idx.hipporag(q)) == pids(hipporag_passages(st, ps, q, fake_embed, cfg))
    assert pids(idx.bm25(q)) == pids(bm25_passages(st, ps, q, cfg))


def test_agent_answers_from_passages_on_factconsolidation_chunks(tmp_path):
    """Checks GRAFT's agent with a passages config on FactConsolidation-style chunks (numbered fact lines): each arm puts its passage block (not fact lines) in the benchmark prompt within the budget, the guided arm uses the guided region and the HippoRAG and BM25 arms never run GRAFT's retrieval, and the log carries passages shown, tokens and link counts.
    Guards against: a passage arm that silently answers from G35's fact lines, a baseline that secretly uses the guide, or a run with nothing to report."""
    from types import SimpleNamespace as NS
    from baselines.common.protocol import Task
    from my_method.agent import GraftAgent
    chunks = ["1. Anna Berg is a citizen of Norway.\n2. Norway has the capital Oslo.",
              "3. Anna Berg is a citizen of Chile.\n4. Chile has the capital Santiago.\n5. Bo Lund plays chess."]
    gw = type("G", (), {"anthropic_base_url": "http://unused"})()
    task = Task(sub_datasets=["factconsolidation_mh_6k"], chunk_size=512, chunks=chunks, questions=[])
    for arm in ("guided", "hipporag", "bm25"):
        cfg = {"model": "claude-haiku-5-5", "writer": "rule", "revisions": True, "embedding_model": "hash:16",
               "work_dir": str(tmp_path / arm), "retrieval": "ppr", "max_facts": 5, "max_tokens": 5120,
               "include_outdated": False, "goat_targets": 3, "goat_topk": 12, "answer_max_tokens": 64,
               "passages": {"arm": arm, "budget_tokens": 30, "header": "PASSAGES (source text, most relevant first):"}}
        agent = GraftAgent(cfg, gw, task)
        agent.memorize(chunks)
        prompts = []
        agent.llm = NS(complete=lambda system, user, mt: (prompts.append(user), NS(text="Answer: Santiago", stop_reason="end_turn"))[1])
        if arm != "guided":
            agent._region = lambda q: (_ for _ in ()).throw(AssertionError("baseline ran GRAFT retrieval"))
        text, meta = agent.answer(NS(q_index=0, query="What is the capital of the country Anna Berg is a citizen of?"))
        assert text == "Answer: Santiago" and meta["passage_arm"] == arm
        assert prompts[0].startswith("PASSAGES (source text") and "Memory 1:" not in prompts[0]
        assert meta["retrieved_text"] in prompts[0] and 0 < meta["passages_shown"] and meta["passage_tokens"] <= 30
        assert sum(meta["passage_links"].values()) == agent.store.stats()["facts"]
        assert ("facts_ranked" in meta) == (arm == "guided")


def test_parse_open_takes_only_replies_that_end_in_open_lines():
    """Checks that an OPEN request is read only when the reply ends with OPEN lines (bold or backticks allowed, a copied explanation after the scope allowed), duplicates dropped, at most 3; an answer that merely mentions opening is not a request.
    Guards against: G53 treating a real answer as a request for more text, or missing a request Qwen formatted in markdown."""
    from my_method.passages import parse_open
    assert parse_open("OPEN P3 AROUND") == [(3, "AROUND")]
    assert parse_open("Need more.\n**OPEN P1 session**\n`OPEN P4 AROUND (the text just before)`") == [(1, "SESSION"), (4, "AROUND")]
    assert parse_open("OPEN P1 AROUND\nOPEN P1 AROUND\nOPEN P2 AROUND\nOPEN P3 AROUND\nOPEN P5 SESSION") == [(1, "AROUND"), (2, "AROUND"), (3, "AROUND")]
    assert parse_open("I could OPEN P3 AROUND but the answer is Oslo.") == [] and parse_open("") == []


def test_open_more_adds_neighbours_or_the_rest_of_the_chunk_within_its_cap():
    """Checks that AROUND adds the passages just before and after the named shown passage in its chunk, SESSION the rest of the chunk in order, already shown passages are skipped, the added text stays within open_tokens, and an unknown passage number adds nothing.
    Guards against: an OPEN request pulling text from another session, repeating what Qwen already has, or growing past its token cap."""
    from my_method.passages import PassageIndex, open_more
    st, F = toy_store()
    idx = PassageIndex(st, CHUNKS, PassageConfig(passage_tokens=64, open_tokens=10_000), embed=fake_embed)
    chunk0 = [p for p in idx.passages if p.chunk_id == 0]
    mid = chunk0[2]
    around = open_more(idx, [mid], 1, "AROUND")
    assert [p.pid for p in around] == [chunk0[1].pid, chunk0[3].pid]
    session = open_more(idx, [mid, chunk0[0]], 1, "SESSION")
    assert [p.pid for p in session] == [p.pid for p in chunk0 if p.pid not in (mid.pid, chunk0[0].pid)]
    idx.cfg.open_tokens = chunk0[1].tokens()
    assert sum(p.tokens() for p in open_more(idx, [mid], 1, "SESSION")) <= idx.cfg.open_tokens
    assert open_more(idx, [mid], 5, "AROUND") == []


def test_reading_arm_opens_text_counts_tokens_and_stops_after_three_asks(tmp_path):
    """Checks GRAFT's G53 loop with scripted replies: each OPEN reply adds passages to what Qwen sees next and its tokens are logged, the reading rule is shown only while asks remain, after 3 asks the last call gets the plain question, and the final answer's context includes the opened text.
    Guards against: unbounded asking, asked text that never reaches Qwen, or opened tokens left out of the tokens shown."""
    from types import SimpleNamespace as NS
    from baselines.common.protocol import Task
    from my_method.agent import GraftAgent
    chunks = ["1. Anna Berg is a citizen of Norway. 2. Norway has the capital Oslo. 3. Bo Lund plays chess. "
              "4. Bo Lund was born in Rome. 5. Rome is in Italy. 6. Cy Dahl speaks Danish. 7. Cy Dahl lives in Lund.",
              "8. Anna Berg is a citizen of Chile. 9. Chile has the capital Santiago. 10. Ed Ek writes poems."]
    gw = type("G", (), {"anthropic_base_url": "http://unused"})()
    task = Task(sub_datasets=["factconsolidation_mh_6k"], chunk_size=512, chunks=chunks, questions=[])
    cfg = {"model": "claude-haiku-5-5", "writer": "rule", "revisions": True, "embedding_model": "hash:16",
           "work_dir": str(tmp_path / "w"), "retrieval": "ppr", "max_facts": 2, "max_tokens": 5120,
           "include_outdated": False, "goat_targets": 3, "goat_topk": 12, "answer_max_tokens": 64,
           "passages": {"arm": "guided", "budget_tokens": 12, "passage_tokens": 12, "open_tokens": 40,
                        "reading": True, "max_asks": 3}}
    agent = GraftAgent(cfg, gw, task)
    agent.memorize(chunks)
    replies = iter(["OPEN P1 AROUND", "**OPEN P1 SESSION**", "OPEN P2 AROUND", "OPEN P1 SESSION", "never reached"])
    seen = []
    agent.llm = NS(complete=lambda system, user, mt: (seen.append(user), NS(text=next(replies), stop_reason="end_turn"))[1])
    text, meta = agent.answer(NS(q_index=0, query="What is the capital of the country Anna Berg is a citizen of?"))
    r = meta["reading"]
    assert r["calls"] == 4 and r["asks"] == 3 and text == "OPEN P1 SESSION" and r["still_asking"]
    assert all("OPEN P<number> AROUND" in u for u in seen[:3]) and "OPEN P<number>" not in seen[3]
    assert len(seen[1]) > len(seen[0]) and r["log"][0]["passages_added"] > 0
    assert r["tokens_added"] == sum(a["tokens_added"] for a in r["log"]) and all(a["tokens_added"] <= 3 * 40 for a in r["log"])
    assert meta["retrieved_text"] in seen[3] and meta["tokens_shown"] >= meta["passage_tokens"]
