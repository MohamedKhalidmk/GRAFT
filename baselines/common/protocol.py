"""Contract between the runner and a method process.

Every method (baseline or ours) runs as its own process, often in its own Python environment,
because the third-party systems pin conflicting packages. This module is stdlib-only so any
environment can import it.

The runner writes a task file (chunks + question prompts, never the gold answers) and starts:

    python -m <method module> --task task.json --config method.json --out <dir> --gateway <url>

The method memorizes every chunk in order, then answers every question, and writes
    <out>/build.json          {"memory_build_time_s": ..., **extra}
    <out>/predictions.jsonl   one {"q_index", "prediction", "query_time_s", **extra} per question

All LLM and embedding calls go through the Claude gateway at <url>. The method tells the gateway
which phase it is in, so the gateway can attribute every call's tokens to building or to a question.
"""

import argparse
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class Question:
    q_index: int
    split: str  # "sh" or "mh"
    query: str  # the benchmark's full query prompt for this method's prompt family


@dataclass
class Task:
    sub_datasets: list[str]
    chunk_size: int
    chunks: list[str]
    questions: list[Question]

    @classmethod
    def load(cls, path: str | Path) -> "Task":
        raw = json.loads(Path(path).read_text())
        return cls(raw["sub_datasets"], raw["chunk_size"], raw["chunks"],
                   [Question(**q) for q in raw["questions"]])

    def dump(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps({
            "sub_datasets": self.sub_datasets, "chunk_size": self.chunk_size, "chunks": self.chunks,
            "questions": [q.__dict__ for q in self.questions]}, ensure_ascii=False))


class Gateway:
    """Client for the gateway's control endpoint."""

    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.openai_base_url = self.url + "/v1"  # for OpenAI-style clients
        self.anthropic_base_url = self.url  # for the Anthropic SDK

    def set_phase(self, phase: str, q_index: int | None = None) -> None:
        body = json.dumps({"phase": phase, "q_index": q_index}).encode()
        request = urllib.request.Request(self.url + "/control/phase", data=body,
                                         headers={"Content-Type": "application/json"})
        urllib.request.urlopen(request, timeout=30).read()


class Agent(Protocol):
    def memorize(self, chunks: list[str]) -> dict:
        """Ingest all chunks in arrival order. Returns extra info to record in build.json."""

    def answer(self, question: Question) -> tuple[str, dict]:
        """Answer one question. Returns (prediction, extra info for predictions.jsonl)."""


def run_agent(make_agent) -> None:
    """Entry point for a method module: `run_agent(lambda config, gateway, task: MyAgent(...))`."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--gateway", required=True)
    args = parser.parse_args()

    task = Task.load(args.task)
    config = json.loads(Path(args.config).read_text())
    gateway = Gateway(args.gateway)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    gateway.set_phase("build")
    start = time.time()
    agent = make_agent(config, gateway, task)
    extra = agent.memorize(task.chunks) or {}
    build = {"memory_build_time_s": time.time() - start, "n_chunks": len(task.chunks), **extra}
    (out / "build.json").write_text(json.dumps(build, indent=2))
    print(f"[agent] memory built in {build['memory_build_time_s']:.1f}s", flush=True)

    with open(out / "predictions.jsonl", "w") as f:
        for q in task.questions:
            gateway.set_phase("query", q.q_index)
            start = time.time()
            prediction, extra = agent.answer(q)
            row = {"q_index": q.q_index, "prediction": prediction,
                   "query_time_s": time.time() - start, **(extra or {})}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[agent] q{q.q_index} ({q.split}) -> {prediction!r}", flush=True)
    gateway.set_phase("done")
