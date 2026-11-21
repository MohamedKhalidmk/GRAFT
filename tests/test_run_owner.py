"""Run folders are owned: a folder whose owner is still running is never resumed by another process."""
import json
import os
import socket

from eval.run import _claim, _owner_alive


def test_owner_alive(tmp_path):
    d = tmp_path / "exp_x_20261121-000000"
    d.mkdir()
    assert not _owner_alive(d)  # no owner file: an old folder, free to resume
    (d / "owner.json").write_text(json.dumps({"job": None, "host": socket.gethostname(), "pid": os.getppid()}))
    assert _owner_alive(d)  # another live process on this host
    (d / "owner.json").write_text(json.dumps({"job": None, "host": socket.gethostname(), "pid": 2 ** 22 + 12345}))
    assert not _owner_alive(d)  # dead pid
    _claim(d)
    assert not _owner_alive(d)  # our own claim does not block us
