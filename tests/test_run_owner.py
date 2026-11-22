"""Run folders are owned by one job: only the same Slurm job (a requeue) resumes its unfinished folder. A rerun never
reuses another job's folder, dead or alive (2026-11-21: Nibi 28263641 had resumed the failed 28252727's folders)."""
import json
import os
import socket

import yaml

from eval.run import _claim, _own_folder, run_folder

CFG = {"run_name": "exp_x", "method": "graft", "repeats": 3}


def _unfinished(runs, name, job):
    d = runs / name
    d.mkdir(parents=True)
    (d / "config.yaml").write_text(yaml.safe_dump(CFG, sort_keys=False))
    (d / "owner.json").write_text(json.dumps({"job": job, "host": socket.gethostname(), "pid": 2 ** 22 + 12345}))
    return d


def test_own_folder(tmp_path, monkeypatch):
    """Checks that a run folder counts as this job's own only when its owner file names the current Slurm job.
    Guards against: a rerun resuming another job's folder, dead or alive, or a run outside Slurm resuming anything."""
    d = tmp_path / "exp_x_20261121-000000_j1"
    d.mkdir()
    monkeypatch.setenv("SLURM_JOB_ID", "200")
    assert not _own_folder(d)  # no owner file
    (d / "owner.json").write_text(json.dumps({"job": "100", "host": "h", "pid": 1}))
    assert not _own_folder(d)  # another job's folder (dead or alive)
    _claim(d)
    assert _own_folder(d)  # this job's own earlier attempt (requeue)
    monkeypatch.delenv("SLURM_JOB_ID")
    assert not _own_folder(d)  # outside Slurm nothing is resumed
    (d / "owner.json").write_text(json.dumps({"job": None, "host": socket.gethostname(), "pid": os.getpid()}))
    assert not _own_folder(d)


def test_rerun_gets_a_new_folder(tmp_path, monkeypatch):
    """Checks that a new Slurm job gets a new run folder even when a failed job left an unfinished folder of the same config.
    Guards against: a rerun writing its results into a dead job's run folder."""
    runs = tmp_path / "runs"
    dead = _unfinished(runs, "exp_x_20261121-081013_j28252727", "28252727")  # a failed job, long gone
    monkeypatch.setenv("SLURM_JOB_ID", "28263641")
    out, resumed = run_folder(runs, CFG)
    assert not resumed and out != dead and out.name.endswith("_j28263641")


def test_requeue_resumes_its_own_folder(tmp_path, monkeypatch):
    """Checks that a requeued job resumes its own unfinished folder, and starts a new one once that folder is finished.
    Guards against: a requeued job redoing its finished repeats, or a later attempt writing into an already finished folder."""
    runs = tmp_path / "runs"
    _unfinished(runs, "exp_x_20261121-081013_j28252727", "28252727")
    mine = _unfinished(runs, "exp_x_20261121-090000_j28263641", "28263641")
    monkeypatch.setenv("SLURM_JOB_ID", "28263641")
    assert run_folder(runs, CFG) == (mine, True)
    (mine / "summary.json").write_text("{}")  # finished: a later attempt of the same job starts a new folder
    out, resumed = run_folder(runs, CFG)
    assert not resumed and out != mine
