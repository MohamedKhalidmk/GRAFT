# Sources: goat, subgraphrag, pyg (docs/reference/REFERENCES.md)
"""Train GRAFT's node-scoring GNN (GOAt's GCN_NC: 3 GCN layers + 2 linear, 2 classes).

    python -m my_method.gnn.train --source synthetic --out results/checkpoints/gnn_synth \
        --embedding-model hash:384

Writes to --out:
    config.json     everything needed to rebuild the model and its features
    metrics.jsonl   one line per epoch (train/val loss, val answer recall@10), for the live chart
    model.pt        the weights with the best validation recall
The training and validation sets are split by world (synthetic) or by question (SubgraphRAG),
never within one graph.
"""

import argparse
import json
import random
import time
from pathlib import Path

import torch
import torch.nn.functional as F

from baselines.claude_gateway.embeddings import load_embedder
from my_method.gnn.data_subgraphrag import subgraphrag_examples
from my_method.gnn.data_synthetic import synthetic_examples
from my_method.gnn.dataset import SubgraphConfig, build_dataset
from my_method.gnn.features import TextEmbedder, feature_dim
from my_method.gnn.goat import GCN_NC

N_LAYERS = 3  # gcn_explain decomposes exactly three GCN layers
RECALL_AT = 10


def make_model(in_dim: int, hidden: int) -> GCN_NC:
    return GCN_NC(in_dim, 2, N_LAYERS, hidden)


def load_model(checkpoint_dir: str | Path, device: str = "cpu") -> tuple[GCN_NC, dict]:
    cfg = json.loads((Path(checkpoint_dir) / "config.json").read_text())
    model = make_model(cfg["in_dim"], cfg["hidden"])
    model.load_state_dict(torch.load(Path(checkpoint_dir) / "model.pt", map_location=device))
    return model.eval(), cfg


def load_groups(source: str, seed: int, synthetic_worlds: int, questions_per_world: int, subgraphrag_limit: int):
    groups = []
    if source in ("synthetic", "both"):
        groups += synthetic_examples(seed, synthetic_worlds, questions_per_world)
    if source in ("subgraphrag", "both"):
        groups += subgraphrag_examples("webqsp", "train", subgraphrag_limit // 2)
        groups += subgraphrag_examples("cwq", "train", subgraphrag_limit - subgraphrag_limit // 2)
    return groups


def full_x(data, table: torch.Tensor) -> torch.Tensor:
    """Structural features + the shared text vectors = the GNN's input."""
    return torch.cat([data.x, table[data.text_ids]], dim=1)


def answer_recall(model: GCN_NC, data, table: torch.Tensor) -> float:
    """1 if an answer node is among the RECALL_AT highest-scored nodes."""
    with torch.no_grad():
        scores = model(full_x(data, table), data.edge_index)[:, 1]
    top = torch.topk(scores, min(RECALL_AT, len(scores))).indices
    return float(data.answer_mask[top].any())


def epoch_loss(model: GCN_NC, graphs, table: torch.Tensor, optimizer=None, pos_weight: float = 1.0) -> float:
    model.train(optimizer is not None)
    weight = torch.tensor([1.0, pos_weight])
    total = 0.0
    for data in graphs:
        logits = model.fwd_base(full_x(data, table), data.edge_index)
        loss = F.cross_entropy(logits, data.y, weight=weight)
        if optimizer is not None:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        total += float(loss)
    return total / max(1, len(graphs))


def train(args) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    texts = TextEmbedder(load_embedder(args.embedding_model))
    sub_cfg = SubgraphConfig(max_nodes=args.max_nodes)
    print(f"[train] building data from {args.source} ...", flush=True)
    groups = load_groups(args.source, args.seed, args.synthetic_worlds, args.questions_per_world,
                         args.subgraphrag_limit)
    random.shuffle(groups)
    n_val = max(1, int(len(groups) * args.val_fraction))
    val = [d for g in build_dataset(groups[:n_val], texts, sub_cfg) for d in g]
    trn = [d for g in build_dataset(groups[n_val:], texts, sub_cfg) for d in g]
    table = torch.from_numpy(texts.table())
    texts.cache.clear()
    positives = sum(int(d.y.sum()) for d in trn)
    nodes = sum(len(d.y) for d in trn)
    pos_weight = min(50.0, (nodes - positives) / max(1, positives))
    print(f"[train] {len(trn)} train / {len(val)} val graphs, positive rate {positives / max(1, nodes):.3f}",
          flush=True)

    cfg = {"source": args.source, "embedding_model": args.embedding_model, "in_dim": feature_dim(texts.dim),
           "hidden": args.hidden, "max_nodes": args.max_nodes, "epochs": args.epochs,
           "lr": args.lr, "seed": args.seed, "n_train": len(trn), "n_val": len(val), "pos_weight": pos_weight}
    (out / "config.json").write_text(json.dumps(cfg, indent=2))
    model = make_model(cfg["in_dim"], args.hidden)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    best = -1.0
    with open(out / "metrics.jsonl", "w") as log:
        for epoch in range(1, args.epochs + 1):
            start = time.time()
            random.shuffle(trn)
            train_loss = epoch_loss(model, trn, table, optimizer, pos_weight)
            val_loss = epoch_loss(model, val, table, None, pos_weight)
            model.eval()
            recall = sum(answer_recall(model, d, table) for d in val) / max(1, len(val))
            row = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss,
                   f"val_answer_recall@{RECALL_AT}": recall, "seconds": time.time() - start}
            log.write(json.dumps(row) + "\n")
            log.flush()
            print(f"[train] epoch {epoch}: train {train_loss:.4f} val {val_loss:.4f} recall@{RECALL_AT} {recall:.3f}",
                  flush=True)
            if recall > best:
                best = recall
                torch.save(model.state_dict(), out / "model.pt")
    print(f"[train] best val recall@{RECALL_AT} {best:.3f}; saved {out / 'model.pt'}", flush=True)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["synthetic", "subgraphrag", "both"], default="synthetic")
    p.add_argument("--out", required=True)
    p.add_argument("--embedding-model", default="hash:384")
    p.add_argument("--synthetic-worlds", type=int, default=40)
    p.add_argument("--questions-per-world", type=int, default=30)
    p.add_argument("--subgraphrag-limit", type=int, default=1000)
    p.add_argument("--max-nodes", type=int, default=400)
    p.add_argument("--hidden", type=int, default=64)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--val-fraction", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=0)
    train(p.parse_args())


if __name__ == "__main__":
    main()
