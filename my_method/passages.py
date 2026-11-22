# Sources: hipporag, bm25, original (docs/reference/REFERENCES.md)
"""Passage index on top of the guided graph (design: docs/design/graft_passage_index_design.md; G49, G50, G51).

Passages are turn-sized pieces of the history's chunks (each chunk is one session, as Flotilla's Memory route builds
them). Every fact keeps its chunk_id and source sentence (provenance span); the passage index maps each fact to the
passage inside its chunk that holds that sentence. Three ways to choose passages, all cut to the same token budget:

  guided    (G49, ours) the guided ranking of facts (the guide plan, GNN + GOAt) is kept; each fact brings its passage,
            in fact order, duplicates dropped; a passage holding a superseded fact is marked outdated; a short summary
            of the facts behind the passages (with dates and outdated marks) follows
  hipporag  (G50) HippoRAG 2's passage nodes on GRAFT's graph: passage nodes linked to the entities of their facts,
            Personalized PageRank (damping 0.5) seeded by the question's best-matching facts (their entities) and by
            dense passage similarity at a small weight; no guide, no GNN
  bm25      (G51) BM25 on the question over the same passages

Borrowed from HippoRAG 2 (Gutierrez et al., arXiv 2502.14802): passages as graph nodes linked to their phrases, PPR
over the combined graph with query-to-triple seeds and a dense passage weight, damping 0.5, passages to the reader.
Ours: the guide and its planned walk, supersede and the outdated marks, time (session dates), the fact-to-passage
link through the source sentence, and passages ordered by the guided ranking.
"""
import math
import re
from dataclasses import dataclass, field

import networkx as nx
import numpy as np

TOKEN_CHARS = 4   # approximate characters per token, as GRAFT's other budgets
HEADER = re.compile(r"^\[Chat session (?P<sid>[^,\]]+), date (?P<date>[^,\]]+)(?:, part \d+ of \d+)?\]\s*$")
SENT = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"\w+")


@dataclass
class PassageConfig:
    arm: str = "guided"            # guided (G49) | hipporag (G50) | bm25 (G51)
    budget_tokens: int = 4096      # the same for every passage arm
    passage_tokens: int = 256      # the largest passage; longer turns are split at sentence ends
    summary_facts: int = 30        # guided only: facts behind the shown passages, listed after them
    hippo_top_facts: int = 5       # hipporag: the question's best-matching facts seed their entities
    hippo_passage_weight: float = 0.05   # hipporag: weight of dense passage similarity in the seeds
    damping: float = 0.5           # hipporag: PageRank damping (HippoRAG 2)


@dataclass
class Passage:
    pid: str
    chunk_id: int
    session: str
    date: str
    text: str

    def tokens(self) -> int:
        return math.ceil(len(self.text) / TOKEN_CHARS)


@dataclass
class PassageResult:
    passages: list[Passage]
    outdated_notes: dict[str, list[str]] = field(default_factory=dict)   # pid -> outdated facts it holds
    summary: list[str] = field(default_factory=list)                     # guided only: fact ids
    link: dict[str, str] = field(default_factory=dict)                   # fact id -> exact | approximate | none

    def tokens(self) -> int:
        return sum(p.tokens() for p in self.passages)


def _split_long(line: str, limit_chars: int) -> list[str]:
    """One turn longer than the passage size: cut at sentence ends (a single over-long sentence at the limit)."""
    out, cur = [], ""
    for s in SENT.split(line):
        while len(s) > limit_chars:
            if cur:
                out.append(cur)
                cur = ""
            out.append(s[:limit_chars])
            s = s[limit_chars:]
        if cur and len(cur) + 1 + len(s) > limit_chars:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def split_passages(chunks: list[str], passage_tokens: int = 256) -> list[Passage]:
    """Turn-sized passages of every chunk: one turn line each ("user: ..." / "assistant: ..."), long turns cut at
    sentence ends. Each passage keeps its chunk, session and date (from the chunk's header line)."""
    limit = passage_tokens * TOKEN_CHARS
    out = []
    for c, chunk in enumerate(chunks):
        lines = chunk.splitlines()
        m = HEADER.match(lines[0]) if lines else None
        sid, date = (m.group("sid"), m.group("date")) if m else (f"chunk {c}", "unknown date")
        body = lines[1:] if m else lines
        k = 0
        for line in body:
            if not line.strip():
                continue
            for piece in _split_long(line.strip(), limit):
                out.append(Passage(f"p:{c}:{k}", c, sid, date, piece))
                k += 1
    return out


def _words(text: str) -> set[str]:
    return {w.lower() for w in WORD.findall(text or "")}


def link_facts(store, passages: list[Passage]) -> tuple[dict[str, str], dict[str, str]]:
    """Each fact's passage: the passage of its chunk that contains its source sentence (exact), else the one with the
    largest word overlap with it (approximate); none when the chunk has no passages. Returns ({fact: pid},
    {fact: exact | approximate | none})."""
    by_chunk: dict[int, list[Passage]] = {}
    for p in passages:
        by_chunk.setdefault(p.chunk_id, []).append(p)
    where, how = {}, {}
    for f in store.facts():
        prov = store.fact(f).get("provenance") or {}
        cands = by_chunk.get(prov.get("chunk_id"), [])
        span = (prov.get("span") or "").strip()
        if not cands:
            how[f] = "none"
            continue
        hit = next((p for p in cands if span and span in p.text), None)
        if hit is not None:
            where[f], how[f] = hit.pid, "exact"
            continue
        sw = _words(span)
        best = max(cands, key=lambda p: len(sw & _words(p.text)))
        if sw & _words(best.text):
            where[f], how[f] = best.pid, "approximate"
        else:
            how[f] = "none"
    return where, how


def _fill(order: list[str], by_id: dict[str, Passage], budget: int) -> list[Passage]:
    """Passages in order, duplicates dropped, until the next one would pass the budget (a passage too large alone is
    skipped, the next smaller one may still fit)."""
    out, used, seen = [], 0, set()
    for pid in order:
        if pid in seen or pid not in by_id:
            continue
        seen.add(pid)
        t = by_id[pid].tokens()
        if used + t <= budget:
            out.append(by_id[pid])
            used += t
    return out


def guided_passages(store, passages: list[Passage], ranked_facts: list[str], outdated: set[str],
                    cfg: PassageConfig) -> PassageResult:
    """G49: the guided ranking's facts bring their passages in order; outdated facts mark their passage."""
    where, how = link_facts(store, passages)
    by_id = {p.pid: p for p in passages}
    chosen = _fill([where[f] for f in ranked_facts if f in where], by_id, cfg.budget_tokens)
    shown = {p.pid for p in chosen}
    notes: dict[str, list[str]] = {}
    for f in ranked_facts:
        if where.get(f) in shown and (f in outdated or store.is_superseded(f)):
            notes.setdefault(where[f], []).append(f)
    summary = [f for f in ranked_facts if where.get(f) in shown][:cfg.summary_facts]
    return PassageResult(chosen, notes, summary, how)


def _outdated_notes(store, where: dict[str, str], chosen: list[Passage]) -> dict[str, list[str]]:
    shown = {p.pid for p in chosen}
    notes: dict[str, list[str]] = {}
    for f, pid in where.items():
        if pid in shown and store.is_superseded(f):
            notes.setdefault(pid, []).append(f)
    return notes


def hipporag_passages(store, passages: list[Passage], question: str, embed, cfg: PassageConfig) -> PassageResult:
    """G50: HippoRAG 2-style passage retrieval on GRAFT's graph, no guide and no GNN. embed(list[str]) -> unit-norm
    vectors (GRAFT's TextEmbedder.embed_texts in runs, a fake in tests)."""
    where, how = link_facts(store, passages)
    facts = [f for f in store.facts() if not store.is_superseded(f)]
    g = nx.Graph()
    for f in store.facts():
        d = store.fact(f)
        s, o = f"e:{d['subject'].lower()}", f"e:{d['object'].lower()}"
        g.add_edge(s, o, weight=g.get_edge_data(s, o, {}).get("weight", 0) + 1.0)
        if f in where:
            for e in (s, o):
                g.add_edge(where[f], e, weight=1.0)
    for p in passages:
        g.add_node(p.pid)
    q = np.asarray(embed([question]))[0]
    seeds: dict[str, float] = {}
    if facts:
        ftexts = [" ".join((store.fact(f)["subject"], store.fact(f)["relation"], store.fact(f)["object"])) for f in facts]
        sims = np.asarray(embed(ftexts)) @ q
        for i in np.argsort(-sims)[:cfg.hippo_top_facts]:
            d = store.fact(facts[i])
            for e in (f"e:{d['subject'].lower()}", f"e:{d['object'].lower()}"):
                seeds[e] = seeds.get(e, 0.0) + max(float(sims[i]), 0.0)
    if passages:
        psims = np.asarray(embed([p.text for p in passages])) @ q
        top = max(float(psims.max()), 1e-9)
        for p, s in zip(passages, psims):
            if s > 0:
                seeds[p.pid] = seeds.get(p.pid, 0.0) + cfg.hippo_passage_weight * float(s) / top
    seeds = {k: v for k, v in seeds.items() if k in g and v > 0}
    if not seeds:
        return PassageResult([], {}, [], how)
    pr = nx.pagerank(g, alpha=cfg.damping, personalization=seeds, weight="weight")
    order = sorted((p.pid for p in passages), key=lambda pid: -pr.get(pid, 0.0))
    chosen = _fill(order, {p.pid: p for p in passages}, cfg.budget_tokens)
    return PassageResult(chosen, _outdated_notes(store, where, chosen), [], how)


def bm25_passages(store, passages: list[Passage], question: str, cfg: PassageConfig) -> PassageResult:
    """G51: BM25 (rank_bm25's Okapi BM25) on the question over the same passages; no graph, no marks."""
    from rank_bm25 import BM25Okapi
    if not passages:
        return PassageResult([], {}, [], {})
    tok = lambda t: [w.lower() for w in WORD.findall(t)]
    bm = BM25Okapi([tok(p.text) for p in passages])
    scores = bm.get_scores(tok(question))
    order = [passages[i].pid for i in np.argsort(-scores) if scores[i] > 0]
    chosen = _fill(order, {p.pid: p for p in passages}, cfg.budget_tokens)
    return PassageResult(chosen, {}, [], {})


def render(store, res: PassageResult) -> str:
    """The memory block Qwen reads: dated passages (with outdated notes), then the guided arm's fact summary."""
    lines = ["PASSAGES (from your earlier chat sessions with this user, most relevant first):"]
    for i, p in enumerate(res.passages, 1):
        note = ""
        if p.pid in res.outdated_notes:
            olds = "; ".join(" ".join((store.fact(f)["subject"], store.fact(f)["relation"], store.fact(f)["object"]))
                             for f in res.outdated_notes[p.pid])
            note = f" | OUTDATED: contains a fact later updated ({olds})"
        lines.append(f"[P{i}] {p.date} | session {p.session}{note}\n{p.text}")
    if not res.passages:
        lines.append("(no passages were recalled)")
    if res.summary:
        lines.append("FACTS FOUND (summary):")
        for f in res.summary:
            d = store.fact(f)
            mark = " | OUTDATED" if store.is_superseded(f) else ""
            lines.append(f"- {d['subject']} | {d['relation']} | {d['object']}{mark}")
    return "\n".join(lines) + "\nEND OF MEMORY"


def passage_retrieval(store, chunks: list[str], ranked_facts: list[str], outdated: set[str], question: str,
                      settings: dict, embed=None) -> dict:
    """One question's passage arm, as Flotilla's GRAFT bridge calls it: settings is the preset's "passages" dict
    (arm, budget_tokens, passage_tokens, summary_facts, ...). Returns the block Qwen reads and what to log."""
    cfg = PassageConfig(**{k: v for k, v in settings.items() if k in PassageConfig.__dataclass_fields__})
    ps = split_passages(chunks, cfg.passage_tokens)
    if cfg.arm == "guided":
        res = guided_passages(store, ps, ranked_facts, outdated, cfg)
    elif cfg.arm == "hipporag":
        if embed is None:
            raise ValueError("the hipporag passage arm needs an embedder")
        res = hipporag_passages(store, ps, question, embed, cfg)
    elif cfg.arm == "bm25":
        res = bm25_passages(store, ps, question, cfg)
    else:
        raise ValueError(f"unknown passage arm {cfg.arm!r}")
    links = {}
    for how in (res.link or link_facts(store, ps)[1]).values():
        links[how] = links.get(how, 0) + 1
    return {"passage_block": render(store, res), "passage_arm": cfg.arm, "passage_budget": cfg.budget_tokens,
            "passages": [{"pid": p.pid, "session": p.session, "date": p.date, "tokens": p.tokens(),
                          "outdated": p.pid in res.outdated_notes} for p in res.passages],
            "passage_tokens": res.tokens(), "passage_summary": res.summary, "passage_links": links,
            "passages_total": len(ps)}
