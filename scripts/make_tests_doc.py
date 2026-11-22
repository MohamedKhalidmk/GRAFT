"""Write docs/reference/TESTS.md from the tests' own docstrings (same script in Flotilla and GRAFT).

    python scripts/make_tests_doc.py          # rewrite TESTS.md
    python scripts/make_tests_doc.py --check  # exit 1 if TESTS.md is out of date (tests/test_tests_doc.py does this too)

Every test function's docstring has two lines: what it checks, then "Guards against: ..." (what would go wrong
without it); further lines are detail and are left out. The tests are read with ast, never imported, so this runs
anywhere. Everything from the "## Gaps" heading to the end of TESTS.md is written by hand and kept as it is.
"""
import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "reference" / "TESTS.md"
GAPS = "## Gaps"
GUARD = "Guards against: "


def repo_name() -> str:
    return "Flotilla" if (ROOT / "flotilla").is_dir() else "GRAFT"


def tests_in(path: Path) -> tuple[str, list[tuple[str, str, str]]]:
    """(the module docstring's first line, [(test name, checks, guards against)]) for one test file."""
    tree = ast.parse(path.read_text())
    mod = (ast.get_docstring(tree) or "").strip().splitlines()
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            lines = [l.strip() for l in (ast.get_docstring(node) or "").splitlines()]
            if len(lines) < 2 or not lines[0] or not lines[1].startswith(GUARD):
                raise ValueError(f"{path.relative_to(ROOT)}::{node.name}: the docstring needs two lines, what it checks, "
                                 f"then '{GUARD}...'")
            rows.append((node.name, lines[0], lines[1][len(GUARD):]))
    return (mod[0] if mod else ""), rows


def cell(s: str) -> str:
    return s.replace("|", "\\|")


def generated() -> str:
    files = sorted((ROOT / "tests").rglob("test_*.py"))
    parts, n = [], 0
    for f in files:
        mod, rows = tests_in(f)
        if not rows:
            continue
        n += len(rows)
        rel = f.relative_to(ROOT).as_posix()
        parts += [f"## [{rel}](../../{rel})", ""]
        if mod:
            parts += [mod, ""]
        parts += ["| Test | What it checks | Guards against |", "|---|---|---|"]
        parts += [f"| `{name}` | {cell(c)} | {cell(g)} |" for name, c, g in rows]
        parts.append("")
    head = [f"# Tests ({repo_name()})", "",
            f"{n} tests in {sum(1 for f in files if tests_in(f)[1])} files, in plain words. Generated from each test's "
            "docstring by `scripts/make_tests_doc.py`; to change a line, edit the docstring and rerun the script. "
            "`tests/test_tests_doc.py` fails if a test is missing here or a line is out of date. The Gaps section at "
            "the end is written by hand.", ""]
    return "\n".join(head + parts)


def gaps() -> str:
    text = DOC.read_text() if DOC.exists() else ""
    return text[text.index(GAPS):] if GAPS in text else f"{GAPS}\n\nThings nothing tests yet.\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    want = generated() + "\n" + gaps()
    if a.check:
        if not DOC.exists() or DOC.read_text() != want:
            sys.exit(f"{DOC.relative_to(ROOT)} is out of date: run python scripts/make_tests_doc.py")
        return
    DOC.write_text(want)
    print(f"wrote {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
