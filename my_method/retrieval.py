"""SGAR read phase: find the region of the memory graph that answers a question.

1. Link the question to graph entities (exact name match on normalised words; longest names win).
2. For the GNN modes, let PPR pick the most relevant nodes in the whole graph (as many as the GNN
   was trained with).
3. Rank facts, by retrieval mode:
     gnn_goat  trained GNN scores nodes; GOAt attributes the top-scored nodes' predictions to edges;
               the facts on the most important edges are the region (the method as designed)
     gnn_topk  trained GNN scores nodes; the highest-scored facts are the region (ablation)
     ppr       Personalized PageRank over the whole graph, no GNN and no depth limit (ablation,
               as HippoRAG does it)
   If no entity links, every mode falls back to embedding similarity over current facts.
4. Latest-version rule: each fetched fact is replaced by its newest version; optionally the
   superseded versions are kept too, marked outdated.
5. Cut to the budget (max facts and max approximate tokens).
"""

import re
from dataclasses import dataclass, field

import numpy as np
import torch

from my_method.gnn.explain import edge_attributions
from my_method.gnn.features import TextEmbedder, build_features, node_text, ppr_scores, select_subgraph
from my_method.graph_store import GraphStore

MODES = ("gnn_goat", "gnn_topk", "ppr")


@dataclass
class RetrievalConfig:
    mode: str = "gnn_goat"
    max_facts: int = 300
    max_tokens: int = 5120  # approximate: 4 characters per token
    include_outdated: bool = False
    max_nodes: int = 400
    goat_targets: int = 3  # top-scored nodes whose predictions GOAt explains
    goat_topk: int = 12  # edges kept per explained node


@dataclass
class Region:
    facts: list[str]  # fact ids, most relevant first (current versions, then outdated ones if kept)
    outdated: set[str] = field(default_factory=set)
    linked_entities: list[str] = field(default_factory=list)
    subgraph_nodes: int = 0
    fallback: bool = False


def _words(text: str) -> str:
    return " " + " ".join(re.findall(r"[a-z0-9]+", text.lower())) + " "


class Retriever:
    def __init__(self, store: GraphStore, cfg: RetrievalConfig, texts: TextEmbedder, model=None):
        assert cfg.mode in MODES, cfg.mode
        if cfg.mode != "ppr" and model is None:
            raise ValueError(f"retrieval mode {cfg.mode} needs a trained GNN checkpoint")
        self.store, self.cfg, self.texts, self.model = store, cfg, texts, model
        names = [(e, _words(store.fact(e)["name"])) for e in store.entities()]
        self.names = sorted([(e, w) for e, w in names if len(w.strip()) >= 3], key=lambda p: -len(p[1]))

    def link(self, question: str) -> list[str]:
        q = _words(question)
        found: list[tuple[str, str]] = []
        for entity, words in self.names:
            if words in q and not any(words in longer for _, longer in found):
                found.append((entity, words))
        return [e for e, _ in found]

    def retrieve(self, question: str) -> Region:
        linked = self.link(question)
        if not linked:
            return self._finish(self._similar_facts(question), Region([], fallback=True))
        if self.cfg.mode == "ppr":
            return self._finish(self._ppr(linked), Region([], linked_entities=linked,
                                                          subgraph_nodes=self.store.g.number_of_nodes()))
        nodes = select_subgraph(self.store, linked, self.cfg.max_nodes)
        region = Region([], linked_entities=linked, subgraph_nodes=len(nodes))
        sub = build_features(self.store, nodes, linked, question, self.texts)
        with torch.no_grad():
            scores = self.model(sub.x, sub.edge_index)[:, 1].numpy()
        ranked = self._goat(sub, scores) if self.cfg.mode == "gnn_goat" else self._by_score(nodes, scores)
        return self._finish(ranked, region)

    # ---- ranking ----

    def _is_fact(self, node: str) -> bool:
        return self.store.fact(node)["type"] == "Fact"

    def _by_score(self, nodes: list[str], scores: np.ndarray) -> list[str]:
        order = np.argsort(-scores)
        return [nodes[i] for i in order if self._is_fact(nodes[i])]

    def _goat(self, sub, scores: np.ndarray) -> list[str]:
        """Facts touched by the edges GOAt finds most important for the top-scored nodes."""
        if sub.edge_index.shape[1] == 0:
            return self._by_score(sub.nodes, scores)
        edge_scores, edge_ids = edge_attributions(self.model, sub.x, sub.edge_index, self.cfg.goat_topk)
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

    def _ppr(self, seeds: list[str]) -> list[str]:
        rank = ppr_scores(self.store, seeds)
        return sorted((n for n in rank if self._is_fact(n)), key=lambda n: -rank[n])

    def _similar_facts(self, question: str) -> list[str]:
        current = [f for f in self.store.facts() if not self.store.is_superseded(f)]
        if not current:
            return []
        vecs = self.texts.embed_texts([node_text(self.store, f) for f in current])
        sims = vecs @ self.texts.embed_one(question)
        return [current[i] for i in np.argsort(-sims)]

    # ---- latest-version rule and budget ----

    def _finish(self, ranked: list[str], region: Region) -> Region:
        chosen: list[str] = []
        outdated: list[str] = []
        budget_chars = self.cfg.max_tokens * 4
        for fact in ranked:
            newest = self.store.current(fact)
            if newest in chosen:
                continue
            chosen.append(newest)
            if self.cfg.include_outdated and fact != newest and fact not in outdated:
                outdated.append(fact)
            text = sum(len(self.store.fact(f)["provenance"]["span"]) for f in chosen + outdated)
            if len(chosen) >= self.cfg.max_facts or text >= budget_chars:
                break
        region.facts = chosen + outdated
        region.outdated = set(outdated)
        return region
