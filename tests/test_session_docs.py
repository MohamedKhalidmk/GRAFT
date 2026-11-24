# Sources: flotilla (docs/reference/REFERENCES.md)
"""Copied from Flotilla (keep both the same). The session documents (docs/session/) must match scripts/SHA256SUMS, which scripts/sync_session_docs.py
(Flotilla) writes in both repos when it copies Flotilla's source to GRAFT. A copy edited without a sync fails here."""
import hashlib
from pathlib import Path

SESSION = Path(__file__).resolve().parent.parent / "docs" / "session"


def test_session_docs_match_their_manifest():
    """Checks that the docs/session files match scripts/SHA256SUMS, with no file missing, extra or changed.
    Guards against: a session document edited in GRAFT alone drifting from Flotilla's copy."""
    sums = dict(reversed(l.split("  ", 1)) for l in (SESSION.parent.parent / "scripts" / "SHA256SUMS").read_text().splitlines() if l.strip())
    present = {p.name for p in SESSION.iterdir() if p.suffix == ".md"}
    assert present == set(sums), f"files and manifest differ: {sorted(present ^ set(sums))}"
    for name, digest in sums.items():
        got = hashlib.sha256((SESSION / name).read_bytes()).hexdigest()
        assert got == digest, f"{name} differs from the synced copy: edit Flotilla's docs/session/ and run scripts/sync_session_docs.py"


STATES = {"queued", "running", "waiting on me", "done", "parked", "dropped"}
COLUMNS = ["#", "Experiment", "IDs", "State", "Result (one line)", "Next step", "Last changed"]


def test_status_open_experiments_table():
    """Checks that STATUS.md's Open experiments table has the fixed columns, only the six states, a date on every row, and rows numbered 1..n.
    Guards against: an experiment row being deleted instead of having its state changed, so its record is lost.
    Rule from the user, 2026-11-22: rows are never deleted, only their state changes, so a gap in the numbers shows a deleted row."""
    import re
    text = (SESSION / "STATUS.md").read_text()
    section = text.split("## Open experiments", 1)[1]
    lines = [l for l in section.splitlines() if l.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    assert header == COLUMNS
    rows = [[c.strip() for c in l.strip("|").split("|")] for l in lines[2:]]
    assert [int(r[0]) for r in rows] == list(range(1, len(rows) + 1)), "row numbers must run 1..n: never delete a row"
    for r in rows:
        assert len(r) == len(COLUMNS), r[:2]
        assert r[3] in STATES, f"row {r[0]}: state {r[3]!r}"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r[6]), f"row {r[0]}: last changed {r[6]!r}"
