"""Mem0 baseline, following the benchmark's Mem0 path step by step.

Source: baselines/memoryagentbench/agent.py, `_initialize_mem0_agent` and `_handle_mem0_agent`.
Same memorize messages (system + filled memorize template + fixed assistant reply) passed to
`Memory.add`, same `Memory.search(query=<full query prompt>, limit=retrieve_num)`, same answer
prompt and max_tokens. `config["source"]` picks the Mem0 code:
- "bundled": the benchmark's copy (byte-identical to mem0ai 0.1.88), env envs/mem0-bundled;
- "upstream": mem0ai 2.2.1 from PyPI with its [nlp] extra, env envs/mem0-upstream.

Differences from the benchmark, all deliberate:
- The benchmark used `Memory()` defaults: OpenAI gpt-4o-mini and text-embedding-3-small. Here
  Mem0's LLM and embedder are its "openai" providers pointed at the gateway, so every Mem0 call
  goes to Claude and to the run's shared embedding model. Mem0's anthropic provider is not used:
  it sends sampling parameters that Claude rejects; the gateway drops them uniformly.
- Embedding dims come from the gateway (length of one embedded string), not Mem0's 1536 default.
- The vector store is Mem0's default provider (local Qdrant) with its path inside work_dir instead
  of /tmp/qdrant; MEM0_DIR (history DB, user-id file) is inside work_dir too, so runs never share
  state. Telemetry is off (MEM0_TELEMETRY=False), which in 2.2.1 also stops the notice fetches.
  Upstream's BM25 encoder model (fastembed Qdrant/bm25) is read from the env's pre-filled cache.
- The answer call omits `temperature` (Claude rejects sampling parameters).
- Upstream only: its API moved `limit`/`user_id` in search to `top_k`/`filters`, and search
  applies upstream's default score threshold (0.1); its add pipeline is ADD-only (no UPDATE).
"""

import importlib.metadata
import importlib.util
import os
import sys
import time
from collections import Counter
from pathlib import Path

from openai import OpenAI

from baselines.common.protocol import Gateway, Question, Task, run_agent

AGENT_NAME = "Structure_rag_mem0"
TEMPLATES_PATH = Path(__file__).resolve().parents[1] / "memoryagentbench" / "utils" / "templates.py"
API_KEY = "via-gateway"  # the gateway holds the real key; clients only need a placeholder
MEMORIZE_REPLY = "I'll make sure to add the content into the memory."
# predictions.jsonl uses Claude's stop reasons (the runner counts "max_tokens" stops)
STOP_REASON = {"stop": "end_turn", "length": "max_tokens", "tool_calls": "tool_use"}


def load_get_template():
    """The benchmark's `utils.templates.get_template`, loaded by path so the benchmark root (with its
    own top-level `utils`, `letta`, `cognee`, `mem0`) never goes on sys.path."""
    spec = importlib.util.spec_from_file_location("memoryagentbench_templates", TEMPLATES_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.get_template


def embedding_dims(client: OpenAI, model: str) -> int:
    return len(client.embeddings.create(input=["dimension probe"], model=model).data[0].embedding)


def make_memory(config: dict, gateway: Gateway, dims: int):
    work_dir = Path(config["work_dir"])
    # read by mem0 at import time, so they must be set before the first `import mem0`
    os.environ["MEM0_DIR"] = str(work_dir / "mem0_home")
    os.environ["MEM0_TELEMETRY"] = "False"
    os.environ["FASTEMBED_CACHE_PATH"] = str(Path(sys.prefix) / "fastembed_cache")  # upstream's BM25 encoder
    from mem0 import Memory

    return Memory.from_config({
        "llm": {"provider": "openai", "config": {
            "model": config["model"], "api_key": API_KEY, "openai_base_url": gateway.openai_base_url}},
        "embedder": {"provider": "openai", "config": {
            "model": config["embedding_model"], "api_key": API_KEY,
            "openai_base_url": gateway.openai_base_url, "embedding_dims": dims}},
        "vector_store": {"config": {"path": str(work_dir / "qdrant"), "embedding_model_dims": dims}},
    })


class Mem0Agent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.source = config["source"]
        if self.source not in ("bundled", "upstream"):
            raise ValueError(f"unknown Mem0 source: {self.source}")
        self.model = config["model"]
        self.answer_max_tokens = config["answer_max_tokens"]
        self.retrieve_num = config["retrieve_num"]
        self.sub_dataset = task.sub_datasets[0]
        self.user_id = f"context_0_{self.sub_dataset}"  # benchmark: context_{context_id}_{sub_dataset}
        self.get_template = load_get_template()
        self.client = OpenAI(base_url=gateway.openai_base_url, api_key=API_KEY)
        self.memory = make_memory(config, gateway, embedding_dims(self.client, config["embedding_model"]))

    def memorize(self, chunks: list[str]) -> dict:
        system = self.get_template(self.sub_dataset, "system", AGENT_NAME)
        template = self.get_template(self.sub_dataset, "memorize", AGENT_NAME)
        events: Counter = Counter()
        for chunk in chunks:
            fill = {"time_stamp": time.strftime("%Y-%m-%d %H:%M:%S")} if "{time_stamp}" in template else {}
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": template.format(context=chunk, **fill)},
                        {"role": "assistant", "content": MEMORIZE_REPLY}]
            result = self.memory.add(messages, user_id=self.user_id)
            events.update(r.get("event", "?") for r in result["results"])
        return {"mem0_source": self.source, "mem0_version": importlib.metadata.version("mem0ai"),
                "memories_stored": len(self.all_memories()), "add_events": dict(events)}

    def all_memories(self) -> list[dict]:
        if self.source == "bundled":
            return self.memory.get_all(user_id=self.user_id, limit=10**6)["results"]
        return self.memory.get_all(filters={"user_id": self.user_id}, top_k=10**6)["results"]

    def search(self, query: str) -> list[dict]:
        if self.source == "bundled":
            return self.memory.search(query=query, user_id=self.user_id, limit=self.retrieve_num)["results"]
        return self.memory.search(query=query, filters={"user_id": self.user_id}, top_k=self.retrieve_num)["results"]

    def answer(self, question: Question) -> tuple[str, dict]:
        memories = self.search(question.query)
        memories_str = "\n".join(f"- {entry['memory']}" for entry in memories)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system",
                       "content": f"You are a helpful AI. Answer the question based on query and memories.\n{memories_str}\n"},
                      {"role": "user",
                       "content": question.query + "\n\nCurrent Time: " + time.strftime("%Y-%m-%d %H:%M:%S")}],
            max_tokens=self.answer_max_tokens,
        )
        choice = response.choices[0]
        return choice.message.content or "", {"stop_reason": STOP_REASON.get(choice.finish_reason, choice.finish_reason),
                                              "memories_retrieved": len(memories)}


if __name__ == "__main__":
    run_agent(Mem0Agent)
