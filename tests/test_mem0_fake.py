"""Both Mem0 variants run end to end on the fake gateway (no API calls)."""

import json

import pytest

from eval.methods import METHODS, REPO
from eval.run import run


@pytest.mark.parametrize("source", ["bundled", "upstream"])
def test_mem0_fake_run(source, tmp_path, monkeypatch):
    """Checks that each Mem0 variant runs end to end on the fake gateway, stores memories, and records ADD events, plus UPDATE events for the bundled one.
    Guards against: Mem0 silently storing nothing, or the bundled version's update path never running, while still answering questions."""
    if not METHODS[f"mem0_{source}"].python.exists():
        pytest.skip(f"run scripts/setup/mem0-{source}.sh first")
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    out = run(str(REPO / "configs" / "runs" / f"mem0_{source}_fake_6k.yaml"))
    summary = json.loads((out / "summary.json").read_text())
    assert summary["unanswered"] == 0
    build = summary["build_info"]
    assert build["llm_calls"] > 0 and build["memories_stored"] > 0
    assert build["add_events"].get("ADD", 0) > 0
    if source == "bundled":  # 0.1.88 also runs its UPDATE path; 2.2.1 is ADD-only
        assert build["add_events"].get("UPDATE", 0) > 0
