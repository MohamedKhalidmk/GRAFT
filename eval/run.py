"""Run one experiment config end to end.

    python -m eval.run configs/runs/bm25_tiny.yaml

For each repeat: build the task from the benchmark, start the Claude gateway, run the method in
its own environment, then score every answer with the benchmark's metric and attribute every
LLM call's tokens and cost to building or to a question.

Output, under <RESULTS_DIR>/runs/<run_name>_<timestamp>/ (RESULTS_DIR defaults to ./results):
    config.yaml                the exact config (re-run it with this command)
    run.log                    gateway + method output
    repeat_<k>/task.json       what the method saw (no gold answers)
    repeat_<k>/usage.jsonl     one line per LLM call
    repeat_<k>/scored.jsonl    one line per question: prediction, gold, score, tokens, cost
    summary.json               accuracy per split, tokens, times, cost

With `llm.mode: fake` nothing reaches the Anthropic API: replies are scripted, so accuracy is
meaningless, but every code path runs and the token counts approximate a real run's input side.
"""

import argparse
import json
import os
import socket
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import yaml

from eval.benchmark import answer_in_text, build_task, score
from eval.methods import METHODS, REPO

CORE_PYTHON = REPO / ".venv" / "bin" / "python"


def load_config(path: str | Path) -> dict:
    cfg = yaml.safe_load(Path(path).read_text())
    spec = METHODS[cfg["method"]]
    cfg.setdefault("method_config", {})
    cfg["data"].setdefault("chunk_size", spec.chunk_size)
    cfg["data"].setdefault("max_questions", None)
    cfg.setdefault("repeats", 1)
    return cfg


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _env() -> dict:
    return {**os.environ, "PYTHONPATH": str(REPO), "PYTHONUNBUFFERED": "1", "TOKENIZERS_PARALLELISM": "false"}


def start_gateway(cfg: dict, usage_log: Path, log) -> tuple[subprocess.Popen, str]:
    port = _free_port()
    cmd = [str(CORE_PYTHON), "-m", "baselines.claude_gateway.server", "--port", str(port),
           "--model", cfg["llm"]["model"], "--embedding-model", cfg["embedding_model"],
           "--usage-log", str(usage_log)]
    if cfg["llm"]["mode"] == "fake":
        cmd.append("--fake")
    elif not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("llm.mode is 'real' but ANTHROPIC_API_KEY is not set")
    proc = subprocess.Popen(cmd, cwd=REPO, env=_env(), stdout=log, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}"
    for _ in range(3600):  # 30 minutes: importing the embedding library alone takes minutes on cluster disks
        if proc.poll() is not None:
            raise RuntimeError("gateway exited during startup; see run.log")
        try:
            urllib.request.urlopen(url + "/health", timeout=1)
            return proc, url
        except OSError:
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("gateway did not start within 30 minutes")


def run_method(cfg: dict, repeat_dir: Path, gateway_url: str, log) -> None:
    spec = METHODS[cfg["method"]]
    if not spec.python.exists():
        raise SystemExit(f"environment for {spec.key} is missing: {spec.python} (see scripts/setup_envs.sh)")
    method_config = {**spec.defaults, **cfg["method_config"], "model": cfg["llm"]["model"],
                     "answer_max_tokens": cfg["llm"]["answer_max_tokens"],
                     "embedding_model": cfg["embedding_model"], "work_dir": str(repeat_dir / "memory")}
    (repeat_dir / "method_config.json").write_text(json.dumps(method_config, indent=2))
    cmd = [str(spec.python), "-m", spec.module, "--task", str(repeat_dir / "task.json"),
           "--config", str(repeat_dir / "method_config.json"), "--out", str(repeat_dir),
           "--gateway", gateway_url]
    result = subprocess.run(cmd, cwd=REPO, env=_env(), stdout=log, stderr=subprocess.STDOUT)
    if result.returncode != 0:
        raise RuntimeError(f"{spec.key} exited with code {result.returncode}; see run.log")


def score_repeat(repeat_dir: Path, golds) -> dict:
    """Score predictions and attribute gateway usage to build vs each question."""
    predictions = {r["q_index"]: r for r in map(json.loads, open(repeat_dir / "predictions.jsonl"))}
    usage = [json.loads(line) for line in open(repeat_dir / "usage.jsonl")] if (repeat_dir / "usage.jsonl").exists() else []
    per_q = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "llm_calls": 0})
    build = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "llm_calls": 0}
    for u in usage:
        bucket = per_q[u["q_index"]] if u["phase"] == "query" else build
        tokens_in = u["input_tokens"] + u["cache_read_tokens"] + u["cache_write_tokens"]
        bucket["input_tokens"] += tokens_in
        bucket["output_tokens"] += u["output_tokens"]
        bucket["cost_usd"] += u["cost_usd"]
        bucket["llm_calls"] += 1

    rows = []
    with open(repeat_dir / "scored.jsonl", "w") as f:
        for g in golds:
            p = predictions.get(g.q_index)
            prediction = p["prediction"] if p else ""
            row = {"q_index": g.q_index, "split": g.split, "qa_pair_id": g.qa_pair_id, "answers": g.answers,
                   "prediction": prediction, "answered": p is not None, **score(prediction, g.answers),
                   "query_time_s": p["query_time_s"] if p else None,
                   "stop_reason": (p or {}).get("stop_reason"), **per_q[g.q_index]}
            if p and "retrieved_text" in p:
                row["answer_in_retrieved"] = answer_in_text(g.answers, p["retrieved_text"])
                row["retrieved_text"] = p["retrieved_text"]
            if p and "subgraph_text" in p:  # is the gold answer anywhere in the subgraph? (text not kept: too large)
                row["answer_in_subgraph"] = answer_in_text(g.answers, p["subgraph_text"])
            if p and p.get("fact_sources"):
                row["fact_sources"] = p["fact_sources"]  # aligned with the "Memory i" blocks of retrieved_text
            rows.append(row)
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    build_info = json.loads((repeat_dir / "build.json").read_text())
    return {"rows": rows, "build": {**build, **build_info}}


def summarize(cfg: dict, repeats: list[dict]) -> dict:
    spec = METHODS[cfg["method"]]
    splits = cfg["data"]["splits"]
    acc = {s: [100 * statistics.mean(r["substring_exact_match"] for r in rep["rows"] if r["split"] == s)
               for rep in repeats] for s in splits}
    rows = [r for rep in repeats for r in rep["rows"]]
    query_times = [r["query_time_s"] for r in rows if r["query_time_s"] is not None]
    build_cost = sum(rep["build"]["cost_usd"] for rep in repeats)
    query_cost = sum(r["cost_usd"] for r in rows)
    return {
        "run_name": cfg["run_name"], "method": spec.key, "display": spec.display, "family": spec.family,
        "variant": ", ".join(f"{k}={v}" for k, v in sorted(cfg["method_config"].items())),
        "paper_row": spec.paper_row, "llm_mode": cfg["llm"]["mode"], "model": cfg["llm"]["model"],
        "embedding_model": cfg["embedding_model"], "length": cfg["data"]["length"],
        "chunk_size": cfg["data"]["chunk_size"], "repeats": len(repeats),
        "n_questions": {s: sum(1 for r in repeats[0]["rows"] if r["split"] == s) for s in splits},
        "unanswered": sum(not r["answered"] for r in rows),
        "accuracy": {s: {"mean": statistics.mean(v), "std": statistics.stdev(v) if len(v) > 1 else 0.0,
                         "per_repeat": v} for s, v in acc.items()},
        "answer_in_retrieved": {s: statistics.mean(r["answer_in_retrieved"] for r in rows if r["split"] == s)
                                for s in splits} if all("answer_in_retrieved" in r for r in rows) else None,
        "tokens_per_question": statistics.mean(r["input_tokens"] + r["output_tokens"] for r in rows),
        "llm_calls_per_question": statistics.mean(r["llm_calls"] for r in rows),
        "memory_build_time_s": statistics.mean(rep["build"]["memory_build_time_s"] for rep in repeats),
        "build_tokens": statistics.mean(rep["build"]["input_tokens"] + rep["build"]["output_tokens"] for rep in repeats),
        "query_time_s": statistics.mean(query_times) if query_times else None,
        "max_tokens_stops": sum(r["stop_reason"] == "max_tokens" for r in rows),
        "api_cost_usd": {"build": build_cost, "query": query_cost, "total": build_cost + query_cost},
        "build_info": repeats[0]["build"],
    }


def run(config_path: str) -> Path:
    cfg = load_config(config_path)
    spec = METHODS[cfg["method"]]
    runs_dir = Path(os.environ.get("RESULTS_DIR", REPO / "results")) / "runs"
    # resume: the newest unfinished run of this config (no summary.json, same config) is continued, keeping its
    # finished repeats; otherwise a new run folder
    unfinished = [d for d in sorted(runs_dir.glob(f"{cfg['run_name']}_2*")) if not (d / "summary.json").exists()
                  and (d / "config.yaml").exists() and yaml.safe_load((d / "config.yaml").read_text()) == cfg]
    out = unfinished[-1] if unfinished else runs_dir / f"{cfg['run_name']}_{time.strftime('%Y%m%d-%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    repeats = []
    with open(out / "run.log", "a", buffering=1) as log:
        for k in range(cfg["repeats"]):
            repeat_dir = out / f"repeat_{k}"
            if (repeat_dir / "scored.jsonl").exists():  # finished before a cut-off: rescore its saved predictions
                d = cfg["data"]
                _, golds = build_task(d["length"], d["splits"], d["chunk_size"], spec.agent_name, d["max_questions"])
                repeats.append(score_repeat(repeat_dir, golds))
                log.write(f"[runner] repeat {k}: kept from the earlier attempt\n")
                continue
            if repeat_dir.exists():  # an unfinished repeat starts over (its build resumes from the graph checkpoint)
                shutil.rmtree(repeat_dir)
            repeat_dir.mkdir()
            d = cfg["data"]
            task, golds = build_task(d["length"], d["splits"], d["chunk_size"], spec.agent_name, d["max_questions"])
            task.dump(repeat_dir / "task.json")
            log.write(f"[runner] repeat {k}: {spec.key}, {len(task.chunks)} chunks, {len(task.questions)} questions, "
                      f"llm={cfg['llm']['mode']}\n")
            gateway, url = start_gateway(cfg, repeat_dir / "usage.jsonl", log)
            try:
                run_method(cfg, repeat_dir, url, log)
            finally:
                gateway.terminate()
                gateway.wait()
            repeats.append(score_repeat(repeat_dir, golds))
        summary = summarize(cfg, repeats)
        (out / "summary.json").write_text(json.dumps(summary, indent=2))
        log.write(f"[runner] done: {json.dumps(summary['accuracy'])}\n")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    out = run(parser.parse_args().config)
    print((out / "summary.json").read_text())
    print(f"saved to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
