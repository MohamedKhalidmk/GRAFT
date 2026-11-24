# Sources: subgraphrag (docs/reference/REFERENCES.md)
"""Weak node labels for GNN training, as in SubgraphRAG (Li et al., ICLR 2025).

A node is positive if it lies on a shortest path between a question entity and an answer entity,
walking only through current (not superseded) facts, so the GNN learns to prefer newest versions.
Everything else in the subgraph is negative.
"""

from itertools import islice

import networkx as nx

from my_method.graph_store import GraphStore

MAX_PATHS = 20  # per (question entity, answer) pair; hubs can have thousands


def weak_labels(store: GraphStore, nodes: list[str], question_entities: list[str],
                answer_entities: list[str]) -> list[int]:
    keep = [n for n in nodes if store.fact(n)["type"] == "Entity" or not store.is_superseded(n)]
    sub = store.g.subgraph(keep).to_undirected(as_view=True)
    positive: set[str] = set()
    for q in question_entities:
        for a in answer_entities:
            if q in sub and a in sub and nx.has_path(sub, q, a):
                for path in islice(nx.all_shortest_paths(sub, q, a), MAX_PATHS):
                    positive.update(path)
    return [int(n in positive) for n in nodes]
