"""Both MemGPT / Letta variants run end to end through eval.run in fake LLM mode.

Needs envs/letta-bundled and envs/letta-upstream (scripts/setup/letta-*.sh); each test is skipped
when its env is missing. No API calls: llm.mode is fake.
"""

import json

import pytest

from baselines.claude_gateway.fake_rules.fc_answer import FAKE_ANSWER
from eval.methods import METHODS, REPO
from eval.run import run


@pytest.mark.parametrize("method", ["letta_bundled", "letta_upstream"])
def test_fake_run_answers_every_question(method: str) -> None:
    """Checks that each Letta variant runs end to end in fake mode, stores every chunk, searches then answers per question, and returns the fake answer.
    Guards against: a Letta failure turning into the benchmark's 'Error' answer and being scored as a normal wrong answer instead of failing."""
    if not METHODS[method].python.exists():
        pytest.skip(f"environment for {method} is not installed")
    out = run(str(REPO / "configs" / "runs" / f"{method}_fake_6k.yaml"))
    summary = json.loads((out / "summary.json").read_text())
    assert summary["unanswered"] == 0
    assert summary["build_info"]["archival_passages"] >= summary["build_info"]["n_chunks"]
    assert summary["llm_calls_per_question"] == 2  # archival_memory_search, then send_message
    scored = [json.loads(line) for line in open(out / "repeat_0" / "scored.jsonl")]
    assert all(row["prediction"] == FAKE_ANSWER for row in scored)  # the benchmark answers "Error" on failure
