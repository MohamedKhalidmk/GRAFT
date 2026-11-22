"""GRAFT read phase: find the region of the memory graph that answers a question.

1. Link the question to graph entities (exact name match on normalised words; longest names win).
2. For the GNN modes, let PPR pick the most relevant nodes in the whole graph (as many as the GNN
   was trained with).
3. Rank facts, by retrieval mode:
     gnn_goat  trained GNN scores nodes; GOAt attributes the top-scored nodes' predictions to edges;
               the facts on the most important edges are the region (the method as designed)
     gnn_topk  trained GNN scores nodes; the highest-scored facts are the region (ablation)
     ppr       Personalized PageRank over the whole graph, no GNN and no depth limit (ablation,
               as HippoRAG does it)
     goat_ppr  experiment B: region WITHOUT PPR (the max_nodes nodes nearest the question's
               entities, or the whole graph with region="full"); GNN + GOAt pick the nodes that
               drive the top scores; PPR from those picks over the whole graph adds the facts
               around them
     ppr_goat_ppr  experiment C: PPR cuts the graph to max_nodes (as gnn_goat), GNN + GOAt pick
               nodes, then a short second PPR (restart 0.5) from the picks inside that region
   B and C rank: GOAt-picked facts first (by importance), then facts by the second PPR, then the
   GNN's ranking to fill the budget.
   If no entity links, every mode falls back to embedding similarity over current facts.
   Options (off by default): link_embed_k adds the k entities whose name embedding is closest to the
   question to the exact matches before PPR (HippoRAG-style linking); hybrid interleaves the mode's ranking
   with plain embedding search over all current facts, one fact from each in turn, duplicates dropped.
4. Latest-version rule: each fetched fact is replaced by its newest version; optionally the
   superseded versions are kept too, marked outdated.
5. Cut to the budget (max facts and max approximate tokens).
"""

import math
import re
from dataclasses import dataclass, field

import networkx as nx
import numpy as np
import torch

from my_method.gnn.eig import eig_edge_attributions
from my_method.gnn.explain import edge_attributions
from my_method.gnn.features import TextEmbedder, build_features, nearest_nodes, node_text, pagerank, ppr_scores, select_subgraph
from my_method.graph_store import GraphStore, entity_id, is_stopword_name, norm

MODES = ("gnn_goat", "gnn_topk", "ppr", "goat_ppr", "ppr_goat_ppr", "embed")


@dataclass
class RetrievalConfig:
    mode: str = "gnn_goat"
    max_facts: int = 300
    max_tokens: int = 5120  # approximate: 4 characters per token
    include_outdated: bool = False
    max_nodes: int = 400
    goat_targets: int = 3  # top-scored nodes whose predictions GOAt explains
    goat_topk: int = 12  # edges kept per explained node
    region: str = "nearest"  # goat_ppr only: "nearest" (max_nodes nearest by hops) | "full" (whole graph)
    expand_alpha: float = 0.5  # goat_ppr / ppr_goat_ppr: PageRank damping of the second walk (HippoRAG 2 uses 0.5)
    explainer: str = "goat"  # edge attribution in every GOAt step: "goat" (GOAt, ICLR 2024) | "eig" (EiG-Search, ICML 2024)
    link_embed_k: int = 0  # also link the k entities closest to the question by embedding (0 = exact match only)
    hybrid: bool = False  # interleave the mode's ranking with embedding search over all current facts
    hybrid_k: int = 0  # instead: the mode's top (max_facts - k) facts, then the top k embedding facts not yet included
    query_graph: bool = False  # Haiku turns the question into schema nodes/edges, attached for this question only
    query_match_min: float = 0.85  # name-embedding cosine needed to match a question entity to a graph entity
    query_linking: str = "embedding"  # "embedding" (cosine >= query_match_min) | "llm" (Haiku picks among the top 10)
    guide_planning: bool = False  # test 06 arm B: follow the parsed relation chain with the T-REx guide, facts first
    background_facts: int = 0  # test 06 arm D: with document_facts_only, also keep the top k base facts as labelled background
    document_facts_only: bool = False  # bridge option (test 06 arm C): outside-base facts stay in the walk, never returned
    adaptive: str = ""  # "drop" (G39/G40, docs/design/graft_adaptive_retrieval_design.md): rank a pool of max_facts,
    #                      show the first k, k at the largest score drop between min_facts and drop_max
    min_facts: int = 10
    drop_max: int = 100


@dataclass
class Region:
    facts: list[str]  # fact ids, most relevant first (current versions, then outdated ones if kept)
    outdated: set[str] = field(default_factory=set)
    linked_entities: list[str] = field(default_factory=list)
    subgraph_nodes: int = 0
    subgraph_facts: list[str] = field(default_factory=list)  # every fact in the GNN's subgraph (before ranking and budget)
    fallback: bool = False
    sources: list[str] = field(default_factory=list)  # per fact in `facts`: "graph", "embed" or "both" (hybrid / embed)
    query_graph: dict = field(default_factory=dict)  # query_graph option: the parsed edges and matched entities
    background: list[str] = field(default_factory=list)  # background_facts option: base facts shown apart, labelled
    plan: dict = field(default_factory=dict)  # guide_planning option: the chain followed and what was found
    pool: list[str] = field(default_factory=list)  # adaptive: the whole ranked pool; facts = its first `shown`
    shown: int = 0  # adaptive: how many pool facts are shown (the drop cutoff)
    fact_scores: dict = field(default_factory=dict)  # adaptive: shown/pool fact -> its ranking score


def _words(text: str) -> str:
    return " " + " ".join(re.findall(r"[a-z0-9]+", text.lower())) + " "


def drop_cut(scores: list[float], lo: int, hi: int) -> int:
    """How many facts to show (G39): sort the scores high to low and cut at the largest drop between neighbours,
    measured as a ratio (largest log s[i] - log s[i+1]), with the cut after position lo..hi. A score of 0 (never reached
    by the walk) after a positive one is an infinite drop. Fewer than lo scores: all of them."""
    s = sorted((max(float(x), 0.0) for x in scores), reverse=True)
    n = len(s)
    if n <= lo:
        return n
    hi = min(hi, n)
    best, cut = -1.0, lo  # no drop found (flat, or nothing scored): the minimum
    for i in range(lo - 1, hi - 1):
        a, b = s[i], s[i + 1]
        if a <= 0:
            break
        gap = float("inf") if b <= 0 else math.log(a) - math.log(b)
        if gap > best:
            best, cut = gap, i + 1
    return cut


class Retriever:
    def __init__(self, store: GraphStore, cfg: RetrievalConfig, texts: TextEmbedder, model=None):
        assert cfg.mode in MODES, cfg.mode
        if cfg.mode not in ("ppr", "embed") and model is None:
            raise ValueError(f"retrieval mode {cfg.mode} needs a trained GNN checkpoint")
        self.store, self.cfg, self.texts, self.model = store, cfg, texts, model
        names = [(e, _words(store.fact(e)["name"])) for e in store.entities()]
        # an entity named by a single stopword ("The") would match every question: never linked
        self.names = sorted([(e, w) for e, w in names if len(w.strip()) >= 3 and not is_stopword_name(w)],
                            key=lambda p: -len(p[1]))
        self._entity_vecs = None  # built on first use from cached vectors (forked workers never embed)

    def link(self, question: str) -> list[str]:
        q = _words(question)
        found: list[tuple[str, str]] = []
        for entity, words in self.names:
            if words in q and not any(words in longer for _, longer in found):
                found.append((entity, words))
        exact = [e for e, _ in found]
        if self.cfg.link_embed_k <= 0:
            return exact
        if self._entity_vecs is None:
            ids = self.store.entities()
            self._entity_vecs = (ids, self.texts.embed_texts([node_text(self.store, e) for e in ids]))
        ids, vecs = self._entity_vecs
        if not ids:
            return exact
        sims = vecs @ self.texts.embed_one(question)
        extra = [ids[i] for i in np.argsort(-sims)[: self.cfg.link_embed_k + len(exact) + 5]
                 if ids[i] not in exact and not is_stopword_name(self.store.fact(ids[i])["name"])]
        return exact + extra[: self.cfg.link_embed_k]

    def retrieve(self, question: str) -> Region:
        self._fact_score = {}
        region = self._retrieve_ranked(question)
        if self.cfg.adaptive == "drop":
            self._drop_cutoff(region)
        return region

    def _drop_cutoff(self, region: Region) -> None:
        """G39: keep G35's order, show only the first k facts of the pool, k at the largest score drop."""
        pool = list(region.facts)
        scores = [region.fact_scores.get(f, 0.0) for f in pool]
        n_plan = sum(1 for s in region.sources if s == "plan") if region.sources else 0
        k = max(drop_cut(scores, self.cfg.min_facts, self.cfg.drop_max), n_plan)
        region.pool, region.shown = pool, min(k, len(pool))
        region.facts = pool[:region.shown]
        if region.sources:
            region.sources = region.sources[:region.shown]

    def _retrieve_ranked(self, question: str) -> Region:
        if self.cfg.guide_planning and not self.cfg.query_graph:
            return self._with_plan(question, self._retrieve(question))
        if not self.cfg.query_graph:
            return self._retrieve(question)
        added, matched, qfacts = self._attach_query(question)
        try:
            region = self._retrieve(question, extra_seeds=matched + qfacts, extra_entities=matched)
            region.query_graph = {"edges": [list(e) for e in self.query_graphs.get(question, [])], "matched": matched}
            return region
        finally:
            self._detach_query(added)

    def _retrieve(self, question: str, extra_seeds: list[str] = (), extra_entities: list[str] = ()) -> Region:
        self._merge_info = None
        if self.cfg.mode == "embed":  # baseline: plain embedding search over all current facts, same budget
            region = self._finish(self._similar_facts(question), Region([]))
            region.sources = ["embed"] * len(region.facts)
            return region
        linked = list(dict.fromkeys(self.link(question) + list(extra_entities)))
        seeds = list(dict.fromkeys(linked + list(extra_seeds)))
        if not seeds:
            return self._finish(self._similar_facts(question, record=True), Region([], fallback=True))
        if self.cfg.mode == "ppr":
            return self._finish(self._merge(question, self._ppr(linked)),
                                Region([], linked_entities=linked, subgraph_nodes=self.store.g.number_of_nodes()))
        if self.cfg.mode == "goat_ppr":
            nodes = (self.store.entities() + self.store.facts() if self.cfg.region == "full"
                     else nearest_nodes(self.store, linked, self.cfg.max_nodes))
            nodes = [n for n in linked if n in nodes] + [n for n in nodes if n not in linked]
        else:
            nodes = select_subgraph(self.store, seeds, self.cfg.max_nodes)
        region = Region([], linked_entities=linked, subgraph_nodes=len(nodes),
                        subgraph_facts=[n for n in nodes if self._is_fact(n)])
        sub = build_features(self.store, nodes, linked, question, self.texts)
        with torch.no_grad():
            scores = self.model(sub.x, sub.edge_index)[:, 1].numpy()
        if self.cfg.mode in ("goat_ppr", "ppr_goat_ppr"):
            ranked = self._goat_then_ppr(sub, scores, whole_graph=self.cfg.mode == "goat_ppr")
        elif self.cfg.mode == "gnn_goat":
            ranked = self._goat(sub, scores)
        else:
            ranked = self._by_score(nodes, scores)
        return self._finish(self._merge(question, ranked), region)

    def _with_plan(self, question: str, region: Region) -> Region:
        """guide_planning: the facts found by following the parsed chain go first (current versions, document facts
        only), then the mode's facts, within the same max_facts."""
        edges = getattr(self, "query_graphs", {}).get(question) or []
        chain, log = self.guide.plan(self.store, edges, self.link(question))
        rest = [f for f in region.facts if f not in chain]
        n_rest = max(self.cfg.max_facts - len(chain), 0)
        srcs = dict(zip(region.facts, region.sources)) if region.sources else {}
        region.facts = chain + rest[:n_rest]
        region.sources = ["plan"] * len(chain) + [srcs.get(f, "graph") for f in rest[:n_rest]]
        region.plan = {"edges": [list(e) for e in edges], **log}
        return region

    def _merge(self, question: str, ranked: list[str]) -> list[str]:
        """hybrid: one fact from the mode's ranking, then one from embedding search, in turn; duplicates dropped.
        hybrid_k: the ranking's top (max_facts - k), then the top k embedding facts not already among them."""
        if self.cfg.hybrid_k > 0:
            head = ranked[: max(self.cfg.max_facts - self.cfg.hybrid_k, 0)]
            have = set(head) | {self.store.current(f) for f in head}
            extra = [f for f in self._similar_facts(question) if f not in have][: self.cfg.hybrid_k]
            self._merge_info = ("topk", set(head), set(extra))
            return head + extra + [f for f in ranked[len(head):] if f not in extra]
        if not self.cfg.hybrid:
            return ranked
        similar = self._similar_facts(question)
        out, seen, rounds = [], set(), {}
        for i in range(max(len(ranked), len(similar))):
            for lst in (ranked, similar):
                if i < len(lst) and lst[i] not in seen:
                    seen.add(lst[i])
                    out.append(lst[i])
                    rounds[lst[i]] = i
        self._merge_info = (ranked, similar, rounds)  # lets _finish label each kept fact by where it came from
        return out

    # ---- ranking ----

    def _is_fact(self, node: str) -> bool:
        d = self.store.fact(node)
        return d["type"] == "Fact" and not d.get("query")  # question-graph facts are never retrieved

    # ---- question graph (query_graph option) ----

    def prepare_query_links(self, questions: list[str], link) -> None:
        """query_linking="llm": for each question's named entities, link(question, names) -> {name: entity id or None}.
        Runs in the parent after prepare_queries; results are read by workers."""
        self.query_links = getattr(self, "query_links", {})
        from concurrent.futures import ThreadPoolExecutor
        todo = [q for q in questions if q not in self.query_links]
        names = {q: sorted({x for s, _, o in self.query_graphs.get(q, []) for x in (s, o)
                            if not x.startswith("?") and not is_stopword_name(x)}) for q in todo}
        with ThreadPoolExecutor(8) as pool:
            for q, m in zip(todo, pool.map(lambda q: link(q, names[q]) if names[q] else {}, todo)):
                self.query_links[q] = m

    def prepare_queries(self, questions: list[str], parse) -> None:
        """Parent process, before workers fork: parse every question (parse(q) -> [(subject, relation, object)])
        and embed every text the question graphs will need, so workers only read cached vectors."""
        self.query_graphs = getattr(self, "query_graphs", {})
        from concurrent.futures import ThreadPoolExecutor
        todo = [q for q in dict.fromkeys(questions) if q not in self.query_graphs]
        with ThreadPoolExecutor(8) as pool:
            for q, edges in zip(todo, pool.map(parse, todo)):
                self.query_graphs[q] = edges
        # exactly the texts node_text() will produce for these question graphs (forked workers cannot embed):
        # every entity name, placeholders included, and each fact as "subject relation object" with the relation
        # normalised as the graph stores it
        names = {x for edges in self.query_graphs.values() for s, _, o in edges for x in (s, o)}
        facts = [f"{s} {norm(r)} {o}" for edges in self.query_graphs.values() for s, r, o in edges]
        self.texts.embed_texts(sorted(names) + facts)
        self._entity_matrix()

    def _entity_matrix(self):
        if getattr(self, "_ent_norm", None) is None:
            ids = self.store.entities()
            vecs = self.texts.embed_texts([node_text(self.store, e) for e in ids]) if ids else np.zeros((0, self.texts.dim))
            vecs = vecs / (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-8)
            self._ent_norm = (ids, vecs)
        return self._ent_norm

    def _match_entity(self, name: str) -> str | None:
        exact = entity_id(name)
        if exact in self.store.g and self.store.fact(exact)["type"] == "Entity":
            return exact
        ids, vecs = self._entity_matrix()
        if not ids:
            return None
        v = self.texts.embed_one(name)
        sims = vecs @ (v / (np.linalg.norm(v) + 1e-8))
        i = int(np.argmax(sims))
        return ids[i] if sims[i] >= self.cfg.query_match_min else None

    def _attach_query(self, question: str) -> tuple[list[str], list[str], list[str]]:
        """Add this question's graph: matched entities are reused, unknowns (?X) and unmatched names become
        temporary entity nodes, each edge a temporary fact node. Returns (added nodes, matched entities, query facts)."""
        edges = getattr(self, "query_graphs", {}).get(question) or []
        g, simple = self.store.g, self.store.simple_graph()
        added, matched, qfacts, node_of = [], [], [], {}

        def node_for(name: str) -> str:
            if name in node_of:
                return node_of[name]
            if name.startswith("?") or is_stopword_name(name):  # a bare "the" / "who" is never linked
                m = None
            elif self.cfg.query_linking == "llm":
                m = getattr(self, "query_links", {}).get(question, {}).get(name)
            else:
                m = self._match_entity(name)
            if m and is_stopword_name(self.store.fact(m)["name"]):  # nor linked to an entity named "The"
                m = None
            if m:
                matched.append(m)
                node_of[name] = m
                return m
            n = f"q:{norm(name)}"
            if n not in g:
                g.add_node(n, type="Entity", name=name, query=True)
                simple.add_node(n, type="Entity", name=name, query=True)
                added.append(n)
            node_of[name] = n
            return n

        for i, (s, r, o) in enumerate(edges):
            su, ob = node_for(s), node_for(o)
            f = f"qf:{i}"
            attrs = dict(type="Fact", subject=s, relation=norm(r), object=o, query=True, mentions=[],
                         provenance={"chunk_id": -1, "arrival": self.store.next_arrival, "serial": None, "span": f"{s} {r} {o}"})
            g.add_node(f, **attrs)
            simple.add_node(f, **attrs)
            g.add_edge(su, f, type="subject_of")
            g.add_edge(ob, f, type="object_of")
            simple.add_edge(su, f)
            simple.add_edge(ob, f)
            added.append(f)
            qfacts.append(f)
        return added, list(dict.fromkeys(matched)), qfacts

    def _detach_query(self, added: list[str]) -> None:
        self.store.g.remove_nodes_from(added)
        if self.store._simple is not None:
            self.store._simple.remove_nodes_from(added)

    def _by_score(self, nodes: list[str], scores: np.ndarray) -> list[str]:
        order = np.argsort(-scores)
        return [nodes[i] for i in order if self._is_fact(nodes[i])]

    def _attributions(self, sub):
        """Per node, its goat_topk most important edges, by the configured explainer."""
        if self.cfg.explainer == "eig":
            return eig_edge_attributions(self.model, sub.x, sub.edge_index, self.cfg.goat_topk)
        return edge_attributions(self.model, sub.x, sub.edge_index, self.cfg.goat_topk)

    def _goat(self, sub, scores: np.ndarray) -> list[str]:
        """Facts touched by the edges GOAt finds most important for the top-scored nodes."""
        if sub.edge_index.shape[1] == 0:
            return self._by_score(sub.nodes, scores)
        edge_scores, edge_ids = self._attributions(sub)
        importance: dict[str, float] = {}
        for target in np.argsort(-scores)[: self.cfg.goat_targets]:
            if self._is_fact(sub.nodes[target]):
                importance[sub.nodes[target]] = max(importance.get(sub.nodes[target], 0.0), float(scores[target]))
            for score, edge in zip(edge_scores[target].tolist(), edge_ids[target].tolist()):
                if score <= 0:
                    continue
                for end in sub.edge_index[:, edge].tolist():
                    node = sub.nodes[end]
                    if self._is_fact(node):
                        importance[node] = max(importance.get(node, 0.0), score)
        ranked = sorted(importance, key=lambda n: -importance[n])
        rest = [n for n in self._by_score(sub.nodes, scores) if n not in importance]
        return ranked + rest  # GOAt's region first, then the GNN's ranking to fill the budget

    def _goat_nodes(self, sub, scores: np.ndarray) -> dict[str, float]:
        """Every node (entity or fact) GOAt finds behind the top scores, with its importance."""
        importance: dict[str, float] = {}
        if sub.edge_index.shape[1] == 0:
            return {sub.nodes[t]: float(scores[t]) for t in np.argsort(-scores)[: self.cfg.goat_targets]}
        edge_scores, edge_ids = self._attributions(sub)
        for target in np.argsort(-scores)[: self.cfg.goat_targets]:
            node = sub.nodes[target]
            importance[node] = max(importance.get(node, 0.0), float(scores[target]))
            for score, edge in zip(edge_scores[target].tolist(), edge_ids[target].tolist()):
                if score <= 0:
                    continue
                for end in sub.edge_index[:, edge].tolist():
                    importance[sub.nodes[end]] = max(importance.get(sub.nodes[end], 0.0), score)
        return importance

    def _goat_then_ppr(self, sub, scores: np.ndarray, whole_graph: bool) -> list[str]:
        """Experiments B and C: GOAt's picks, then a PPR walk from them, then the GNN's ranking."""
        picks = self._goat_nodes(sub, scores)
        graph = self.store.simple_graph() if whole_graph else self.store.simple_graph().subgraph(sub.nodes)
        seeds = {n: w for n, w in picks.items() if n in graph and w > 0} or {sub.nodes[int(np.argmax(scores))]: 1.0}
        rank = pagerank(graph, seeds, alpha=self.cfg.expand_alpha)
        self._fact_score = {n: float(v) for n, v in rank.items()}  # the second walk's mass, for the drop cutoff
        picked = sorted((n for n in picks if self._is_fact(n)), key=lambda n: -picks[n])
        walked = sorted((n for n in rank if n not in picks and self._is_fact(n)), key=lambda n: -rank[n])
        rest = [n for n in self._by_score(sub.nodes, scores) if n not in picks and n not in rank]
        return picked + walked + rest

    def _ppr(self, seeds: list[str]) -> list[str]:
        rank = ppr_scores(self.store, seeds)
        return sorted((n for n in rank if self._is_fact(n)), key=lambda n: -rank[n])

    def _similar_facts(self, question: str, record: bool = False) -> list[str]:
        current = [f for f in self.store.facts() if not self.store.is_superseded(f)]
        if not current:
            return []
        vecs = self.texts.embed_texts([node_text(self.store, f) for f in current])
        sims = vecs @ self.texts.embed_one(question)
        if record:  # the fallback ranking's scores (cosine), for the drop cutoff
            self._fact_score = {current[i]: float(sims[i]) for i in range(len(current))}
        return [current[i] for i in np.argsort(-sims)]

    # ---- latest-version rule and budget ----

    def _finish(self, ranked: list[str], region: Region) -> Region:
        chosen: list[str] = []
        picked: list[str] = []  # the ranked fact behind each chosen (newest) fact
        outdated: list[str] = []
        budget_chars = self.cfg.max_tokens * 4
        for fact in ranked:
            newest = self.store.current(fact)
            if newest in chosen:
                continue
            if self.cfg.document_facts_only and self.store.fact(newest).get("layer") == "base":
                if len(region.background) < self.cfg.background_facts and newest not in region.background:
                    region.background.append(newest)
                continue
            chosen.append(newest)
            picked.append(fact)
            region.fact_scores[newest] = max(getattr(self, "_fact_score", {}).get(fact, 0.0),
                                             getattr(self, "_fact_score", {}).get(newest, 0.0))
            if self.cfg.include_outdated and fact != newest and fact not in outdated:
                outdated.append(fact)
            text = sum(len(self.store.fact(f)["provenance"]["span"]) for f in chosen + outdated)
            if len(chosen) >= self.cfg.max_facts or text >= budget_chars:
                break
        region.facts = chosen + outdated
        region.outdated = set(outdated)
        info = getattr(self, "_merge_info", None)
        if info and picked and info[0] == "topk":
            _, g, e = info
            region.sources = [("embed" if f in e else "graph") for f in picked] + [""] * len(outdated)
        elif info and picked:
            graph, similar, rounds = info
            cut = max(rounds[f] for f in picked) + 1  # both lists were walked this far before the budget ran out
            g, e = set(graph[:cut]), set(similar[:cut])
            region.sources = [("both" if f in g and f in e else "graph" if f in g else "embed") for f in picked] + [""] * len(outdated)
        return region
