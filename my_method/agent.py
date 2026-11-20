"""GRAFT as a bench method: write phase over the chunk stream, then read + answer per question.

Config keys (defaults in eval/methods.py, all switchable in the UI):
    writer            "llm" (the method) | "rule" (FactConsolidation template parser; ablation)
    schema            "fixed" (schema.yaml) | "free" (the LLM invents the structure; ablation)
    schema_path       which schema file to use with "fixed"
    revisions         true: SUPERSEDE edges | false: append-only (ablation)
    shared_graph      path: load this graph instead of writing one (built and saved there on first use)
    start_graph       "empty" (from scratch) | "synthetic" (experiment D: extend a synthetic starting graph) |
                      "outside" (GRAFT layer 1: the base graph at start_graph_path, built by my_method/base_graph.py)
    retrieval         "gnn_goat" (A) | "goat_ppr" (B) | "ppr_goat_ppr" (C) | "gnn_topk" | "ppr"
    region, expand_alpha   B / C only, see my_method/retrieval.py
    explainer         edge attribution: "goat" (default) | "eig" (EiG-Search)
    gnn_checkpoint    directory written by my_method.gnn.train (needed by the gnn_* modes)
    max_facts, max_tokens, include_outdated, goat_targets, goat_topk     read-phase budget
    writer_max_tokens output cap for the writer's extraction and decision calls
    retrieval_workers CPU processes for retrieval (GOAt is per-question CPU work, so this is its speedup)
"""

import json
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


QUERY_GRAPH_PROMPT = """GRAFT-QUERY
You turn a question into a small graph pattern for a memory graph with this schema:
{schema}
Write every fact the question states or asks about as an edge (subject, relation, object). Name each entity the
question mentions exactly as it is written. For each unknown thing the question asks about or passes through, use a
placeholder ?A, ?B, ... in order. Use short relation labels in the style of stored facts, e.g. "spouse",
"country of citizenship", "official language", "author".
Example: "Where was the spouse of Pee Wee King born?" ->
{{"edges": [{{"subject": "Pee Wee King", "relation": "spouse", "object": "?A"}},
            {{"subject": "?A", "relation": "place of birth", "object": "?B"}}]}}
Return JSON only: {{"edges": [{{"subject": "...", "relation": "...", "object": "..."}}]}}"""


def parse_question_graph(llm: ClaudeLLM, schema_text: str, question: str) -> list[tuple[str, str, str]]:
    """Haiku's graph pattern for one question; [] if the reply has no usable edges (retrieval then runs as usual)."""
    from my_method.writer import parse_json
    for _ in range(2):
        try:
            reply = parse_json(llm.complete(QUERY_GRAPH_PROMPT.format(schema=schema_text), question, 512).text)
            edges = [(str(e["subject"]).strip(), str(e["relation"]).strip(), str(e["object"]).strip())
                     for e in reply.get("edges", []) if isinstance(e, dict) and all(e.get(k) for k in ("subject", "relation", "object"))]
            return edges[:8]
        except (ValueError, KeyError, TypeError):
            continue
    return []


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
        elif config.get("start_graph", "empty") == "outside":  # GRAFT layer 1: graft the documents onto a base graph
            from my_method.writer import graph_pattern
            self.store = GraphStore.load(REPO / config["start_graph_path"])
            pattern = graph_pattern(self.store, max_labels=60)
        if config["writer"] == "rule":
            self.writer = RuleWriter(revisions=config["revisions"])
        else:
            schema = Schema.load(REPO / config["schema_path"])
            self.writer = LLMWriter(self.llm, schema, config["schema"], config["revisions"], config["writer_max_tokens"],
                                   pattern)
        self.texts = TextEmbedder(load_embedder(config["embedding_model"]))
        if config.get("writer_linking") == "llm" and isinstance(self.writer, LLMWriter):  # Haiku links names to base entities
            from my_method.writer import EntityLinker
            self.writer.linker = EntityLinker(self.llm, self.store, self.texts, self.writer.stats,
                                              k=config.get("linking_candidates", 10))
        self.retriever: Retriever | None = None
        self.questions = task.questions
        self.regions: dict[int, Region] = {}

    def _writer_state(self) -> dict:
        st = getattr(self.writer, "stats", None)
        linker = getattr(self.writer, "linker", None)
        return {"ops": dict(st.ops) if st else {}, "rejected": dict(st.rejected) if st else {},
                "parse_failures": st.parse_failures if st else 0, "llm_calls": st.llm_calls if st else 0,
                "linking": dict(st.linking) if st else {},
                "link_cache": linker.cache if linker else {}, "link_log": linker.log if linker else []}

    def _restore_writer(self, meta: dict) -> None:
        from collections import Counter
        st = getattr(self.writer, "stats", None)
        if st is not None:
            st.ops, st.rejected, st.linking = Counter(meta["ops"]), Counter(meta["rejected"]), Counter(meta["linking"])
            st.parse_failures, st.llm_calls = meta["parse_failures"], meta["llm_calls"]
        linker = getattr(self.writer, "linker", None)
        if linker is not None:
            linker.cache, linker.log = meta["link_cache"], meta["link_log"]

    def memorize(self, chunks: list[str]) -> dict:
        shared = self.config.get("shared_graph")  # one built graph reused by several read variants
        shared = REPO / shared if shared else None
        if shared and Path(shared).exists():
            self.store = GraphStore.load(shared)
            print(f"[graft] reusing graph {shared}: {self.store.stats()}", flush=True)
            self.retriever = self._make_retriever()
            return {"graph": self.store.stats(), "writer": {"reused_graph": str(shared)}, "graph_file": str(shared)}
        # checkpoints (shared builds): the partial graph and the writer's state every `checkpoint_every` chunks, so a
        # job cut off by its time limit resumes from the last checkpoint instead of starting over
        every = self.config.get("checkpoint_every", 75)
        ck = Path(str(shared) + ".partial.json") if shared else None
        ck_meta = Path(str(shared) + ".partial.meta.json") if shared else None
        start = 0
        if ck and ck.exists() and ck_meta.exists():
            meta = json.loads(ck_meta.read_text())
            self.store = GraphStore.load(ck)
            start = meta["next_chunk"]
            self._restore_writer(meta)
            print(f"[graft] resuming from checkpoint at chunk {start}: {self.store.stats()}", flush=True)
        for chunk_id in range(start, len(chunks)):
            self.writer.write_chunk(chunk_id, chunks[chunk_id], self.store)
            if getattr(self.writer, "linker", None) is not None and chunk_id % 50 == 0:
                print(f"[graft] linking so far: {dict(self.writer.stats.linking)}", flush=True)
            if chunk_id % 50 == 0:
                print(f"[graft] chunk {chunk_id + 1}/{len(chunks)}: {self.store.stats()}", flush=True)
            if ck and every and (chunk_id + 1) % every == 0 and chunk_id + 1 < len(chunks):
                self.store.save(ck)
                ck_meta.write_text(json.dumps({"next_chunk": chunk_id + 1, **self._writer_state()}))
                print(f"[graft] checkpoint saved after chunk {chunk_id + 1}", flush=True)
        self.store.save(self.work_dir / "graph.json")
        linker = getattr(self.writer, "linker", None)
        if linker is not None:  # every linking decision, next to the graph (and with the shared copy)
            with open(self.work_dir / "entity_linking.jsonl", "w") as f:
                f.writelines(json.dumps(d, ensure_ascii=False) + "\n" for d in linker.log)
        if shared:
            Path(shared).parent.mkdir(parents=True, exist_ok=True)
            self.store.save(shared)
            if linker is not None:
                Path(str(shared) + ".linking.jsonl").write_text((self.work_dir / "entity_linking.jsonl").read_text())
            for p in (Path(str(shared) + ".partial.json"), Path(str(shared) + ".partial.meta.json")):
                p.unlink(missing_ok=True)  # the finished graph replaces the checkpoint
        self.retriever = self._make_retriever()
        return {"graph": self.store.stats(), "writer": self.writer.stats.as_dict(),
                "graph_file": str(self.work_dir / "graph.json")}

    def _make_retriever(self) -> Retriever:
        c = self.config
        cfg = RetrievalConfig(mode=c["retrieval"], max_facts=c["max_facts"], max_tokens=c["max_tokens"],
                              include_outdated=c["include_outdated"], goat_targets=c["goat_targets"], goat_topk=c["goat_topk"],
                              region=c.get("region", "nearest"), expand_alpha=c.get("expand_alpha", 0.5),
                              explainer=c.get("explainer", "goat"), link_embed_k=c.get("link_embed_k", 0),
                              hybrid=c.get("hybrid", False), hybrid_k=c.get("hybrid_k", 0),
                              query_graph=c.get("query_graph", False), query_match_min=c.get("query_match_min", 0.85),
                              query_linking=c.get("query_linking", "embedding"))
        model = None
        if cfg.mode not in ("ppr", "embed"):
            model, gnn_cfg = load_model(REPO / c["gnn_checkpoint"])
            if gnn_cfg["embedding_model"] != c["embedding_model"]:
                raise ValueError(f"GNN was trained with embeddings {gnn_cfg['embedding_model']}, "
                                 f"this run uses {c['embedding_model']}")
            # the GNN's training size, unless the run sets max_nodes (larger subgraphs than the GNN was trained on)
            cfg.max_nodes = c.get("max_nodes", gnn_cfg["max_nodes"])
        return Retriever(self.store, cfg, self.texts, model)

    def _retrieve_all(self, workers: int) -> None:
        """Retrieve every question in parallel on first use, so the time counts as query time."""
        global _worker_retriever
        _worker_retriever = self.retriever
        texts = [question_text(q.query) for q in self.questions]
        self._prepare_query_graphs(texts)
        # Embed every node and question here, in the parent: workers are forked, and a forked process
        # cannot use CUDA. With everything cached, workers only read vectors.
        self.texts.embed_texts([node_text(self.store, n) for n in self.store.g.nodes] + texts)
        with multiprocessing.get_context("fork").Pool(workers) as pool:
            regions = pool.map(_retrieve_in_worker, texts, chunksize=1)
        self.regions = {q.q_index: r for q, r in zip(self.questions, regions)}

    def _link_question(self, question: str, names: list[str]) -> dict:
        """Top 10 graph entities (base and documents) by name embedding per name; one Haiku call picks one or "new"."""
        import numpy as np
        from my_method.writer import LINK_PROMPT, parse_json
        r = self.retriever
        ids, vecs = r._entity_matrix()
        qv = self.texts.embed_texts(names)
        qv = qv / (np.linalg.norm(qv, axis=1, keepdims=True) + 1e-8)
        top = np.argsort(-(qv @ vecs.T), axis=1)[:, :10]
        lines, cands = [], {}
        for i, n in enumerate(names):
            cands[f"N{i + 1}"] = [ids[j] for j in top[i]]
            lines.append(f"N{i + 1}: {n}   [from the question: {question}]")
            for c, e in enumerate(cands[f"N{i + 1}"]):
                fs = self.store.facts_of_entity(e)
                ex = self.store.fact(fs[0]) if fs else None
                desc = f"{self.store.fact(e)['name']}" + (f"  (e.g. {ex['subject']} | {ex['relation']} | {ex['object']})" if ex else "")
                lines.append(f"    c{c + 1}: {desc}")
        reply = {}
        for _ in range(2):
            try:
                reply = parse_json(self.llm.complete(LINK_PROMPT, "\n".join(lines), 1024).text)
                break
            except (ValueError, KeyError):
                continue
        chosen = {str(x.get("name")): str(x.get("match", "new")) for x in reply.get("links", []) if isinstance(x, dict)}
        out = {}
        for i, n in enumerate(names):
            m = chosen.get(f"N{i + 1}", "new")
            pick = cands[f"N{i + 1}"][int(m[1:]) - 1] if m.startswith("c") and m[1:].isdigit() and 1 <= int(m[1:]) <= 10 else None
            out[n] = pick
            self.query_link_log.append({"question": question, "name": n, "candidates": [self.store.fact(e)["name"] for e in cands[f"N{i + 1}"]],
                                        "choice": m, "matched": pick})
        return out

    def _prepare_query_graphs(self, texts: list[str]) -> None:
        """query_graph option: parse the questions with Haiku here, in the parent, before workers fork."""
        if not self.retriever.cfg.query_graph:
            return
        schema = Schema.load(REPO / self.config["schema_path"]).describe()
        self.retriever.prepare_queries(texts, lambda q: parse_question_graph(self.llm, schema, q))
        if self.retriever.cfg.query_linking == "llm":  # link question entities into the graph the way the writer does
            self.query_link_log = getattr(self, "query_link_log", [])
            self.retriever.prepare_query_links(texts, self._link_question)
            with open(self.work_dir / "query_linking.jsonl", "a") as f:  # every question-entity linking decision
                f.writelines(json.dumps(d, ensure_ascii=False) + "\n" for d in self.query_link_log)
            self.query_link_log = []

    def answer(self, question: Question) -> tuple[str, dict]:
        workers = self.config.get("retrieval_workers", 1)
        if workers > 1 and not self.regions:
            self._retrieve_all(workers)
        if not self.regions and self.retriever.cfg.query_graph:
            self._prepare_query_graphs([question_text(question.query)])
        region = self.regions.get(question.q_index) or self.retriever.retrieve(question_text(question.query))
        call, memory = answer(self.llm, self.store, region, question.query, self.sub_dataset,
                              self.config["answer_max_tokens"])
        return call.text, {"stop_reason": call.stop_reason, "retrieved_text": memory,
                           "linked_entities": region.linked_entities, "region_facts": len(region.facts),
                           "subgraph_nodes": region.subgraph_nodes, "fallback": region.fallback,
                           "subgraph_text": "\n".join(self.store.fact(f)["provenance"]["span"] for f in region.subgraph_facts),
                           "fact_sources": region.sources, "query_graph": region.query_graph}


SGARAgent = GraftAgent  # old name, kept for older scripts

if __name__ == "__main__":
    run_agent(GraftAgent)
