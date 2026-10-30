"""Import Prof. Lu's GOAt (ICLR 2024) node-classification code from the pinned submodule.

my_method/gnn/GOAt is https://github.com/sluxsr/GOAt at commit 1ef20f0, unmodified. We use its
`GCN_NC` model (3 GCN layers + 2 linear layers, the architecture `gcn_explain` decomposes) and its
`gcn_explain` attribution function.
"""

import importlib.util
import sys
from pathlib import Path

GOAT_NC = Path(__file__).resolve().parent / "GOAt" / "node_classification_pack"
# The NC pack's Utils/utils.py imports GIN and GraphSAGE model files that only exist in the
# graph-classification pack. Neither pack has __init__.py, so with both on the path Python merges
# GNN_Models/ and Utils/ (NC files first) and the NC code imports unmodified.
GOAT_GC = GOAT_NC.parent / "graph_classification_pack"
COMPAT = Path(__file__).resolve().parent / "compat"

for _name in ("torch_scatter", "torch_sparse"):
    if importlib.util.find_spec(_name) is None and str(COMPAT) not in sys.path:
        sys.path.append(str(COMPAT))  # stand-ins, see compat/
sys.path[:0] = [str(GOAT_NC), str(GOAT_GC)]

from GNN_Models.gcn import GCN_NC  # noqa: E402
from gcn_nc import gcn_explain  # noqa: E402

__all__ = ["GCN_NC", "gcn_explain"]
