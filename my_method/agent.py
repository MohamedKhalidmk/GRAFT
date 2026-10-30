"""SGAR as a bench method: write phase over the chunk stream, then read + answer per question.

Config keys (defaults in eval/methods.py, all switchable in the UI):
    writer            "llm" (the method) | "rule" (FactConsolidation template parser; ablation)
    schema            "fixed" (schema.yaml) | "free" (the LLM invents the structure; ablation)
    schema_path       which schema file to use with "fixed"
    revisions         true: SUPERSEDE edges | false: append-only (ablation)
    retrieval         "gnn_goat" | "gnn_topk" | "ppr"
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
from my_method.gnn.features import TextEmbedder
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


class SGARAgent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.config = config
        self.llm = ClaudeLLM(gateway.anthropic_base_url, config["model"])
        self.sub_dataset = task.sub_datasets[0]
        self.work_dir = Path(config["work_dir"])
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.store = GraphStore()
        if config["writer"] == "rule":
            self.writer = RuleWriter(revisions=config["revisions"])
        else:
            schema = Schema.load(REPO / config["schema_path"])
            self.writer = LLMWriter(self.llm, schema, config["schema"], config["revisions"], config["writer_max_tokens"])
        self.texts = TextEmbedder(load_embedder(config["embedding_model"]))
        self.retriever: Retriever | None = None
        self.questions = task.questions
        self.regions: dict[int, Region] = {}

    def memorize(self, chunks: list[str]) -> dict:
        for chunk_id, chunk in enumerate(chunks):
            self.writer.write_chunk(chunk_id, chunk, self.store)
            if chunk_id % 50 == 0:
                print(f"[sgar] chunk {chunk_id + 1}/{len(chunks)}: {self.store.stats()}", flush=True)
        self.store.save(self.work_dir / "graph.json")
        self.retriever = self._make_retriever()
        return {"graph": self.store.stats(), "writer": self.writer.stats.as_dict(),
                "graph_file": str(self.work_dir / "graph.json")}

    def _make_retriever(self) -> Retriever:
        c = self.config
        cfg = RetrievalConfig(mode=c["retrieval"], max_facts=c["max_facts"], max_tokens=c["max_tokens"],
                              include_outdated=c["include_outdated"], goat_targets=c["goat_targets"], goat_topk=c["goat_topk"])
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


if __name__ == "__main__":
    run_agent(SGARAgent)
