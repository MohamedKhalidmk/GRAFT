"""Run GOAt's `gcn_explain` on GRAFT's trained GCN_NC for one question subgraph.

GOAt reads the model's per-layer activations from forward hooks and its weights by parameter
name, exactly as GOAt's own node-classification driver (gcn_nc.py `main`) sets them up. We
explain the "relevant" class (1) for every node (mutual=0, y = class-1 one-hot) on an undirected
graph (is_undirected=1, every edge present in both directions).
"""

from types import SimpleNamespace

import torch

from my_method.gnn.goat import GCN_NC, gcn_explain

HOOKED = ("conv1", "convs.0", "convs.1", "lin1", "lin2")


def edge_attributions(model: GCN_NC, x: torch.Tensor, edge_index: torch.Tensor,
                      topk: int) -> tuple[torch.Tensor, torch.Tensor]:
    """Return (scores, edge ids): for each node, its `topk` most important edges for class 1."""
    activation: dict[str, torch.Tensor] = {}
    modules = dict(model.named_modules())
    hooks = [modules[name].register_forward_hook(
        lambda _m, _i, out, name=name: activation.__setitem__(name, out.detach())) for name in HOOKED]
    try:
        model.eval()
        with torch.no_grad():
            model(x, edge_index)
            params = dict(model.named_parameters())
            weights = [params[f"{n}.lin.weight" if n.startswith("conv") else f"{n}.weight"].data.float()
                       for n in HOOKED]
            bias = [params[f"{n}.bias"].data.float() for n in HOOKED]
            y = torch.zeros(x.shape[0], 2)
            y[:, 1] = 1
            scores, edges = gcn_explain(model, x, edge_index, y, weights, bias, activation,
                                        SimpleNamespace(is_undirected=1), 2.0, -1, 1e-12,
                                        topk=min(topk, edge_index.shape[1]), mutual=0)
    finally:
        for h in hooks:
            h.remove()
    return torch.as_tensor(scores), torch.as_tensor(edges)
