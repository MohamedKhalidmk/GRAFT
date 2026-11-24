"""Run several run configs one after another, then rebuild the results table. Used by the UI.

    python -m eval.queue --name <queue id> configs/runs/a.yaml configs/runs/b.yaml ...

Progress goes to <RESULTS_DIR>/queues/<name>.jsonl (one event per line) so the UI can show it.
A failing config is recorded and the queue moves on to the next one.
"""

import argparse
import json
import sys
import os
import time
import traceback
from pathlib import Path

import yaml

from eval.methods import REPO
from eval.run import run
from eval.table import build


def queues_dir() -> Path:
    path = Path(os.environ.get("RESULTS_DIR", REPO / "results")) / "queues"
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("configs", nargs="+")
    args = parser.parse_args()
    log_path = queues_dir() / f"{args.name}.jsonl"

    def event(**fields) -> None:
        with open(log_path, "a") as f:
            f.write(json.dumps({"ts": time.time(), **fields}) + "\n")

    event(status="queued", configs=args.configs)
    tables, failed = set(), []
    for config in args.configs:
        cfg = yaml.safe_load(Path(config).read_text())
        event(status="started", config=config, run_name=cfg["run_name"])
        try:
            out = run(config)
            event(status="finished", config=config, run_name=cfg["run_name"], run_dir=str(out))
            tables.add((cfg["data"]["length"], cfg["llm"]["mode"]))
        except BaseException as e:  # record and continue with the rest of the queue
            event(status="failed", config=config, run_name=cfg["run_name"], error=f"{type(e).__name__}: {e}",
                  traceback=traceback.format_exc()[-2000:])
            failed.append(cfg["run_name"])
    for length, mode in tables:
        build(length, mode)
    event(status="done", failed=failed)
    if failed:  # the job must not end as COMPLETED when a run died (G35 and G40 repeats, Nibi, 2026-11-22)
        sys.exit(f"{len(failed)} of {len(args.configs)} runs failed: {', '.join(failed)} (see {log_path})")


if __name__ == "__main__":
    main()
