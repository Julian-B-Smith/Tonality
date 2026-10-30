"""Argument validation at the tool boundary (security slice, 2026-10-08; P0.2).

Every MCP tool argument is chosen by a caller this engine cannot trust: a
prompt-injected model on the stdio server, or any local process on the HTTP
bridge. Python type hints are not enforced at runtime, so before this a wrong
type (a dict where a list belongs, ``None`` for a required string, an int as a
file path) went straight into engine code and surfaced as a ``TypeError``,
``KeyError`` or ``AttributeError`` — which the bridge, correctly per RE-4e,
reports as a 500 *engine bug*, and which a fuzz pass found in 65 of 79 tools.
An int path was worse than a crash: ``open(7)`` opens file descriptor 7 of the
server process.

This checks each argument against the tool's own annotations, so the tools stay
the single source of their schema — no second copy to drift. Stdlib only on
purpose: the bridge must run without the optional ``mcp`` extra, so it cannot
lean on the pydantic validation FastMCP gives the stdio door. That validation
also has a gap this closes on every door: pydantic accepts NaN and infinity for
a float, and valid JSON can encode infinity (``1e999``).

Scope, stated: this checks SHAPE (container and scalar types, finiteness), not
MEANING. Whether an events row is a well-formed note, or a ruleset is
well-formed, stays with the tool's own validators, which already raise
``ValueError`` with a field-level message. A failure here raises ``ValueError``,
so every door reports it as the caller's error (HTTP 400), never a 500.
"""

from __future__ import annotations

import functools
import inspect
import math
import types
import typing

_NONE = type(None)


def _describe(value) -> str:
    return "None" if value is None else type(value).__name__


# No real argument nests deeper than a handful of levels (a list of events, a
# ruleset's rules and their conditions). 64 is far above that and far below
# Python's recursion limit, so every later recursive walk -- json.dumps of the
# echo, the engine's own parsers -- is safe once this passes. (P0.3 slice 1,
# 2026-10-17 review M7: a 3,000-deep payload reached this walk's old recursive
# form and escaped as RecursionError, a 500.)
MAX_NESTING = 64


def _finite(value, where: str) -> str | None:
    """Walk the whole payload: every float must be finite, and nothing may nest
    deeper than ``MAX_NESTING`` (NaN/inf are never valid musical input, and
    infinity sizes windowed analyses without bound).

    Iterative on purpose: a recursive walk over attacker-chosen depth IS the
    RecursionError it is meant to prevent. Children are pushed in reverse so the
    first problem reported is the same one the old depth-first recursion found.
    """

    stack = [(value, where, 0)]
    while stack:
        item, path, depth = stack.pop()
        if isinstance(item, float) and not math.isfinite(item):
            return f"{path} must be finite, got {item!r}"
        if isinstance(item, (list, dict)):
            if depth >= MAX_NESTING:
                return (f"{where} nests deeper than {MAX_NESTING} levels "
                        "(mts.mcp.validation.MAX_NESTING)")
            if isinstance(item, list):
                children = [(v, f"{path}[{i}]") for i, v in enumerate(item)]
            else:
                children = [(v, f"{path}[{k!r}]") for k, v in item.items()]
            stack.extend((v, p, depth + 1) for v, p in reversed(children))
    return None


def _check(value, ann, where: str) -> str | None:
    """None if ``value`` matches ``ann``; else a one-line reason."""

    if ann is typing.Any or ann is inspect._empty:
        return None
    origin = typing.get_origin(ann)
    if origin in (typing.Union, types.UnionType):
        options = typing.get_args(ann)
        if any(_check(value, opt, where) is None for opt in options):
            return None
        # If the value has the right CONTAINER for one option, its inner problem
        # is the useful message ("pcs[2] must be an int") — not "must be list |
        # None, got list", which names the type the caller already sent.
        for opt in options:
            o = typing.get_origin(opt) or opt
            if isinstance(o, type) and o is not _NONE and isinstance(value, o) and o in (list, dict):
                return _check(value, opt, where)
        names = " | ".join("None" if o is _NONE else getattr(o, "__name__", str(o)) for o in options)
        return f"{where} must be {names}, got {_describe(value)}"
    if ann is _NONE:
        return None if value is None else f"{where} must be None, got {_describe(value)}"
    if ann is bool:
        return None if isinstance(value, bool) else f"{where} must be a bool, got {_describe(value)}"
    if ann is int:
        # bool IS an int subclass; True as a pitch class is a type confusion.
        # An INTEGRAL float (3.0) is accepted: many JSON encoders emit one, and
        # the stdio door's pydantic layer accepts it, so the doors must agree.
        # A fractional one (3.5) is refused — the old int() silently truncated it.
        if isinstance(value, bool):
            return f"{where} must be an int, got bool"
        if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
            return None
        return f"{where} must be an int, got {_describe(value)} {value!r}" if isinstance(value, float) \
            else f"{where} must be an int, got {_describe(value)}"
    if ann is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return f"{where} must be a number, got {_describe(value)}"
        return None
    if ann is str:
        return None if isinstance(value, str) else f"{where} must be a string, got {_describe(value)}"
    if ann is list or origin is list:
        if not isinstance(value, list):
            return f"{where} must be a list, got {_describe(value)}"
        (item_ann,) = typing.get_args(ann) or (typing.Any,)
        for i, item in enumerate(value):
            problem = _check(item, item_ann, f"{where}[{i}]")
            if problem:
                return problem
        return None
    if ann is dict or origin is dict:
        return None if isinstance(value, dict) else f"{where} must be an object (dict), got {_describe(value)}"
    return None  # an annotation this checker does not model: defer to the tool


def validate_arguments(fn, kwargs: dict) -> None:
    """Raise ``ValueError`` if any argument does not match ``fn``'s annotations."""

    hints = typing.get_type_hints(fn)
    for name, value in kwargs.items():
        if name in hints:
            problem = _check(value, hints[name], name)
            if problem:
                raise ValueError(f"{fn.__name__}: {problem}.")
        problem = _finite(value, name)
        if problem:
            raise ValueError(f"{fn.__name__}: {problem}.")


def validated(fn):
    """Wrap a tool so every door (stdio, bridge, import) validates identically.

    ``functools.wraps`` preserves ``__name__``, ``__doc__`` and ``__wrapped__``,
    and ``inspect.signature`` follows ``__wrapped__``, so the published schema,
    the FastMCP argument model and the tool-manifest pin all see the original
    function unchanged.
    """

    signature = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)  # a TypeError here = bad call shape
        validate_arguments(fn, dict(bound.arguments))
        return fn(*args, **kwargs)

    return wrapper


__all__ = ["validate_arguments", "validated"]
