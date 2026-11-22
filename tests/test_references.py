import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = re.compile(r"^(?:#\s*)?Sources:\s*(.+?)\s*(?:\(docs/reference/REFERENCES\.md\))?\s*$")


def reference_keys() -> set[str]:
    text = (ROOT / "docs/reference/REFERENCES.md").read_text()
    return set(re.findall(r"^\| `([^`]+)` \|", text, re.M))


def named_sources(path: Path) -> list[str] | None:
    for line in path.read_text(errors="replace").splitlines()[:30]:
        m = SOURCES.match(line.strip())
        if m:
            return [k.strip() for k in m.group(1).split(",") if k.strip()]
    return None


def scanned_files() -> list[Path]:
    """GRAFT's own Python files; the two submodules (MemoryAgentBench, GOAt) are third-party and left as they are."""
    pats = ["my_method/*.py", "my_method/gnn/*.py", "eval/*.py", "data/*.py", "scripts/**/*.py", "baselines/*.py", "baselines/*/*.py", "baselines/*/*/*.py", "tests/*.py"]
    files = {Path(p) for pat in pats for p in glob.glob(str(ROOT / pat), recursive=True)}
    return sorted(p for p in files if "memoryagentbench" not in p.parts and "GOAt" not in p.parts)


def test_every_named_source_is_in_references():
    """Checks that every key in a file's Sources line (GRAFT's code, scripts, baselines, tests) is listed in docs/reference/REFERENCES.md.
    Guards against: a file crediting a source that the references page does not cite, link or licence."""
    keys = reference_keys() | {"original"}
    missing = {str(p.relative_to(ROOT)): sorted(set(named_sources(p) or []) - keys) for p in scanned_files()}
    assert not {f: k for f, k in missing.items() if k}


def test_reference_entries_point_at_real_files():
    """Checks that every repository path named in REFERENCES.md exists, and that the main borrowed-code files carry a Sources line.
    Guards against: a references page that credits files which were renamed or deleted."""
    text = (ROOT / "docs/reference/REFERENCES.md").read_text()
    paths = {p for p in re.findall(r"`((?:my_method|eval|data|scripts|baselines|tests|docs|configs)/[^`*]+)`", text)}
    assert not sorted(p for p in paths if not (ROOT / p).exists())
    for f in ("eval/benchmark.py", "my_method/gnn/eig.py", "my_method/gnn/goat.py", "my_method/retrieval.py",
              "scripts/dnli_triples.py", "my_method/base_graph.py"):
        assert named_sources(ROOT / f), f
