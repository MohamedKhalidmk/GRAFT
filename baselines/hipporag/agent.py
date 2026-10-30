"""HippoRAG-v2 baseline, following the benchmark's HippoRAG path step by step.

Source: baselines/memoryagentbench/agent.py, `_handle_rag_agent` (memorize: every chunk wrapped in
the memorize template) and `_handle_hippo_rag` (query: `index(docs)` once, then per question
`retrieve(queries=[message], num_to_retrieve=retrieve_num)`, `rag_qa(retrieval_results)` and the
answer `qa_results[0][0].answer`). The question prompt is the benchmark's full rag_agent query.

config["source"] picks the HippoRAG code:
    bundled   the benchmark's modified copy (methods/hipporag, 2.0.0a3-era), which
              envs/hipporag-bundled exposes as the top-level package `hipporag`
    upstream  hipporag 2.0.0a4 from PyPI (envs/hipporag-upstream)

Differences from the benchmark, and why:
- LLM: HippoRAG's own OpenAI client is pointed at the gateway, so every call is answered by
  Claude. HippoRAG's prompts and generation lengths are unchanged (max_new_tokens 2048 for NER,
  triples and QA; 512 for the fact filter); config["answer_max_tokens"] is not used. The gateway
  drops temperature and seed. The API key is a placeholder: the gateway needs none.
- Embeddings: by default HippoRAG's own OpenAI-compatible embedding class (bundled:
  OpenAI_Compatible_EmbeddingModel, upstream: OpenAIEmbeddingModel) calls the gateway's
  /v1/embeddings, which serves the run's shared config["embedding_model"]. HippoRAG picks its
  embedding class from substrings of the model name, so that lookup is bypassed and a name such
  as "NV-Embed-v2" or "contriever" cannot load a local model. The benchmark (and the paper) used
  NV-Embed-v2 in-process; config "hipporag_embedding: nv-embed-v2" restores that (GPU only).
- HippoRAG's save_dir is config["work_dir"] instead of ./outputs/rag_retrieved/...
- vllm is only used by HippoRAG's offline-OpenIE mode but is imported at module level; when it
  is not installed (macOS, CPU hosts) a stub that raises on use takes its place.
- upstream only: the benchmark's copy extracts the question after "Now Answer the Question:" for
  retrieval inside `retrieve()` while QA still sees the full prompt. Upstream `retrieve()` uses
  the query as given, so the same extraction happens here and the full prompt is put back as the
  QA question, which reproduces the bundled behaviour exactly.
"""

import importlib.util
import os
import re
import sys
import time
import types
from pathlib import Path

from baselines.common.protocol import Gateway, Question, Task, run_agent

AGENT_NAME = "Structure_rag_hippo_rag_v2"  # selects the benchmark's rag_agent prompts
BENCH_DIR = Path(__file__).resolve().parent.parent / "memoryagentbench"
NV_EMBED = "nvidia/NV-Embed-v2"
GATEWAY_EMBEDDING_CLASS = {"bundled": "OpenAI_Compatible_EmbeddingModel", "upstream": "OpenAIEmbeddingModel"}


def load_benchmark_templates() -> types.ModuleType:
    """The benchmark's utils/templates.py, loaded by path so its top-level `utils` stays off sys.path."""
    spec = importlib.util.spec_from_file_location("memoryagentbench_templates", BENCH_DIR / "utils" / "templates.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stub_vllm_if_missing() -> None:
    if importlib.util.find_spec("vllm") is not None:
        return

    def unavailable(*args, **kwargs):
        raise RuntimeError("vllm is not installed; HippoRAG's offline-OpenIE mode is unavailable")

    stub = types.ModuleType("vllm")
    stub.LLM = stub.SamplingParams = unavailable
    sys.modules["vllm"] = stub


def import_hipporag(source: str, embedding: str):
    """Import the env's `hipporag` package; in gateway mode, force its OpenAI-compatible embedder."""
    stub_vllm_if_missing()
    import hipporag

    origin = os.path.realpath(hipporag.__path__[0])
    expected = os.path.realpath(BENCH_DIR / "methods" / "hipporag")
    if (origin == expected) != (source == "bundled"):
        raise RuntimeError(f"source={source!r} but `hipporag` resolves to {origin}")
    if embedding == "gateway":
        import hipporag.embedding_model as embedding_models
        embedder_class = getattr(embedding_models, GATEWAY_EMBEDDING_CLASS[source])
        sys.modules["hipporag.HippoRAG"]._get_embedding_model_class = lambda embedding_model_name: embedder_class
    return hipporag


def retrieval_query(message: str) -> str:
    """Same patterns as the bundled HippoRAG.retrieve (and agent.py `_extract_retrieval_query`)."""
    for pattern in (r"Now Answer the Question:\s*(.*)", r"Here is the conversation:\s*(.*)"):
        match = re.search(pattern, message, re.DOTALL)
        if match:
            return "".join(match.groups())
    return message


class HippoRAGAgent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.source = config["source"]
        self.retrieve_num = config["retrieve_num"]
        self.sub_dataset = task.sub_datasets[0]
        embedding = config.get("hipporag_embedding", "gateway")
        if embedding not in ("gateway", "nv-embed-v2"):
            raise ValueError(f"unknown hipporag_embedding {embedding!r}")
        os.environ["OPENAI_API_KEY"] = "sk-gateway"  # placeholder; never a real key
        hipporag = import_hipporag(self.source, embedding)
        kwargs = {"save_dir": str(Path(config["work_dir"]) / "hipporag"), "llm_model_name": config["model"],
                  "llm_base_url": gateway.openai_base_url,
                  "embedding_model_name": NV_EMBED if embedding == "nv-embed-v2" else config["embedding_model"],
                  "embedding_base_url": gateway.openai_base_url}
        if self.source == "bundled":
            kwargs |= {"llm_api_key": "sk-gateway", "embedding_api_key": "sk-gateway"}
        self.rag = hipporag.HippoRAG(**kwargs)

    def memorize(self, chunks: list[str]) -> dict:
        template = load_benchmark_templates().get_template(self.sub_dataset, "memorize", AGENT_NAME)
        docs = [template.format(context=c, time_stamp=time.strftime("%Y-%m-%d %H:%M:%S")) for c in chunks]
        self.rag.index(docs=docs)
        return self.stats()

    def stats(self) -> dict:
        return {"n_passages": len(self.rag.chunk_embedding_store.get_all_ids()),
                "n_entities": len(self.rag.entity_embedding_store.get_all_ids()),
                "n_facts": len(self.rag.fact_embedding_store.get_all_ids()),
                "graph_nodes": self.rag.graph.vcount(), "graph_edges": self.rag.graph.ecount()}

    def answer(self, question: Question) -> tuple[str, dict]:
        if self.source == "bundled":
            solutions, _ = self.rag.retrieve(queries=[question.query], num_to_retrieve=self.retrieve_num)
        else:
            solutions = self.rag.retrieve(queries=[retrieval_query(question.query)],
                                          num_to_retrieve=self.retrieve_num)
            solutions[0].question = question.query
        qa_results = self.rag.rag_qa(solutions)
        return qa_results[0][0].answer, {"n_retrieved": len(solutions[0].docs),
                                         "qa_response": qa_results[1][0]}


if __name__ == "__main__":
    run_agent(HippoRAGAgent)
