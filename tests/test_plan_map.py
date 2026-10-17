"""The plan map's data stays true to the plan of record (Layer-0, blocking).

docs/design/plan-map.html carries its data as a JSON block and runs these same
checks in the browser. Here they run in the dev suite, so a ROADMAP edit that
orphans a citation, or a map edit that drifts from docs/design/1.0-PLAN.md,
fails a PR instead of waiting for someone to press the button.

The parsers mirror the page's JavaScript (parseRoadmap / parseDecisions /
parsePlanTable); a change to one is a change to both. Every check has a
planted must-fail control at the bottom of this file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "docs" / "design" / "plan-map.html"
PLAN = ROOT / "docs" / "design" / "1.0-PLAN.md"
STATUSES = {"shipped", "in progress", "ruled", "planned", "recorded", "post-1.0", "parked"}
SINK = "v1"
# Gap entries sit between these markers; ROADMAP has other numbered lists
# (standing reviews) whose "1. **" lines would otherwise be read as gaps.
GAP_START, GAP_END = "\n1. **MIDI export**", "\n## Decisions on record"


def load_data(html: str) -> dict:
    m = re.search(r'<script type="application/json" id="plan-data">\s*(.*?)\s*</script>', html, re.S)
    assert m, "plan-map.html has no plan-data block"
    return json.loads(m.group(1))


def parse_roadmap(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    a, b = text.find(GAP_START), text.find(GAP_END)
    if a >= 0 and b > a:
        block = text[a:b].split("\n")
        for i, line in enumerate(block):
            m = re.match(r"^(\d+)\. \*\*(.*)$", line)
            if m:
                title = m.group(2)
                if "**" not in title and i + 1 < len(block):
                    title += " " + block[i + 1].strip()
                out[f"G{m.group(1)}"] = title.split("**")[0].strip()
    for m in re.finditer(r"^### Phase ([\d.]+)\b(.*)$", text, re.M):
        out[f"P{m.group(1)}"] = f"Phase {m.group(1)}{m.group(2)}".strip()
    return out


def parse_decisions(text: str) -> dict[str, str]:
    return {f"D{m.group(1)}": m.group(2).split("**")[0].strip()
            for m in re.finditer(r"^(\d+)\. \*\*(.*)$", text, re.M)}


def parse_plan_table(text: str) -> dict | None:
    a, b = text.find("<!-- parts-table:start -->"), text.find("<!-- parts-table:end -->")
    if a < 0 or b < a:
        return None

    def cells(s: str) -> list[str]:
        return [x.strip() for x in s.replace("`", "").split(",") if x.strip() and x.strip() != "—"]

    out = {}
    for line in text[a:b].split("\n"):
        c = [x.strip() for x in line.split("|")]
        if len(c) < 7:
            continue
        m = re.fullmatch(r"`([a-z0-9-]+)`", c[2])
        if m:
            out[m.group(1)] = {"status": c[3], "cites": cells(c[4]), "deps": cells(c[5])}
    return out


def topo(nodes: list[dict]) -> tuple[list[str], bool]:
    ids = {n["id"] for n in nodes}
    indeg = {n["id"]: 0 for n in nodes}
    out: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for n in nodes:
        for d, _ in n["deps"]:
            if d in ids:
                indeg[n["id"]] += 1
                out[d].append(n["id"])
    queue = [n["id"] for n in nodes if indeg[n["id"]] == 0]
    order: list[str] = []
    while queue:
        v = queue.pop(0)
        order.append(v)
        for w in out[v]:
            indeg[w] -= 1
            if indeg[w] == 0:
                queue.append(w)
    return order, len(order) != len(nodes)


def longest_to(nodes: list[dict], target: str) -> list[str] | None:
    """Mirror of the page's longestTo: ties break on the prerequisite listed first."""
    by = {n["id"]: n for n in nodes}
    order, cyclic = topo(nodes)
    if cyclic:
        return None
    best: dict[str, int] = {}
    prev: dict[str, str | None] = {}
    for nid in order:
        n = by[nid]
        if n["in1"] != "yes":
            continue
        best[nid], prev[nid] = 1, None
        for d, _ in n["deps"]:
            if d in best and best[d] + 1 > best[nid]:
                best[nid], prev[nid] = best[d] + 1, d
    if target not in best:
        return None
    path, v = [], target
    while v:
        path.insert(0, v)
        v = prev[v]
    return path


# --- the checks (pure; the controls feed them plants) ----------------------------------------


def citation_problems(nodes, known: dict[str, str]) -> list[str]:
    bad = []
    for n in nodes:
        if n["id"] != SINK and not n["cites"]:
            bad.append(f"{n['id']} cites nothing")
        bad += [f"{n['id']}:{c}" for c in n["cites"] if c not in known]
    return bad


def reference_problems(nodes) -> list[str]:
    ids = {n["id"] for n in nodes}
    bad = [f"{n['id']} status {n['status']!r}" for n in nodes if n["status"] not in STATUSES]
    bad += [f"{n['id']} needs unknown {d}" for n in nodes for d, _ in n["deps"] if d not in ids]
    bad += [f"{n['id']} in1 {n['in1']!r}" for n in nodes if n["in1"] not in ("yes", "open", "no")]
    return bad


def plan_doc_problems(nodes, table: dict) -> list[str]:
    bad = []
    for n in nodes:
        d = table.get(n["id"])
        if d is None:
            bad.append(f"{n['id']} missing from 1.0-PLAN.md")
            continue
        if d["status"] != n["status"]:
            bad.append(f"{n['id']} status {d['status']} != {n['status']}")
        if sorted(d["cites"]) != sorted(n["cites"]):
            bad.append(f"{n['id']} cites differ")
        if sorted(d["deps"]) != sorted(x[0] for x in n["deps"]):
            bad.append(f"{n['id']} prerequisites differ")
    bad += [f"{k} in 1.0-PLAN.md, not the map" for k in table if k not in {n["id"] for n in nodes}]
    return bad


def promise_problems(promises, nodes) -> list[str]:
    ids = {n["id"] for n in nodes}
    bad = [f"{p['id']} has no gate" for p in promises if not p.get("verify")]
    bad += [f"{p['id']} has no level" for p in promises if p.get("level") not in ("MUST", "NICE")]
    bad += [f"{p['id']} today {p.get('today')!r}" for p in promises if p.get("today") not in ("met", "partial", "open")]
    bad += [f"{p['id']} -> {n}" for p in promises for n in p["nodes"] if n not in ids]
    return bad


@pytest.fixture(scope="module")
def data() -> dict:
    return load_data(MAP.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def known() -> dict[str, str]:
    k = parse_roadmap((ROOT / "ROADMAP.md").read_text(encoding="utf-8"))
    k.update(parse_decisions((ROOT / "DECISIONS.md").read_text(encoding="utf-8")))
    return k


def test_every_citation_resolves(data, known):
    assert citation_problems(data["nodes"], known) == []


def test_the_dependency_graph_is_acyclic(data):
    assert topo(data["nodes"])[1] is False


def test_references_and_vocabulary(data):
    assert reference_problems(data["nodes"]) == []
    assert SINK in {n["id"] for n in data["nodes"]}


def test_the_map_matches_the_plan_doc(data):
    table = parse_plan_table(PLAN.read_text(encoding="utf-8"))
    assert table is not None, "1.0-PLAN.md lost its parts-table markers"
    assert plan_doc_problems(data["nodes"], table) == []


def test_the_critical_path_reaches_v1(data):
    path = longest_to(data["nodes"], SINK)
    assert path and path[-1] == SINK and len(path) >= 2


def test_every_promise_names_a_gate_and_real_parts(data):
    assert promise_problems(data["promises"], data["nodes"]) == []


def test_snapshot_titles_match_the_sources(data, known):
    """The page shows these titles when it cannot fetch ROADMAP.md (e.g. the
    published Artifact); a stale snapshot would show a renamed gap's old title."""
    stale = {c: t for c, t in data.get("citeTitles", {}).items() if known.get(c) != t}
    assert stale == {}, "regenerate citeTitles from ROADMAP.md / DECISIONS.md"


# --- must-fail controls ------------------------------------------------------------------------


def test_controls(data, known):
    nodes = data["nodes"]
    planted = nodes + [{"id": "zz", "status": "planned", "in1": "yes", "cites": ["G9999"], "deps": []}]
    assert citation_problems(planted, known)
    cyc = [dict(n, deps=n["deps"] + [[SINK, "planted"]]) if i == 0 else n for i, n in enumerate(nodes)]
    assert topo(cyc)[1] is True
    bad_ref = [dict(n, deps=n["deps"] + [["nope", "planted"]]) if i == 1 else n for i, n in enumerate(nodes)]
    assert reference_problems(bad_ref)
    table = parse_plan_table(PLAN.read_text(encoding="utf-8"))
    first = next(iter(table))
    drifted = dict(table, **{first: dict(table[first], status="parked" if table[first]["status"] != "parked" else "planned")})
    assert plan_doc_problems(nodes, drifted)
    assert promise_problems(data["promises"] + [{"id": "X", "verify": "", "level": "MUST", "today": "met", "nodes": ["nope"]}], nodes)
