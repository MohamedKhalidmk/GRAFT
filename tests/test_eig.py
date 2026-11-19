"""EiG-Search attribution: the batched version matches EiG-Search's own per-edge loop (main.py, NC branch)."""
import torch

from my_method.gnn.eig import eig_edge_attributions
from my_method.gnn.goat import GCN_NC


def _graph(n=30, m=40, dim=16, seed=0):
    g = torch.Generator().manual_seed(seed)
    x = torch.rand(n, dim, generator=g)
    pairs = set()
    while len(pairs) < m:
        a, b = torch.randint(0, n, (2,), generator=g).tolist()
        if a != b:
            pairs.add((min(a, b), max(a, b)))
    e = torch.tensor(sorted(pairs)).T
    return x, torch.cat([e, e.flip(0)], dim=1)


def test_batched_matches_eig_loop():
    torch.manual_seed(0)
    x, ei = _graph()
    model = GCN_NC(16, 2, 3, 8).eval()
    with torch.no_grad():
        base = model(x, ei)
        ref = torch.stack([torch.linalg.vector_norm(base - model.fwd(x, ei, de=e, epsilon=0.0), dim=-1)
                           for e in range(ei.shape[1])])          # (m, n), EiG's own code path
    scores, edges = eig_edge_attributions(model, x, ei, topk=6, batch=7)
    for v in range(x.shape[0]):
        want = torch.topk(ref[:, v], 6).values
        assert torch.allclose(scores[v], want, atol=1e-6)
        assert torch.allclose(ref[edges[v], v], scores[v], atol=1e-6)
