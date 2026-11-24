"""eval.queue runs several configs in one job; a failed run must fail the job (Nibi, 2026-11-22)."""
import sys
from pathlib import Path

import pytest
import yaml

from eval import queue

REPO = Path(__file__).resolve().parent.parent


def _configs(tmp_path, names):
    out = []
    for n in names:
        p = tmp_path / f"{n}.yaml"
        p.write_text(yaml.safe_dump({"run_name": n, "data": {"length": "6k"}, "llm": {"mode": "fake"}}))
        out.append(str(p))
    return out


def test_queue_runs_every_config_and_fails_if_one_failed(tmp_path, monkeypatch):
    """Checks that the queue still runs the configs after a failed one, then exits with an error naming the failed run.
    Guards against: a Slurm job reported COMPLETED although one of its runs died, so a missing repeat goes unnoticed."""
    ran = []

    def run(config):
        ran.append(Path(config).stem)
        if Path(config).stem == "bad":
            raise ConnectionError("Connection error.")
        return tmp_path / Path(config).stem
    monkeypatch.setattr(queue, "run", run)
    monkeypatch.setattr(queue, "build", lambda *a: None)
    monkeypatch.setattr(queue, "queues_dir", lambda: tmp_path)
    monkeypatch.setattr(sys, "argv", ["queue", "--name", "t1", *_configs(tmp_path, ["good", "bad", "last"])])
    with pytest.raises(SystemExit) as e:
        queue.main()
    assert ran == ["good", "bad", "last"] and "1 of 3 runs failed: bad" in str(e.value.code)
    monkeypatch.setattr(sys, "argv", ["queue", "--name", "t2", *_configs(tmp_path, ["good"])])
    queue.main()   # all runs fine: returns normally


def test_qwen_job_scripts_use_a_port_of_their_own():
    """Checks that the Fir and Nibi Qwen job scripts serve vLLM on a free port chosen per job, never a fixed one.
    Guards against: two jobs on one node sharing a server, so a run dies when the other job ends and shuts it down."""
    for f in ("scripts/fir/run_qwen_graft.sbatch", "scripts/nibi/run_qwen_graft.sbatch"):
        s = (REPO / f).read_text()
        assert "PORT=" in s and "--port $PORT" in s and "127.0.0.1:$PORT/v1" in s and "8000" not in s, f
