"""Both HippoRAG-v2 variants run end to end through eval.run in fake LLM mode.

Needs envs/hipporag-bundled and envs/hipporag-upstream (scripts/setup/hipporag-*.sh); each test
is skipped when its env is missing. No API calls: llm.mode is fake.
"""

import json

import pytest

from eval.methods import METHODS, REPO
from eval.run import run


@pytest.mark.parametrize("method", ["hipporag_bundled", "hipporag_upstream"])
def test_fake_run_answers_every_question(method: str) -> None:
    """Checks that each HippoRAG-v2 variant runs end to end in fake mode, answers every question, and makes one NER and one triple call per chunk.
    Guards against: a broken HippoRAG install or adapter leaving questions unanswered or building an empty graph, found only on a paid run."""
    if not METHODS[method].python.exists():
        pytest.skip(f"environment for {method} is not installed")
    out = run(str(REPO / "configs" / "runs" / f"{method}_fake_6k.yaml"))
    summary = json.loads((out / "summary.json").read_text())
    assert summary["unanswered"] == 0
    build = summary["build_info"]
    assert build["llm_calls"] == 2 * build["n_chunks"]  # one NER and one triple extraction call per chunk
    assert build["n_facts"] > 0 and build["graph_edges"] > 0
