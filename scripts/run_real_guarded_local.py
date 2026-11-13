"""PAID runs on this machine with a cost guard (the local twin of scripts/fir/run_real_guarded.sbatch).

Runs the given configs one after another (eval.queue) in its own process group. Every 30 s it adds up
cost_usd from the usage logs of runs started by this call; past --cap (USD) it stops every run.
The API key comes from the environment (ANTHROPIC_API_KEY); it is never written anywhere.
    ANTHROPIC_API_KEY=... .venv/bin/python scripts/run_real_guarded_local.py --cap 3 configs/runs/exp/x.yaml ...
"""
import argparse
import glob
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def spent(results: Path, start: float) -> float:
    total = 0.0
    for path in glob.glob(str(results / "runs" / "*" / "repeat_*" / "usage.jsonl")):
        if os.path.getmtime(path) < start:
            continue  # an earlier run
        for line in open(path):
            try:
                total += json.loads(line)["cost_usd"]
            except (ValueError, KeyError):
                pass
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cap", type=float, default=15.0)
    parser.add_argument("configs", nargs="+")
    args = parser.parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set")
    results = Path(os.environ.get("RESULTS_DIR", REPO / "results"))
    start = time.time()
    proc = subprocess.Popen([sys.executable, "-m", "eval.queue", "--name", f"local_{int(start)}", *args.configs],
                            cwd=REPO, start_new_session=True)
    while proc.poll() is None:
        time.sleep(30)
        cost = spent(results, start)
        print(f"[cost guard] {time.strftime('%H:%M')} spent ${cost:.4f} of ${args.cap}", flush=True)
        if cost > args.cap:
            print("[cost guard] over the cap: stopping every run", flush=True)
            os.killpg(proc.pid, signal.SIGTERM)
            sys.exit(3)
    print(f"[cost guard] finished (exit {proc.returncode}), total ${spent(results, start):.4f}", flush=True)
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
