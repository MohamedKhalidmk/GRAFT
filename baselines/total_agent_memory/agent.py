"""total-agent-memory (TAM) baseline, run through the benchmark's own handler.

Source: baselines/memoryagentbench/methods/total_agent_memory.py,
`initialize_total_agent_memory_agent` and `handle_total_agent_memory_agent`, called unmodified on
a stand-in for the benchmark's AgentWrapper (baselines/knowl/bench_shim.py). TAM itself is the
PyPI package total-agent-memory==14.5.1 (the version the benchmark pins), installed in
envs/total-agent-memory and spoken to over MCP stdio as its `total-agent-memory` server.

Settings: `tam_supersede` (default true) and `tam_show_recorded` (default true) are the
supersede arm, configs/agent_conf/RAG_Agents/gpt-4o-mini/TotalAgentMemory_gpt-4o-mini-supersede.yaml.
`tam_supersede: false` gives TAM's default search-path arm (TotalAgentMemory_gpt-4o-mini.yaml), and
additionally `tam_show_recorded: false` the no-dates ablation.

Deviations from the benchmark's handling:
- Reader: Claude via the gateway instead of gpt-4o-mini; temperature 0.7 is dropped by the gateway,
  and the answer is capped at `answer_max_tokens` (see bench_shim.BENCH_MODEL).
- `tam_supersede` defaults to true here (the benchmark's code defaults to false): this bench
  registers TAM as a supersede-style memory, so an unset key selects that published arm.
- Embeddings: TAM's own FastEmbed model in its default fast mode
  (paraphrase-multilingual-MiniLM-L12-v2, plus its small ms-marco reranker), not the gateway's
  shared model. The vectors are internal to TAM's store, and the benchmark withholds every
  setting that would change them, so the published arm used exactly this. Weights are cached in
  the env (HF_HOME / FASTEMBED_CACHE_PATH), which the handler passes through to TAM.
- Ingest timing: `flush` is called at the end of memorize(), so the write cost lands in the build
  phase. The handler calls the same idempotent flush at the first question, where it is a no-op.
- State: TAM's store (TAM_MEMORY_DIR, a tempfile.mkdtemp) lives under `work_dir`.
- TAM receives no API keys and runs with MEMORY_LLM_ENABLED=false, exactly as the handler sets it,
  so it makes no LLM or embedding calls of its own over the network.
"""

import os
import sys
import tempfile
from pathlib import Path

from baselines.common.protocol import Gateway, Question, Task, run_agent
from baselines.knowl.bench_shim import BenchAgent

from methods.total_agent_memory import (  # noqa: E402 (bench path)
    handle_total_agent_memory_agent,
    initialize_total_agent_memory_agent,
)

AGENT_NAME = "Agentic_memory_total_agent_memory"  # selects the benchmark's agentic-memory prompts
ENV_DIR = Path(sys.prefix)
MODEL_CACHE = ENV_DIR / "models"
PUBLISHED_ARM = {"tam_supersede": True, "tam_show_recorded": True}


class TotalAgentMemoryAgent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        self.bench = BenchAgent(AGENT_NAME, task.sub_datasets[0], gateway, config["answer_max_tokens"])
        _prepare_environment(Path(config["work_dir"]))
        initialize_total_agent_memory_agent(self.bench, {**PUBLISHED_ARM, **config})

    def memorize(self, chunks: list[str]) -> dict:
        for chunk in chunks:
            handle_total_agent_memory_agent(self.bench, chunk, True, None, 0)
        memory = self.bench.tam_memory
        return {**memory.flush(), "tam_supersede": memory.supersede, "tam_show_recorded": memory.show_recorded}

    def answer(self, question: Question) -> tuple[str, dict]:
        response = handle_total_agent_memory_agent(self.bench, question.query, False, question.q_index, 0)
        return response["output"], {"input_len": response["input_len"], "output_len": response["output_len"]}


def _prepare_environment(work_dir: Path) -> None:
    """Run this env's TAM server, keep its store under work_dir and its model weights in the env."""
    tmp = work_dir / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(tmp)
    os.environ.update({
        "TAM_COMMAND": str(ENV_DIR / "bin" / "total-agent-memory"),
        "TMPDIR": str(tmp),
        "HF_HOME": str(MODEL_CACHE / "hf"),
        "FASTEMBED_CACHE_PATH": str(MODEL_CACHE),
    })


if __name__ == "__main__":
    run_agent(TotalAgentMemoryAgent)
