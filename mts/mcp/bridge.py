"""Local HTTP bridge over the pure MCP tool functions (ROADMAP gap 9).

Browsers cannot spawn the stdio MCP server, so this exposes the exact same
surface — the SDK-free functions in ``tools.TOOLS`` — over local HTTP. It is
Decision 5-compliant glue: no intelligence, no new dependencies (stdlib
``http.server`` only), no state. The tool signatures and their ``to_dict()``
shapes remain the contract; the bridge just moves JSON.

Run it with ``python -m mts.mcp.bridge`` (defaults to ``127.0.0.1:8012``).

Endpoints:

- ``GET  /``             service info (name, tool count, endpoint shapes)
- ``GET  /tools``        descriptors for every tool (name, doc, params)
- ``GET  /tools/<name>`` descriptor for one tool
- ``POST /call/<name>``  invoke a tool; body is a JSON object of keyword
  arguments. Success: ``{"ok": true, "result": ...}``. Failure: 400 with
  ``{"ok": false, "error": ..., "error_type": ...}`` for bad input — a
  ``ValueError`` from the engine, or a ``TypeError`` from *binding* the
  kwargs (unknown/missing arguments); 404 for unknown tools; 500 otherwise,
  **including a TypeError raised inside the engine** (an engine bug is not
  the client's fault — RE-4e).

CORS is an **origin allowlist** (RE-4e, mechanism chosen by A6 — see
``integrations/audiology/ack-re4-and-cors-answer.md``). Default policy:

- requests with **no** ``Origin`` header are allowed (curl, CLIs, server-side
  callers — CORS is a browser concept);
- browser origins are allowed when the host is loopback (``localhost`` /
  ``127.0.0.1`` / ``[::1]``, any port, http/https) — the wildcard port is
  load-bearing for Vite-class dev servers;
- anything else is **actively rejected with 403** (not just denied the CORS
  header — a disallowed page must not execute tools), unless added via
  ``--allow-origin <origin>`` (repeatable; exact match — the escape hatch for
  packaged-app schemes like ``tauri://localhost``) or ``--open-cors``
  (restores the old wildcard explicitly).

Local-first: this is not a hosted endpoint and must not become one.
"""

from __future__ import annotations

import argparse
import inspect
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .tools import TOOLS

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8012

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}

_TOOL_MAP = {fn.__name__: fn for fn in TOOLS}

#: Largest request body the bridge reads. The biggest legitimate payload is an
#: events list for a whole piece: at the engine's span limit (100,000 beats) a
#: dense one is a few MB of JSON. 16 MB is far above that and far below harm.
MAX_BODY_BYTES = 16 * 1024 * 1024
# Seconds a connection may sit without sending what it promised. Without it, a
# client that sends `Content-Length: 100` and two bytes pins a handler thread
# forever, and enough of them starve the process of file descriptors (P0.3
# slice 1, 2026-10-17 review M8). It bounds socket WAITS only, never a tool's
# own computation, and loopback delivers a full 16 MB body in well under it.
READ_TIMEOUT_SECONDS = 10.0


def origin_allowed(
    origin: str | None,
    *,
    extra_origins: frozenset[str] = frozenset(),
    open_cors: bool = False,
) -> bool:
    """The RE-4e allowlist: no-Origin callers and loopback web origins pass;
    everything else needs an explicit ``--allow-origin`` entry (exact match)
    or ``--open-cors``."""
    if origin is None or open_cors:
        return True
    if origin in extra_origins:
        return True
    parts = urlsplit(origin)
    return parts.scheme in ("http", "https") and (parts.hostname or "") in _LOOPBACK_HOSTS


def describe_tool(fn) -> dict:
    """A JSON-ready descriptor of one tool: name, docstring, parameters."""
    params = []
    for name, param in inspect.signature(fn).parameters.items():
        required = param.default is inspect.Parameter.empty
        params.append(
            {
                "name": name,
                "annotation": (
                    None
                    if param.annotation is inspect.Parameter.empty
                    else str(param.annotation)
                ),
                "required": required,
                "default": None if required else param.default,
            }
        )
    return {"name": fn.__name__, "doc": inspect.getdoc(fn), "params": params}


def _service_info() -> dict:
    return {
        "service": "tonality-http-bridge",
        "tools": len(TOOLS),
        "endpoints": {
            "GET /tools": "descriptors for every tool",
            "GET /tools/<name>": "descriptor for one tool",
            "POST /call/<name>": "invoke a tool with a JSON object of kwargs",
        },
    }


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "TonalityBridge/0.1"
    # StreamRequestHandler applies this to the socket in setup(); it also closes
    # idle keep-alive connections, which is what frees their threads.
    timeout = READ_TIMEOUT_SECONDS

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass  # a library-embedded local server should not spam stderr

    def _cors_headers(self) -> list[tuple[str, str]]:
        origin = self.headers.get("Origin")
        if origin is None:
            return []
        if getattr(self.server, "open_cors", False):
            return [("Access-Control-Allow-Origin", "*")]
        # allowed (the caller gated on _origin_ok): echo the specific origin
        return [("Access-Control-Allow-Origin", origin), ("Vary", "Origin")]

    def _origin_ok(self) -> bool:
        return origin_allowed(
            self.headers.get("Origin"),
            extra_origins=getattr(self.server, "extra_origins", frozenset()),
            open_cors=getattr(self.server, "open_cors", False),
        )

    def _reject_origin(self) -> None:
        # Active rejection (RE-4e): a disallowed page must not execute tools —
        # denying only the CORS header would still run the call server-side.
        body = json.dumps(
            {
                "ok": False,
                "error": (
                    f"Origin {self.headers.get('Origin')!r} is not allowed. The "
                    "bridge allows loopback web origins and no-Origin callers by "
                    "default; start it with --allow-origin <origin> to extend, "
                    "or --open-cors to disable the allowlist."
                ),
                "error_type": "OriginNotAllowed",
            }
        ).encode("utf-8")
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in self._cors_headers():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: int, message: str, error_type: str) -> None:
        self._send(status, {"ok": False, "error": message, "error_type": error_type})

    def do_OPTIONS(self) -> None:  # CORS preflight
        if not self._origin_ok():
            self._reject_origin()
            return
        self.send_response(204)
        for name, value in self._cors_headers():
            self.send_header(name, value)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if not self._origin_ok():
            self._reject_origin()
            return
        if self.path == "/":
            self._send(200, _service_info())
        elif self.path == "/tools":
            self._send(200, [describe_tool(fn) for fn in TOOLS])
        elif self.path.startswith("/tools/"):
            name = self.path[len("/tools/") :]
            fn = _TOOL_MAP.get(name)
            if fn is None:
                self._send_error(404, f"Unknown tool {name!r}. GET /tools lists all tools.", "NotFound")
            else:
                self._send(200, describe_tool(fn))
        else:
            self._send_error(404, f"Unknown path {self.path!r}.", "NotFound")

    def do_POST(self) -> None:
        if not self._origin_ok():
            self._reject_origin()
            return
        if not self.path.startswith("/call/"):
            self._send_error(404, f"Unknown path {self.path!r}. POST /call/<tool_name>.", "NotFound")
            return
        name = self.path[len("/call/") :]
        fn = _TOOL_MAP.get(name)
        if fn is None:
            self._send_error(404, f"Unknown tool {name!r}. GET /tools lists all tools.", "NotFound")
            return
        # Parse the length STRICTLY before reading (security slice, 2026-10-08).
        # Each of these was live: a non-numeric header crashed the handler so the
        # client got no response at all; a negative one made read(-1) block until
        # the client hung up; and an unbounded one let a caller claim any size and
        # hold the thread waiting for it. The origin gate above already ran, so
        # these are reachable only from an allowed origin or a local process.
        header = self.headers.get("Content-Length") or "0"
        try:
            length = int(header)
        except ValueError:
            self._send_error(400, f"Content-Length must be an integer, got {header!r}.", "BadRequest")
            return
        if length < 0:
            self._send_error(400, "Content-Length must not be negative.", "BadRequest")
            return
        if length > MAX_BODY_BYTES:
            self._send_error(
                413, f"Request body of {length:,} bytes exceeds the bridge limit of "
                f"{MAX_BODY_BYTES:,} (mts.mcp.bridge.MAX_BODY_BYTES).", "PayloadTooLarge")
            return
        try:
            raw = self.rfile.read(length) if length else b""
        except TimeoutError:
            self.close_connection = True
            self._send_error(408, f"Request body did not arrive within {READ_TIMEOUT_SECONDS:g} s "
                             "(mts.mcp.bridge.READ_TIMEOUT_SECONDS).", "RequestTimeout")
            return
        # ValueError, not just JSONDecodeError: an integer literal past Python's
        # 4,300-digit limit raises a plain ValueError, and deep nesting raises
        # RecursionError. Both used to escape do_POST, so the client got an empty
        # reply instead of a status (2026-10-17 review M7).
        try:
            kwargs = json.loads(raw) if raw else {}
        except RecursionError:
            self._send_error(400, "Request body is not valid JSON: nested too deeply to parse.",
                             "JSONDecodeError")
            return
        except ValueError as exc:
            self._send_error(400, f"Request body is not valid JSON: {exc}", "JSONDecodeError")
            return
        if not isinstance(kwargs, dict):
            self._send_error(400, "Request body must be a JSON object of keyword arguments.", "TypeError")
            return
        # Bind the signature BEFORE calling (RE-4e): a TypeError from binding
        # is the caller's (unknown/missing kwargs → 400), but a TypeError
        # raised *inside* the engine is an engine bug and must report as 500 —
        # the old blanket `except TypeError → 400` blamed the client for both.
        try:
            inspect.signature(fn).bind(**kwargs)
        except TypeError as exc:
            self._send_error(400, f"Bad arguments for {name!r}: {exc}", "TypeError")
            return
        try:
            result = fn(**kwargs)
            self._send(200, {"ok": True, "result": result})
        except ValueError as exc:
            self._send_error(400, str(exc), type(exc).__name__)
        except Exception as exc:  # noqa: BLE001 - bridge must answer, not die
            self._send_error(500, f"{type(exc).__name__}: {exc}", type(exc).__name__)


def make_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    extra_origins: frozenset[str] | set[str] = frozenset(),
    open_cors: bool = False,
) -> ThreadingHTTPServer:
    """Build the bridge server (not yet serving; call ``serve_forever``)."""
    server = ThreadingHTTPServer((host, port), BridgeHandler)
    server.daemon_threads = True
    server.extra_origins = frozenset(extra_origins)  # type: ignore[attr-defined]
    server.open_cors = bool(open_cors)  # type: ignore[attr-defined]
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Tonality local HTTP bridge (gap 9).")
    parser.add_argument("--host", default=DEFAULT_HOST, help="bind address (default: loopback)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port (default: {DEFAULT_PORT})")
    parser.add_argument(
        "--allow-origin",
        action="append",
        default=[],
        metavar="ORIGIN",
        help="allow an extra web origin, exact match (repeatable; e.g. "
        "tauri://localhost). Loopback http(s) origins and no-Origin callers "
        "are always allowed.",
    )
    parser.add_argument(
        "--open-cors",
        action="store_true",
        help="disable the origin allowlist entirely (the pre-RE-4e wildcard).",
    )
    args = parser.parse_args(argv)
    server = make_server(
        args.host,
        args.port,
        extra_origins=frozenset(args.allow_origin),
        open_cors=args.open_cors,
    )
    host, port = server.server_address[:2]
    print(f"Tonality HTTP bridge: http://{host}:{port} ({len(TOOLS)} tools; GET /tools to discover)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
