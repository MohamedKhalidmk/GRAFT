"""Question-conditioned node features for a subgraph of the memory graph.

GOAt's GCN has one edge type and no edge features, so what the graph's typed edges would carry
is put into node features instead (SUPERSEDES status, node type). Hop distance from the question's
entities is a feature too, as in SubgraphRAG's directional distance encoding: it gives every node
a question signal even beyond the GCN's 3-layer reach.

Feature layout (in order):
    node type one-hot (Entity, Fact)                          2
    is a question entity                                      1
    hop distance from question entities, one-hot 0..MAX_HOP+1 MAX_HOP + 2   (last = farther / none)
    cosine(question, node text)                               1
    fact is superseded / fact is current                      2
    fact recency (arrival rank within the subgraph, 0..1)     1
    node text embedding                                       embedding dim
"""

from dataclasses import dataclass

import networkx as nx
import numpy as np
import torch

from my_method.graph_store import GraphStore

MAX_HOP = 6
N_STRUCTURAL = 2 + 1 + (MAX_HOP + 2) + 1 + 2 + 1


def feature_dim(embedding_dim: int) -> int:
    return N_STRUCTURAL + embedding_dim


def node_text(store: GraphStore, node: str) -> str:
    d = store.fact(node)
    if d["type"] == "Entity":
        return d["name"]
    return f"{d['subject']} {d['relation']} {d['object']}"


class TextEmbedder:
    """Embeds node and question texts with the run's embedding model, caching node vectors."""

    def __init__(self, embedder):
        self.embedder = embedder
        self.dim = embedder.dim
        self.cache: dict[str, np.ndarray] = {}
        self.index: dict[str, int] = {}  # text -> row of table(), filled by ids()

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]  # cached, so forked workers never touch the GPU model

    def ids(self, texts: list[str]) -> list[int]:
        """Row numbers of these texts in table(); lets training graphs share one embedding table."""
        self.embed_texts(texts)
        return [self.index.setdefault(t, len(self.index)) for t in texts]

    def table(self) -> np.ndarray:
        return np.stack([self.cache[t] for t in self.index])  # dict order = row order

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if missing:
            for t, v in zip(missing, self.embedder.embed(missing)):
                self.cache[t] = v
        return np.stack([self.cache[t] for t in texts]) if texts else np.zeros((0, self.dim), np.float32)


def ppr_scores(store: GraphStore, seeds: list[str]) -> dict[str, float]:
    """Personalized PageRank from the seeds over the whole graph. A walker splits its steps across
    a node's links, so hubs (a country linked to 1,000 facts) pass on little to each neighbour."""
    return nx.pagerank(store.simple_graph(), personalization={s: 1.0 for s in seeds})


def select_subgraph(store: GraphStore, seeds: list[str], max_nodes: int) -> list[str]:
    """The max_nodes nodes most relevant to the seeds anywhere in the graph, seeds first.
    Picking the nearest nodes instead lets hubs fill the budget before chains reach their answers."""
    seeds = [s for s in seeds if s in store.g]
    rank = ppr_scores(store, seeds)
    rest = sorted((n for n in rank if n not in seeds), key=lambda n: -rank[n])
    return (seeds + rest)[:max_nodes]


def nearest_nodes(store: GraphStore, seeds: list[str], max_nodes: int) -> list[str]:
    """The max_nodes nodes closest to the seeds by hop count (breadth-first), seeds first. No PPR:
    the region experiment B uses, so the GNN, not PageRank, decides what matters."""
    g = store.simple_graph()
    seen = [s for s in dict.fromkeys(seeds) if s in g]
    frontier, found = list(seen), set(seen)
    while frontier and len(seen) < max_nodes:
        nxt = []
        for node in frontier:
            for nb in sorted(g.neighbors(node)):
                if nb not in found:
                    found.add(nb)
                    seen.append(nb)
                    nxt.append(nb)
        frontier = nxt
    return seen[:max_nodes]


@dataclass
class SubgraphTensors:
    nodes: list[str]  # graph node ids, index i <-> row i
    x: torch.Tensor
    edge_index: torch.Tensor  # undirected: both directions of every edge


def build_features(store: GraphStore, nodes: list[str], question_entities: list[str], question: str,
                   texts: TextEmbedder) -> SubgraphTensors:
    index = {n: i for i, n in enumerate(nodes)}
    sub = store.g.subgraph(nodes).to_undirected(as_view=True)
    hops = nx.multi_source_dijkstra_path_length(sub, [q for q in question_entities if q in index]) \
        if any(q in index for q in question_entities) else {}

    node_vecs = texts.embed_texts([node_text(store, n) for n in nodes])
    q_vec = texts.embed_one(question)
    cosine = node_vecs @ q_vec / (np.linalg.norm(node_vecs, axis=1) * np.linalg.norm(q_vec) + 1e-8)

    facts = [n for n in nodes if store.fact(n)["type"] == "Fact"]
    by_arrival = sorted(facts, key=lambda f: store.fact(f)["provenance"]["arrival"])
    recency = {f: (rank / max(1, len(by_arrival) - 1)) for rank, f in enumerate(by_arrival)}

    structural = np.zeros((len(nodes), N_STRUCTURAL), np.float32)
    qset = set(question_entities)
    for i, n in enumerate(nodes):
        is_fact = store.fact(n)["type"] == "Fact"
        structural[i, 0 if not is_fact else 1] = 1
        structural[i, 2] = n in qset
        hop = hops.get(n)
        structural[i, 3 + (min(int(hop), MAX_HOP) if hop is not None else MAX_HOP + 1)] = 1
        base = 3 + MAX_HOP + 2
        structural[i, base] = cosine[i]
        if is_fact:
            superseded = store.is_superseded(n)
            structural[i, base + 1] = superseded
            structural[i, base + 2] = not superseded
            structural[i, base + 3] = recency[n]
    x = torch.from_numpy(np.concatenate([structural, node_vecs.astype(np.float32)], axis=1))

    # one undirected edge per node pair: GOAt keys edges by (a, b), and a fact whose subject and
    # object are the same entity would otherwise give two parallel edges
    edges = sorted({tuple(sorted((index[u], index[v]))) for u, v in sub.edges() if u != v})
    pairs = edges + [(v, u) for u, v in edges]
    edge_index = torch.tensor(pairs, dtype=torch.long).t() if pairs else torch.zeros((2, 0), dtype=torch.long)
    return SubgraphTensors(nodes, x, edge_index)
