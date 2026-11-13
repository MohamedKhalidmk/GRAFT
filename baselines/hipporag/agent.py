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
- config "cap_answer: true" caps HippoRAG's answer call (and only that call) at the run's
  answer_max_tokens, like every other method; its NER, triple and filter calls keep their lengths.
- config "shared_index: <path>" puts save_dir there so several runs (e.g. two answer limits) share
  one index. HippoRAG skips chunks it has already indexed and serves repeated LLM calls (the fact
  filter) from its own cache, so later runs pay only for new answer calls. The memorize template
  stamps the current time into every chunk, which would make every run look like new text, so the
  first run's time stamp is stored in the shared folder and reused.
- config "json_openie: true" sends HippoRAG's own configured response_format (json_object, its
  BaseConfig default) with its OpenIE calls (NER and triples) only. The bundled OpenAI client never
  forwards that setting; GPT-4o-mini returned JSON anyway, but Claude often answers the benchmark's
  dialogue-shaped chunks conversationally ("Understood. I've noted the facts..."), which leaves every
  chunk with no entities. The gateway turns json_object into Claude's JSON-only instruction. The
  response cache does not key on response_format, so use a fresh shared_index with it.
- config "json_openie: schema" goes one step further: each OpenIE call sends a strict JSON schema
  (NER: {"named_entities": [str]}; triples: {"triples": [[str]]}), which the gateway turns into
  Claude's native structured output, so the reply is always JSON of the shape HippoRAG parses. A
  written JSON instruction alone was not enough: Claude still answered the dialogue-shaped chunks
  conversationally. HippoRAG's prompts and parsers are unchanged.
- When graph search ends with all-zero (or NaN) node weights, the bundled HippoRAG raises
  AssertionError ("No phrases found in the graph") and the whole run stops. Those questions fall
  back to HippoRAG's own dense passage retrieval (the same fallback HippoRAG uses when its filter
  leaves no facts), and are counted in the prediction row as graph_fallback.
- vllm is only used by HippoRAG's offline-OpenIE mode but is imported at module level; when it
  is not installed (macOS, CPU hosts) a stub that raises on use takes its place.
- upstream only: the benchmark's copy extracts the question after "Now Answer the Question:" for
  retrieval inside `retrieve()` while QA still sees the full prompt. Upstream `retrieve()` uses
  the query as given, so the same extraction happens here and the full prompt is put back as the
  QA question, which reproduces the bundled behaviour exactly.
"""

import importlib.util
import json
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


OPENIE_SCHEMAS = {
    "ner": {"type": "object", "properties": {"named_entities": {"type": "array", "items": {"type": "string"}}},
            "required": ["named_entities"], "additionalProperties": False},
    "triples": {"type": "object", "properties": {"triples": {"type": "array", "items": {
        "type": "array", "items": {"type": "string"}}}}, "required": ["triples"], "additionalProperties": False},
}


class HippoRAGAgent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.source = config["source"]
        self.retrieve_num = config["retrieve_num"]
        self.sub_dataset = task.sub_datasets[0]
        embedding = config.get("hipporag_embedding", "gateway")
        if embedding not in ("gateway", "nv-embed-v2"):
            raise ValueError(f"unknown hipporag_embedding {embedding!r}")
        self.answer_cap = config["answer_max_tokens"] if config.get("cap_answer") else None
        self.json_openie = config.get("json_openie") or False
        shared = config.get("shared_index")
        self.save_dir = Path(shared) if shared else Path(config["work_dir"]) / "hipporag"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        os.environ["OPENAI_API_KEY"] = "sk-gateway"  # placeholder; never a real key
        hipporag = import_hipporag(self.source, embedding)
        kwargs = {"save_dir": str(self.save_dir), "llm_model_name": config["model"],
                  "llm_base_url": gateway.openai_base_url,
                  "embedding_model_name": NV_EMBED if embedding == "nv-embed-v2" else config["embedding_model"],
                  "embedding_base_url": gateway.openai_base_url}
        if self.source == "bundled":
            kwargs |= {"llm_api_key": "sk-gateway", "embedding_api_key": "sk-gateway"}
        self.rag = hipporag.HippoRAG(**kwargs)
        self.fallback = False
        graph_search = self.rag.graph_search_with_fact_entities

        def graph_search_or_dense(query, *args, **kwargs):
            try:
                return graph_search(query, *args, **kwargs)
            except AssertionError:
                self.fallback = True
                return self.rag.dense_passage_retrieval(query)
        self.rag.graph_search_with_fact_entities = graph_search_or_dense

    def memorize(self, chunks: list[str]) -> dict:
        template = load_benchmark_templates().get_template(self.sub_dataset, "memorize", AGENT_NAME)
        stamp_file = self.save_dir / "memorize_time_stamp.json"
        if stamp_file.exists():  # shared index: same chunk text as the run that built it
            stamps = json.loads(stamp_file.read_text())
        else:
            stamps = [time.strftime("%Y-%m-%d %H:%M:%S") for _ in chunks]
            stamp_file.write_text(json.dumps(stamps))
        if len(stamps) != len(chunks):
            raise RuntimeError(f"{stamp_file} has {len(stamps)} stamps for {len(chunks)} chunks")
        docs = [template.format(context=c, time_stamp=t) for c, t in zip(chunks, stamps)]
        params = self.rag.llm_model.llm_config.generate_params
        response_format = getattr(self.rag.global_config, "response_format", None)
        llm = self.rag.llm_model
        if self.json_openie == "schema":  # OpenIE only; the instance override is removed before any answer
            original = llm.infer

            def infer_with_schema(*args, **kwargs):
                system = next((m["content"] for m in kwargs.get("messages", []) if m["role"] == "system"), "")
                schema = OPENIE_SCHEMAS["ner" if "extract named entities" in system else "triples"]
                return original(*args, response_format={"type": "json_schema", "json_schema": {
                    "name": "openie", "strict": True, "schema": schema}}, **kwargs)
            llm.infer = infer_with_schema
        elif self.json_openie and response_format:
            params["response_format"] = response_format
        try:
            self.rag.index(docs=docs)
        finally:
            params.pop("response_format", None)
            llm.__dict__.pop("infer", None)
        return self.stats()

    def stats(self) -> dict:
        return {"n_passages": len(self.rag.chunk_embedding_store.get_all_ids()),
                "n_entities": len(self.rag.entity_embedding_store.get_all_ids()),
                "n_facts": len(self.rag.fact_embedding_store.get_all_ids()),
                "graph_nodes": self.rag.graph.vcount(), "graph_edges": self.rag.graph.ecount()}

    def answer(self, question: Question) -> tuple[str, dict]:
        self.fallback = False
        if self.source == "bundled":
            solutions, _ = self.rag.retrieve(queries=[question.query], num_to_retrieve=self.retrieve_num)
        else:
            solutions = self.rag.retrieve(queries=[retrieval_query(question.query)],
                                          num_to_retrieve=self.retrieve_num)
            solutions[0].question = question.query
        params = self.rag.llm_model.llm_config.generate_params
        default = {k: params[k] for k in ("max_completion_tokens", "seed")}
        if self.answer_cap:  # only the answer call; retrieve() and its filter already ran
            params["max_completion_tokens"] = self.answer_cap
            # HippoRAG's response cache keys on messages, model, seed and temperature, not on the
            # length limit, so in a shared index one limit's answers would be served to another.
            # The seed is part of the key and the gateway drops it, so it separates the limits.
            params["seed"] = self.answer_cap
        try:
            qa_results = self.rag.rag_qa(solutions)
        finally:
            params.update(default)
        return qa_results[0][0].answer, {"n_retrieved": len(solutions[0].docs), "graph_fallback": self.fallback,
                                         "qa_response": qa_results[1][0]}


if __name__ == "__main__":
    run_agent(HippoRAGAgent)
