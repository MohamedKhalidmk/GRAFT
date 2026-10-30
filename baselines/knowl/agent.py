"""Knowl baseline (supersede-at-write memory), run through the benchmark's own handler.

Source: baselines/memoryagentbench/methods/knowl.py, `initialize_knowl_agent` and
`handle_knowl_agent`, called unmodified on a stand-in for the benchmark's AgentWrapper
(bench_shim.py). Knowl itself (github.com/dat999zx/knowl, TypeScript + SQLite) runs as the
benchmark's Node bridge, `benchmarks/memoryagentbench/mab-bridge.ts`, built by
scripts/setup/knowl.sh into envs/knowl together with its own Node runtime.

Settings: `knowl_supersede` (default true) and `knowl_vector` (default true) are the published
arm, configs/agent_conf/RAG_Agents/gpt-4o-mini/Knowl_gpt-4o-mini.yaml; `knowl_supersede: false`
is the ablation arm.

Deviations from the benchmark's handling:
- Reader: Claude via the gateway instead of gpt-4o-mini; temperature 0.7 is dropped by the gateway,
  and the answer is capped at `answer_max_tokens` (see bench_shim.BENCH_MODEL).
- Knowl version: pinned to v5.6.0, the release of 2026-08-19, the day the method was contributed.
- Embeddings: Knowl's own local embedder, not the gateway's shared model. Its vectors, profile
  fingerprint and relevance floor are internal to Knowl's store and ranker, so swapping the model
  would measure a different system. Model: the `granite-small-en-r2` preset (52 MB q8 ONNX), the
  default `knowl init` wrote at that release and the one Knowl's own FC results record.
- Project config: the bridge reads its embedding preset from `.knowl/config.json` in the Knowl
  checkout, which is gitignored upstream. We write one per run under `work_dir` holding only that
  preset and a model cache inside the env.
- Ingest timing: `flush` is called at the end of memorize(), so the write cost lands in the build
  phase. The handler calls the same idempotent flush at the first question, where it is a no-op.
- The `KNOWL_SUPERSEDE` and `KNOWL_MAB_READER_LAYOUT` environment overrides are cleared, so the
  arm and the reader layout come from the config alone (default layout = the benchmark's RAG one).
- State: the bridge's temp store (os.tmpdir()) and KNOWL_HOME live under `work_dir`.
"""

import atexit
import json
import os
import sys
from pathlib import Path

from baselines.common.protocol import Gateway, Question, Task, run_agent
from baselines.knowl.bench_shim import BenchAgent

from methods.knowl import handle_knowl_agent, initialize_knowl_agent  # noqa: E402 (bench path)

AGENT_NAME = "Agentic_memory_knowl"  # selects the benchmark's agentic-memory prompts
ENV_DIR = Path(sys.prefix)
BRIDGE = ENV_DIR / "src" / "knowl" / ".benchmark-dist" / "mab-bridge.js"
MODEL_CACHE = ENV_DIR / "models"
EMBEDDING_PRESET = "granite-small-en-r2"


class KnowlAgent:
    def __init__(self, config: dict, gateway: Gateway, task: Task):
        work_dir = Path(config["work_dir"])
        self.bench = BenchAgent(AGENT_NAME, task.sub_datasets[0], gateway, config["answer_max_tokens"])
        _prepare_environment(work_dir)
        initialize_knowl_agent(self.bench, config)
        atexit.register(self.bench.knowl.close)

    def memorize(self, chunks: list[str]) -> dict:
        for chunk in chunks:
            handle_knowl_agent(self.bench, chunk, True, None, 0)
        stats = self.bench.knowl.flush()
        return {key: stats[key] for key in ("facts", "supersededAtWrite", "activeAfterIngest")}

    def answer(self, question: Question) -> tuple[str, dict]:
        response = handle_knowl_agent(self.bench, question.query, False, question.q_index, 0)
        return response["output"], {"input_len": response["input_len"], "output_len": response["output_len"]}


def _prepare_environment(work_dir: Path) -> None:
    """Point the bridge at this env's Node, a per-run project config, and per-run state dirs."""
    if not BRIDGE.exists():
        raise SystemExit(f"Knowl bridge not built: {BRIDGE} (run scripts/setup/knowl.sh)")
    project = work_dir / "knowl-project"
    (project / ".knowl").mkdir(parents=True, exist_ok=True)
    vector = {"enabled": True, "provider": "local", "preset": EMBEDDING_PRESET, "cacheDir": str(MODEL_CACHE)}
    (project / ".knowl" / "config.json").write_text(json.dumps({"search": {"vector": vector}}, indent=2))
    tmp = work_dir / "tmp"
    tmp.mkdir(exist_ok=True)
    for name in ("KNOWL_SUPERSEDE", "KNOWL_MAB_READER_LAYOUT"):
        os.environ.pop(name, None)
    os.environ.update({
        "PATH": f"{ENV_DIR / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "KNOWL_BRIDGE": str(BRIDGE),
        "KNOWL_PROJECT": str(project),
        "KNOWL_HOME": str(work_dir / "knowl-home"),
        "TMPDIR": str(tmp),
    })


if __name__ == "__main__":
    run_agent(KnowlAgent)
