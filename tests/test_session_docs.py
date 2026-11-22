"""Copied from Flotilla (keep both the same). The session documents (docs/session/) must match docs/session/SHA256SUMS, which scripts/sync_session_docs.py
(Flotilla) writes in both repos when it copies Flotilla's source to GRAFT. A copy edited without a sync fails here."""
import hashlib
from pathlib import Path

SESSION = Path(__file__).resolve().parent.parent / "docs" / "session"


def test_session_docs_match_their_manifest():
    sums = dict(reversed(l.split("  ", 1)) for l in (SESSION / "SHA256SUMS").read_text().splitlines() if l.strip())
    present = {p.name for p in SESSION.iterdir() if p.suffix in (".md", ".pdf")}
    assert present == set(sums), f"files and manifest differ: {sorted(present ^ set(sums))}"
    for name, digest in sums.items():
        got = hashlib.sha256((SESSION / name).read_bytes()).hexdigest()
        assert got == digest, f"{name} differs from the synced copy: edit Flotilla's docs/session/ and run scripts/sync_session_docs.py"
