"""GRAFT as a bench method: write phase over the chunk stream, then read + answer per question.

Config keys (defaults in eval/methods.py, all switchable in the UI):
    writer            "llm" (the method) | "rule" (FactConsolidation template parser; ablation)
    schema            "fixed" (schema.yaml) | "free" (the LLM invents the structure; ablation)
    schema_path       which schema file to use with "fixed"
    revisions         true: SUPERSEDE edges | false: append-only (ablation)
    shared_graph      path: load this graph instead of writing one (built and saved there on first use)
    start_graph       "empty" (from scratch) | "synthetic" (experiment D: extend a synthetic starting graph)
    retrieval         "gnn_goat" (A) | "goat_ppr" (B) | "ppr_goat_ppr" (C) | "gnn_topk" | "ppr"
    region, expand_alpha   B / C only, see my_method/retrieval.py
    explainer         edge attribution: "goat" (default) | "eig" (EiG-Search)
    gnn_checkpoint    directory written by my_method.gnn.train (needed by the gnn_* modes)
    max_facts, max_tokens, include_outdated, goat_targets, goat_topk     read-phase budget
    writer_max_tokens output cap for the writer's extraction and decision calls
    retrieval_workers CPU processes for retrieval (GOAt is per-question CPU work, so this is its speedup)
"""

import multiprocessing
from pathlib import Path

import torch

from baselines.claude_gateway.embeddings import load_embedder
from baselines.claude_llm import ClaudeLLM
from baselines.common.protocol import Gateway, Question, Task, run_agent
from eval.methods import REPO
from my_method.answer import answer
from my_method.gnn.features import TextEmbedder, node_text
from my_method.gnn.train import load_model
from my_method.graph_store import GraphStore
from my_method.retrieval import Region, RetrievalConfig, Retriever
from my_method.schema import Schema
from my_method.writer import LLMWriter, RuleWriter


_worker_retriever: Retriever | None = None  # set before forking, read in each worker


def _retrieve_in_worker(question: str) -> Region:
    torch.set_num_threads(1)
    return _worker_retriever.retrieve(question)


def question_text(query: str) -> str:
    """The question inside the benchmark's FactConsolidation query prompt."""
    return query.rsplit("Based on the provided Knowledge Pool,", 1)[-1].rsplit("Answer:", 1)[0].strip()


class GraftAgent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.config = config
        self.llm = ClaudeLLM(gateway.anthropic_base_url, config["model"])
        self.sub_dataset = task.sub_datasets[0]
        self.work_dir = Path(config["work_dir"])
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.store = GraphStore()
        pattern = ""
        if config.get("start_graph", "empty") == "synthetic":  # experiment D: extend a ready-made graph
            from my_method.gnn.data_synthetic import synthetic_start_graph
            from my_method.writer import graph_pattern
            self.store = synthetic_start_graph(config.get("start_graph_seed", 7))
            pattern = graph_pattern(self.store)
        if config["writer"] == "rule":
            self.writer = RuleWriter(revisions=config["revisions"])
        else:
            schema = Schema.load(REPO / config["schema_path"])
            self.writer = LLMWriter(self.llm, schema, config["schema"], config["revisions"], config["writer_max_tokens"],
                                   pattern)
        self.texts = TextEmbedder(load_embedder(config["embedding_model"]))
        self.retriever: Retriever | None = None
        self.questions = task.questions
        self.regions: dict[int, Region] = {}

    def memorize(self, chunks: list[str]) -> dict:
        shared = self.config.get("shared_graph")  # one built graph reused by several read variants
        shared = REPO / shared if shared else None
        if shared and Path(shared).exists():
            self.store = GraphStore.load(shared)
            print(f"[graft] reusing graph {shared}: {self.store.stats()}", flush=True)
            self.retriever = self._make_retriever()
            return {"graph": self.store.stats(), "writer": {"reused_graph": str(shared)}, "graph_file": str(shared)}
        for chunk_id, chunk in enumerate(chunks):
            self.writer.write_chunk(chunk_id, chunk, self.store)
            if chunk_id % 50 == 0:
                print(f"[graft] chunk {chunk_id + 1}/{len(chunks)}: {self.store.stats()}", flush=True)
        self.store.save(self.work_dir / "graph.json")
        if shared:
            Path(shared).parent.mkdir(parents=True, exist_ok=True)
            self.store.save(shared)
        self.retriever = self._make_retriever()
        return {"graph": self.store.stats(), "writer": self.writer.stats.as_dict(),
                "graph_file": str(self.work_dir / "graph.json")}

    def _make_retriever(self) -> Retriever:
        c = self.config
        cfg = RetrievalConfig(mode=c["retrieval"], max_facts=c["max_facts"], max_tokens=c["max_tokens"],
                              include_outdated=c["include_outdated"], goat_targets=c["goat_targets"], goat_topk=c["goat_topk"],
                              region=c.get("region", "nearest"), expand_alpha=c.get("expand_alpha", 0.5),
                              explainer=c.get("explainer", "goat"), link_embed_k=c.get("link_embed_k", 0),
                              hybrid=c.get("hybrid", False))
        model = None
        if cfg.mode != "ppr":
            model, gnn_cfg = load_model(REPO / c["gnn_checkpoint"])
            if gnn_cfg["embedding_model"] != c["embedding_model"]:
                raise ValueError(f"GNN was trained with embeddings {gnn_cfg['embedding_model']}, "
                                 f"this run uses {c['embedding_model']}")
            cfg.max_nodes = gnn_cfg["max_nodes"]
        return Retriever(self.store, cfg, self.texts, model)

    def _retrieve_all(self, workers: int) -> None:
        """Retrieve every question in parallel on first use, so the time counts as query time."""
        global _worker_retriever
        _worker_retriever = self.retriever
        texts = [question_text(q.query) for q in self.questions]
        # Embed every node and question here, in the parent: workers are forked, and a forked process
        # cannot use CUDA. With everything cached, workers only read vectors.
        self.texts.embed_texts([node_text(self.store, n) for n in self.store.g.nodes] + texts)
        with multiprocessing.get_context("fork").Pool(workers) as pool:
            regions = pool.map(_retrieve_in_worker, texts, chunksize=1)
        self.regions = {q.q_index: r for q, r in zip(self.questions, regions)}

    def answer(self, question: Question) -> tuple[str, dict]:
        workers = self.config.get("retrieval_workers", 1)
        if workers > 1 and not self.regions:
            self._retrieve_all(workers)
        region = self.regions.get(question.q_index) or self.retriever.retrieve(question_text(question.query))
        call, memory = answer(self.llm, self.store, region, question.query, self.sub_dataset,
                              self.config["answer_max_tokens"])
        return call.text, {"stop_reason": call.stop_reason, "retrieved_text": memory,
                           "linked_entities": region.linked_entities, "region_facts": len(region.facts),
                           "subgraph_nodes": region.subgraph_nodes, "fallback": region.fallback}


SGARAgent = GraftAgent  # old name, kept for older scripts

if __name__ == "__main__":
    run_agent(GraftAgent)
