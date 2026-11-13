"""Time GOAt on the WHOLE 262K memory graph for one question (experiment B, region="full").

    python scripts/fir/time_goat_full.py [--question 73] [--device cpu|cuda]

Builds the graph with the rule writer (the same facts and SUPERSEDES edges the fake-mode LLM writer
produces), links one MH question, builds features for every node, runs the GCN and then GOAt's
gcn_explain. Prints wall time per stage, peak process memory, and peak GPU memory if CUDA is used.
"""

import argparse
import json
import resource
import time

import torch

from baselines.claude_gateway.embeddings import load_embedder
from eval.benchmark import build_task
from my_method.agent import question_text
from my_method.gnn.explain import edge_attributions
from my_method.gnn.features import TextEmbedder, build_features
from my_method.gnn.train import load_model
from my_method.graph_store import GraphStore
from my_method.retrieval import RetrievalConfig, Retriever
from my_method.writer import RuleWriter


def peak_rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 2  # Linux reports KB


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--question", type=int, default=73)
    p.add_argument("--device", default="cpu")
    p.add_argument("--checkpoint", default="results/checkpoints/gnn_bge_400w")
    args = p.parse_args()
    out: dict = {}
    t0 = time.time()
    task, _ = build_task("262k", ["mh"], 512, "Structure_rag_sgar", None)
    store, writer = GraphStore(), RuleWriter(revisions=True)
    for i, chunk in enumerate(task.chunks):
        writer.write_chunk(i, chunk, store)
    out["graph"] = store.stats() | {"nodes": store.g.number_of_nodes()}
    out["build_s"] = round(time.time() - t0, 1)
    model, cfg = load_model(args.checkpoint)
    texts = TextEmbedder(load_embedder(cfg["embedding_model"]))
    question = question_text(task.questions[args.question].query)
    linked = Retriever(store, RetrievalConfig(mode="ppr"), texts).link(question)
    nodes = store.entities() + store.facts()
    t = time.time()
    sub = build_features(store, nodes, linked, question, texts)
    out["features_s"] = round(time.time() - t, 1)
    out["edges_undirected"] = int(sub.edge_index.shape[1] // 2)
    dev = torch.device(args.device)
    model = model.to(dev)
    x, ei = sub.x.to(dev), sub.edge_index.to(dev)
    if dev.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    t = time.time()
    with torch.no_grad():
        scores = model(x, ei)[:, 1]
    out["gnn_s"] = round(time.time() - t, 2)
    t = time.time()
    edge_attributions(model, x, ei, 12)
    out["goat_s"] = round(time.time() - t, 1)
    out["peak_rss_gb"] = round(peak_rss_gb(), 2)
    if dev.type == "cuda":
        out["peak_gpu_gb"] = round(torch.cuda.max_memory_allocated() / 1024 ** 3, 2)
    out |= {"question": args.question, "linked": linked, "device": args.device, "top_score": float(scores.max())}
    print(json.dumps(out, indent=1), flush=True)


if __name__ == "__main__":
    main()
