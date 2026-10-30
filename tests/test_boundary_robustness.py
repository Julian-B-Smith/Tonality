"""P0.3 slice 1: the wedge and the bridge (2026-10-17 independent review H7, M7, M8).

Each test feeds the exact input the review used and asserts the boundary answers
with a status instead of blocking, dying silently, or escaping as a 500. Inputs
that used to BLOCK are run in a daemon thread with a deadline, so a regressed
guard fails the test instead of hanging the suite.
"""

from __future__ import annotations

import http.client
import json
import os
import socket
import threading
import time

import pytest

from mts.mcp import tools
from mts.mcp.validation import MAX_NESTING


def _within(seconds, fn, *args, **kwargs):
    """Run fn in a daemon thread; return ('done', result|exc) or ('blocked', None)."""
    box = {}

    def run():
        try:
            box["result"] = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - the test inspects it
            box["result"] = exc

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(seconds)
    return ("blocked", None) if t.is_alive() else ("done", box["result"])


# --- H7: a non-regular path must be refused before it is opened ---------------------------------


@pytest.fixture
def fifo(tmp_path):
    path = tmp_path / "pipe.mid"
    os.mkfifo(path)   # no writer: open() for reading blocks forever
    return path


@pytest.mark.parametrize("tool", [tools.midi_file_analysis, tools.piano_roll_view])
def test_a_fifo_is_refused_not_opened(tool, fifo, monkeypatch):
    monkeypatch.delenv(tools.MIDI_ROOTS_ENV, raising=False)   # the default: unrestricted
    state, result = _within(5, tool, path=str(fifo))
    assert state == "done", "the reader blocked on a FIFO: the server would be wedged"
    assert isinstance(result, ValueError) and "not a regular file" in str(result)


def test_a_symlink_to_a_fifo_is_refused(fifo, tmp_path, monkeypatch):
    monkeypatch.delenv(tools.MIDI_ROOTS_ENV, raising=False)
    link = tmp_path / "innocent.mid"
    link.symlink_to(fifo)
    state, result = _within(5, tools.midi_file_analysis, path=str(link))
    assert state == "done" and isinstance(result, ValueError)


@pytest.mark.parametrize("path", ["/dev/null", "/dev/zero"])
def test_devices_are_refused(path, monkeypatch):
    monkeypatch.delenv(tools.MIDI_ROOTS_ENV, raising=False)
    with pytest.raises(ValueError, match="not a regular file"):
        tools.midi_file_analysis(path=path)


def test_a_regular_midi_file_still_reads(monkeypatch):
    from pathlib import Path

    monkeypatch.delenv(tools.MIDI_ROOTS_ENV, raising=False)
    fixture = Path(__file__).parent / "golden" / "fixtures" / "pipeline.mid"
    assert tools.midi_file_analysis(path=str(fixture))["dataset"]


# --- M7 (validator): depth is capped on every door, without recursion --------------------------


def _nested(depth):
    root = cur = []
    for _ in range(depth):
        nxt = []
        cur.append(nxt)
        cur = nxt
    return root


def test_deep_nesting_is_refused_without_recursion_error():
    """3,000 deep used to escape the validator's own recursive walk as a 500."""
    with pytest.raises(ValueError, match="nests deeper than"):
        tools.validate_ruleset(ruleset=_nested(5000))


def test_nesting_at_the_cap_passes_the_validator():
    report = tools.validate_ruleset(ruleset=_nested(MAX_NESTING - 1))
    assert report["valid"] is False   # reported as data, as validate_ruleset promises


# --- M7 / M8 (bridge): a status for every malformed body, and no pinned threads ----------------


@pytest.fixture
def bridge(monkeypatch):
    from mts.mcp import bridge as b

    monkeypatch.setattr(b.BridgeHandler, "timeout", 0.5)   # keep the stall test fast
    server = b.make_server("127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()


def _post(port, body: bytes):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("POST", "/call/validate_ruleset", body=body,
                 headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    return resp.status, json.loads(resp.read() or b"{}")


@pytest.mark.parametrize("body", [
    b"[" * 20000,                                    # RecursionError inside json.loads
    b'{"ruleset": ' + b"9" * 5000 + b"}",            # past the 4,300-digit int limit
], ids=["deep-brackets", "huge-int-literal"])
def test_unparseable_bodies_get_a_400_not_an_empty_reply(bridge, body):
    status, payload = _post(bridge, body)
    assert status == 400 and payload["error_type"] == "JSONDecodeError"


def test_deep_but_parseable_json_gets_a_400(bridge):
    body = json.dumps({"ruleset": _nested(500)}).encode()
    status, payload = _post(bridge, body)
    assert status == 400 and "nests deeper than" in payload["error"]


def test_a_stalled_body_gets_a_408_and_frees_the_thread(bridge):
    """Content-Length 100, two bytes sent, then silence: used to block forever."""
    with socket.create_connection(("127.0.0.1", bridge), timeout=5) as s:
        s.sendall(b"POST /call/quality_brief HTTP/1.1\r\nHost: x\r\n"
                  b"Content-Length: 100\r\nContent-Type: application/json\r\n\r\n{}")
        start = time.monotonic()
        reply = s.recv(4096)
    assert reply.startswith(b"HTTP/1.0 408") or reply.startswith(b"HTTP/1.1 408"), reply[:80]
    assert time.monotonic() - start < 4
    # The server still answers other clients afterwards.
    status, _ = _post(bridge, b'{"ruleset": {}}')
    assert status == 200


def test_the_shipped_bridge_has_a_read_timeout():
    """The stall test lowers the timeout for speed; this pins the real default."""
    from mts.mcp import bridge as b

    assert b.BridgeHandler.timeout == b.READ_TIMEOUT_SECONDS
    assert 0 < b.READ_TIMEOUT_SECONDS <= 60
