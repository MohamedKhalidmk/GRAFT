# Sources: eig-search (docs/reference/REFERENCES.md)
"""EiG-Search edge attribution (Lu et al., ICML 2024; github.com/sluxsr/EiG-Search, main.py node-classification
branch) on GRAFT's trained GCN_NC.

EiG scores an edge by removing it (with its reverse: edge weight -> epsilon = 0) and measuring how much every
node's predicted class distribution moves: score[e, v] = || p(v) - p_without_e(v) ||_2. One forward pass per
undirected edge, so the cost is linear in |E|. GOAt's and EiG's GCN_NC classes are the same code, so the
trained weights are used directly through `fwd_cam(x, edge_index, edge_weight)`. Here the removals are batched:
B copies of the subgraph are joined into one disjoint graph, each copy with one edge pair removed.

Returns the same shapes as GOAt's attribution (`explain.edge_attributions`): for each node, its `topk`
highest-scoring directed edges (an undirected pair counts as two directed edges, as in both codebases).
"""

import torch


def _pairs(edge_index: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Group directed edges into undirected pairs: (pair id per directed edge, number of pairs)."""
    a = torch.minimum(edge_index[0], edge_index[1])
    b = torch.maximum(edge_index[0], edge_index[1])
    key = a * (int(edge_index.max()) + 1) + b
    _, pair = torch.unique(key, return_inverse=True)
    return pair, int(pair.max()) + 1


@torch.no_grad()
def eig_edge_attributions(model, x: torch.Tensor, edge_index: torch.Tensor, topk: int,
                          epsilon: float = 0.0, batch: int = 64) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    n, m = x.shape[0], edge_index.shape[1]
    ones = torch.ones(m, dtype=torch.float)
    base = model.fwd_cam(x, edge_index, ones)                       # (n, classes)
    pair, n_pairs = _pairs(edge_index)
    pair_score = torch.empty(n_pairs, n)
    for start in range(0, n_pairs, batch):
        ids = torch.arange(start, min(start + batch, n_pairs))
        b = len(ids)
        xs = x.repeat(b, 1)
        ei = torch.cat([edge_index + k * n for k in range(b)], dim=1)
        w = ones.repeat(b)
        for k, p in enumerate(ids.tolist()):
            w[k * m + (pair == p).nonzero(as_tuple=True)[0]] = epsilon
        out = model.fwd_cam(xs, ei, w).view(b, n, -1)
        pair_score[ids] = torch.linalg.vector_norm(out - base.unsqueeze(0), dim=-1)
    edge_score = pair_score[pair]                                    # (m, n): every directed edge gets its pair's score
    k = min(topk, m)
    scores, edges = torch.topk(edge_score.T, k, dim=-1)              # per node: top-k directed edges
    return scores, edges
