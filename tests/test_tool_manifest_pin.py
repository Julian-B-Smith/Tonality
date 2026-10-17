"""Security gate P0.1 — the MCP tool manifest is pinned (rug-pull prevention).

**Tool metadata is executable intent.** An LLM reads a tool's name, signature and
description and acts on them, so those strings are a *trust surface*, not
documentation — the MCP-specific attack class the security-hardening brief names
(tool poisoning / shadowing / **rug pulls**, where a tool's description changes
after review). Output is already pinned by the conformance golden; this pins the
*metadata*, which nothing covered before.

Two gates:

1. **The pin.** ``golden/tool_manifest.json`` stores, per tool, its **name +
   signature + full docstring** — deliberately the *whole text*, not just a hash,
   so a description change lands as a **readable diff in review**. A bare hash
   would tell you *that* something moved, never *what*; the brief's requirement
   is that "a description change gets the same review weight as a code change,"
   and that only works if a reviewer can read it. (A digest is stored too, as a
   cheap whole-manifest fingerprint.)
2. **The instruction-language lint.** A description *describes*; it never
   *directs*. The patterns below target **second-person imperatives aimed at the
   model** ("ignore previous…", "always call…", "your instructions") rather than
   the bare words *never/always*, which this codebase uses constantly and
   legitimately to describe engine behaviour ("never guessed", "never a
   verdict"). Calibrated: the targeted set flags **0** of the current tools, while
   a naive ``never|always`` check would wrongly flag 14 (2026-07-29; 24 by
   2026-10-17, as the surface grew) — a lint that cries wolf
   gets disabled, so it is scoped to the real signal.

Intended friction, stated plainly: an intentional docstring edit now requires a
pin regen **in the same PR** — exactly as an intended output change requires a
golden regen. Regenerate with (from the repo root):

    PYTHONPATH=. .venv/bin/python3.13 tests/test_tool_manifest_pin.py --regenerate

and **read the diff before committing it**.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
from pathlib import Path

import pytest

from mts.mcp import tools

PIN_PATH = Path(__file__).parent / "golden" / "tool_manifest.json"

# Second-person imperatives directed at the READER/MODEL. Not the bare words
# "never"/"always" — see the module docstring on why that matters.
_INSTRUCTION_PATTERNS = (
    r"ignore\s+(all\s+)?(previous|prior|above|other)",
    r"disregard\b",
    r"instead\s+of\s+(using|calling)",
    r"you\s+(must|should\s+always|are\s+required)",
    r"always\s+call",
    r"never\s+call",
    r"do\s+not\s+use\s+\w+\s+tool",
    r"system\s+prompt",
    r"your\s+instructions",
    r"prefer\s+this\s+tool",
)


def _manifest() -> dict:
    """The live tool metadata — name, signature, docstring — sorted by name."""
    entries = []
    for fn in sorted(tools.TOOLS, key=lambda f: f.__name__):
        entries.append({
            "name": fn.__name__,
            "signature": str(inspect.signature(fn)),
            "description": inspect.cleandoc(fn.__doc__ or ""),
        })
    blob = json.dumps(entries, sort_keys=True, ensure_ascii=False)
    return {
        "tool_count": len(entries),
        "digest": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
        "tools": entries,
    }


def _load_pin() -> dict:
    if not PIN_PATH.exists():
        raise AssertionError(
            f"Tool-manifest pin missing: {PIN_PATH}. Generate it with "
            "`PYTHONPATH=. .venv/bin/python3.13 tests/test_tool_manifest_pin.py --regenerate`"
        )
    return json.loads(PIN_PATH.read_text())


def test_every_tool_has_a_description():
    """A tool with no description gives the model nothing to reason from."""
    missing = [fn.__name__ for fn in tools.TOOLS if not (fn.__doc__ or "").strip()]
    assert not missing, f"tools without a description: {missing}"


def test_tool_manifest_matches_the_pin():
    """Names, signatures and descriptions must match the reviewed pin exactly."""
    pinned, live = _load_pin(), _manifest()
    pinned_by_name = {t["name"]: t for t in pinned["tools"]}
    live_by_name = {t["name"]: t for t in live["tools"]}

    added = sorted(set(live_by_name) - set(pinned_by_name))
    removed = sorted(set(pinned_by_name) - set(live_by_name))
    changed = sorted(
        n for n in set(pinned_by_name) & set(live_by_name)
        if pinned_by_name[n] != live_by_name[n]
    )
    detail = []
    for name in changed:
        for field in ("signature", "description"):
            if pinned_by_name[name][field] != live_by_name[name][field]:
                detail.append(f"  {name}.{field} changed")
    assert not (added or removed or changed), (
        "MCP tool metadata drifted from the reviewed pin — tool metadata is a "
        "TRUST SURFACE (an LLM reads it and acts on it), so a change needs the "
        "same review as code.\n"
        f"  added:   {added}\n  removed: {removed}\n  changed: {changed}\n"
        + "\n".join(detail)
        + "\nIf the change is intended, regenerate IN THE SAME PR and read the diff:\n"
        "  PYTHONPATH=. .venv/bin/python3.13 tests/test_tool_manifest_pin.py --regenerate"
    )
    assert live["digest"] == pinned["digest"]
    assert live["tool_count"] == pinned["tool_count"]


@pytest.mark.parametrize("pattern", _INSTRUCTION_PATTERNS)
def test_descriptions_describe_and_never_direct(pattern):
    """No description may issue instructions to the model (prompt-injection shape)."""
    offenders = [
        fn.__name__ for fn in tools.TOOLS
        if re.search(pattern, fn.__doc__ or "", re.IGNORECASE)
    ]
    assert not offenders, (
        f"tool description(s) {offenders} contain instruction-like language "
        f"matching {pattern!r} — descriptions DESCRIBE what a tool does; they "
        "never DIRECT the model. This is the tool-poisoning shape."
    )


def test_manifest_is_deterministic():
    """Descriptions must be static, version-controlled text — not generated.

    A dynamically built description could differ per call or per environment,
    which would make the pin meaningless and put un-reviewed text in front of
    the model (the brief's "no dynamically generated descriptions").
    """
    assert _manifest() == _manifest()


#: Docs that state the tool count as a LIVE claim about the current surface.
#
# The allowlist is deliberately explicit rather than a glob, because most files
# that say "N tools" are **dated records** whose numbers are correct-as-of and
# must NOT be rewritten: ROADMAP's per-slice delivered writeups (…**69 tools**…,
# …**70 tools**…) chronicle what the surface was at each slice, and
# `integrations/` + `docs/reviews/` are historical exchanges. Gating those would
# force falsifying the record to make a test pass — the opposite of the point.
# Adding a doc here is therefore a conscious act: it asserts "this number
# describes the surface *now*".
LIVE_TOOL_COUNT_DOCS = ("README.md", "INTEGRATION.md")

#: A stated count in any of the above. Kept loose (any "<n> tools") so a
#: reworded sentence stays gated instead of silently escaping the pattern.
_TOOL_COUNT_RE = re.compile(r"(\d+) tools")


@pytest.mark.parametrize("doc", LIVE_TOOL_COUNT_DOCS)
def test_live_docs_state_the_real_tool_count(doc):
    """Every live doc's plain-English count is held to the pin's discipline.

    README drifted 57 → 69 unnoticed (#248) because the number sitting next to
    the "the golden harness pins every tool and fails CI on drift" prose had no
    gate of its own. The first version of this gate then covered only README —
    so INTEGRATION.md, the **consumer-facing** door that external projects read
    to learn the surface, stayed at 46 and drifted further (#254). A gate that
    covers one of three doors is how the worst-placed staleness survives; hence
    the allowlist, and hence a failure message naming the file to edit.
    """

    path = PIN_PATH.parents[2] / doc
    live = len(tools.TOOLS)
    claimed = sorted({int(n) for n in _TOOL_COUNT_RE.findall(path.read_text())})
    assert claimed, f"{doc} no longer states a tool count — update this gate too."
    assert set(claimed) == {live}, (
        f"{doc} claims {claimed} tools; the live surface has {live}. "
        f"Update {doc} in the same PR that changes the tool set."
    )


def _regenerate() -> None:
    PIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = _manifest()
    PIN_PATH.write_text(json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"Pinned {manifest['tool_count']} tools to {PIN_PATH}")
    print(f"digest {manifest['digest']}")
    print("REVIEW THE DIFF before committing — this is the rug-pull gate.")


if __name__ == "__main__":
    import sys

    if "--regenerate" in sys.argv:
        _regenerate()
    else:
        print(__doc__)
