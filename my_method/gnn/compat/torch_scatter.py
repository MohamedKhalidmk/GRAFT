"""Stand-in for `torch_scatter`, used only when the compiled package is unavailable (it does not
build against current torch on macOS). GOAt's GCNConv imports `scatter_add` but calls it only in
`gcn_norm`, i.e. with normalize=True; GOAt's models use normalize=False."""

import torch


def scatter_add(src: torch.Tensor, index: torch.Tensor, dim: int = -1, dim_size: int | None = None) -> torch.Tensor:
    size = list(src.shape)
    size[dim] = dim_size if dim_size is not None else int(index.max()) + 1
    return torch.zeros(size, dtype=src.dtype, device=src.device).index_add_(dim, index, src)
