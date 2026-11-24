"""Knowl and total-agent-memory run end to end through eval.run in fake LLM mode.

Needs envs/knowl and envs/total-agent-memory (scripts/setup/knowl.sh, total-agent-memory.sh);
each test is skipped when its env is missing. No API calls: llm.mode is fake.
"""

import json

import pytest

from eval.methods import METHODS, REPO
from eval.run import run


@pytest.mark.parametrize("method", ["knowl", "total_agent_memory"])
def test_fake_run_answers_every_question(method: str) -> None:
    """Checks that Knowl and total-agent-memory each run end to end through eval.run in fake mode and answer every question.
    Guards against: a broken baseline environment or adapter leaving questions unanswered, found only on a paid run."""
    if not METHODS[method].python.exists():
        pytest.skip(f"environment for {method} is not installed")
    out = run(str(REPO / "configs" / "runs" / f"{method}_fake_6k.yaml"))
    summary = json.loads((out / "summary.json").read_text())
    assert summary["unanswered"] == 0
