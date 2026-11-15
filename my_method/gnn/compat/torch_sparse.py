"""Stand-in for `torch_sparse`, used only when the compiled package is unavailable. GOAt's GCNConv
imports these names for its SparseTensor code path; we always pass dense edge_index tensors, so
the functions are never reached and raise if they ever are."""


class SparseTensor:  # only used in isinstance() checks
    pass


def _unavailable(*args, **kwargs):
    raise NotImplementedError("torch_sparse is not installed; GRAFT uses dense edge_index tensors only")


fill_diag = matmul = mul = sum = _unavailable
