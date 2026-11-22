"""docs/reference/TESTS.md lists every test, generated from the docstrings (scripts/make_tests_doc.py)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_tests_doc_lists_every_test_and_is_up_to_date():
    """Checks that every test has a two-line docstring and that TESTS.md matches what the docstrings generate.
    Guards against: a new or changed test that TESTS.md does not describe, so the plain-words list drifts from the code."""
    spec = importlib.util.spec_from_file_location("make_tests_doc", ROOT / "scripts" / "make_tests_doc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = (ROOT / "docs" / "reference" / "TESTS.md").read_text()
    assert doc == mod.generated() + "\n" + mod.gaps(), "TESTS.md is out of date: run python scripts/make_tests_doc.py"
    for f in (ROOT / "tests").rglob("test_*.py"):
        for name, _, _ in mod.tests_in(f)[1]:
            assert f"| `{name}` |" in doc, f"{name} is not in TESTS.md"
