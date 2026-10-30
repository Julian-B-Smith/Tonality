"""Supply-chain gate (ROADMAP gap 27(c)) — Layer-0: offline, deterministic.

What is guaranteed here, per PR: every lock pin is exact and hash-pinned, the
locks still satisfy pyproject's ranges, the SBOM matches the locks, and every
workflow pins its actions to commit SHAs under a declared `permissions:` block.

What is NOT guaranteed here, and why: whether the locks are the LATEST
resolution, and whether a pinned version has a newly published vulnerability.
Both need the network and change with the calendar, not the code, so they live
in the scheduled upstream canary (`.github/workflows/upstream-canary.yml`,
`scripts/upstream-canary.sh`) — measured, never merge-blocking.

Each check is a pure function over file TEXT, so the must-fail controls below
feed it plants without touching the real files.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from packaging.requirements import Requirement

from scripts import sbom

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
LOCK_EXTRAS = {"ci.lock": "dev", "server.lock": "mcp"}

try:
    import tomllib
except ModuleNotFoundError:          # Python 3.10: tomli is in ci.lock for exactly this
    import tomli as tomllib


def lock_problems(text: str) -> list[str]:
    """Every requirement line must be `name==version` and carry a sha256."""
    problems = []
    for line in text.splitlines():
        if line and line[0].isalnum() and not sbom._PIN.match(line):
            problems.append(f"not an exact pin: {line.strip()}")
    for entry in sbom.parse_lock_text(text):
        if not entry["hashes"]:
            problems.append(f"no sha256 for {entry['name']}=={entry['version']}")
    return problems


def range_problems(lock_text: str, requirements: list[str]) -> list[str]:
    """Each direct requirement is locked, at a version its range admits."""
    pinned: dict[str, set[str]] = {}
    for entry in sbom.parse_lock_text(lock_text):
        pinned.setdefault(entry["name"], set()).add(entry["version"])
    problems = []
    for spec in requirements:
        req = Requirement(spec)
        name = req.name.lower()
        if name not in pinned:
            problems.append(f"{name} is required but not locked")
        elif not any(req.specifier.contains(v, prereleases=True) for v in pinned[name]):
            problems.append(f"{name} locked at {sorted(pinned[name])}, outside {req.specifier}")
    return problems


_USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.M)
_SHA_PIN = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")


def workflow_problems(text: str) -> list[str]:
    problems = []
    for ref in _USES.findall(text):
        if not ref.startswith("./") and not _SHA_PIN.match(ref):
            problems.append(f"action not pinned to a commit SHA: {ref}")
    # Top-level only: a job-level block does not cover the other jobs.
    if not re.search(r"^permissions:", text, re.M):
        problems.append("no top-level `permissions:` block (the token defaults to write)")
    return problems


def _pyproject_requirements(extra: str) -> list[str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return list(project["dependencies"]) + list(project["optional-dependencies"][extra])


# --- the real files ---------------------------------------------------------------------------


@pytest.mark.parametrize("lock", sorted(LOCK_EXTRAS))
def test_every_lock_pin_is_exact_and_hashed(lock):
    assert lock_problems((ROOT / "requirements" / lock).read_text()) == []


@pytest.mark.parametrize("lock", sorted(LOCK_EXTRAS))
def test_the_locks_still_satisfy_pyproject(lock):
    """Catches a pyproject range edited without re-running the lock's header command."""
    text = (ROOT / "requirements" / lock).read_text()
    assert range_problems(text, _pyproject_requirements(LOCK_EXTRAS[lock])) == []


def test_the_sbom_matches_the_locks():
    current = sbom.SBOM_PATH.read_text(encoding="utf-8")
    assert current == sbom.render(), "stale SBOM: run scripts/sbom.py"


@pytest.mark.parametrize("workflow", WORKFLOWS, ids=lambda p: p.name)
def test_workflows_pin_actions_and_scope_the_token(workflow):
    assert workflow_problems(workflow.read_text()) == []


def test_ci_installs_from_the_hashed_lock():
    """The lock is only a guarantee if CI actually installs from it."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "--require-hashes -r requirements/ci.lock" in ci
    assert "--no-deps -e ." in ci


# --- must-fail controls: each checker sees its planted defect ---------------------------------

_GOOD_LOCK = "mido==1.3.3 \\\n    --hash=sha256:" + "a" * 64 + "\n"


def test_controls_lock_checker_sees_plants():
    assert lock_problems(_GOOD_LOCK) == []
    assert lock_problems("mido==1.3.3\n")                       # hash dropped
    assert lock_problems("mido>=1.3 \\\n    --hash=sha256:" + "a" * 64 + "\n")  # range, not a pin


def test_controls_range_checker_sees_plants():
    assert range_problems(_GOOD_LOCK, ["mido>=1.3,<2"]) == []
    assert range_problems(_GOOD_LOCK, ["mido>=2"])              # pyproject moved past the lock
    assert range_problems(_GOOD_LOCK, ["mido>=1.3", "newdep"])  # new dep never locked


def test_controls_workflow_checker_sees_plants():
    good = "permissions:\n  contents: read\njobs:\n  t:\n    steps:\n      - uses: a/b@" + "0" * 40 + "\n"
    assert workflow_problems(good) == []
    assert workflow_problems(good.replace("0" * 40, "v4"))       # tag, movable
    assert workflow_problems(good.replace("permissions:\n  contents: read\n", ""))
    assert workflow_problems(good.replace("permissions:", "  permissions:"))  # job-level only


def test_controls_sbom_gate_sees_a_stale_file(monkeypatch, tmp_path):
    stale = tmp_path / "sbom.cdx.json"
    stale.write_text(sbom.render().replace('"1.3.3"', '"1.3.2"', 1), encoding="utf-8")
    monkeypatch.setattr(sbom, "SBOM_PATH", stale)
    assert sbom.main(["--check"]) == 1


# --- the mcp ceiling is load-bearing (audit #245, ROADMAP gap 29) ----------------------------


def ceiling_problems(mcp_spec: str, server_source: str) -> list[str]:
    """While the server is written against the 1.x API, the extra must not admit 2.x.

    mcp 2.0.0 removed `mcp.server.fastmcp`. A range that admits 2.x makes the
    documented `pip install 'mts[mcp]'` resolve the newest 2.x and the server
    fail with "install the extra you just installed". CI cannot see that on its
    own: it installs from the lock, which pins 1.x. Dependabot widened the
    range to <3 on 2026-10-30 (#312) and every check passed, which is why this
    gate exists. Drop it with the ceiling when gap 29 ports build_server().
    """
    if "mcp.server.fastmcp" not in server_source:
        return []
    req = Requirement(mcp_spec)
    if req.specifier.contains("2.0.0", prereleases=True):
        return [f"{mcp_spec!r} admits mcp 2.x, but mts/mcp/server.py imports the 1.x-only "
                "mcp.server.fastmcp; restore the <2 ceiling or port the server (gap 29)"]
    return []


def test_the_mcp_ceiling_matches_the_server_api():
    spec = next(r for r in _pyproject_requirements("mcp") if Requirement(r).name == "mcp")
    server = (ROOT / "mts" / "mcp" / "server.py").read_text(encoding="utf-8")
    assert ceiling_problems(spec, server) == []


def test_controls_ceiling_checker_sees_plants():
    fastmcp = "from mcp.server.fastmcp import FastMCP"
    assert ceiling_problems("mcp>=1.2,<2", fastmcp) == []
    assert ceiling_problems("mcp>=1.2,<3", fastmcp)        # #312's widening
    assert ceiling_problems("mcp>=1.2", fastmcp)           # no ceiling at all
    assert ceiling_problems("mcp>=1.2,<3", "from mcp.server import MCPServer") == []  # ported
