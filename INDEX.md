# INDEX — knowledge retrieval map

The retrieval layer for the [Self-Improving Knowledge Loop](CLAUDE.md#self-improving-knowledge-loop).
**Read this file in full at the start of each session** (it is kept deliberately
small), then pull ONLY the matching entries from [LIBRARY.md](LIBRARY.md) into
context — never load all of LIBRARY by default.

Each line: `[Lxxxx] tags — one-line hook → resolves to the LIBRARY anchor`.
`†` marks a `candidate` (unpromoted) lesson; canonical lessons carry no mark.

## Tags
`workflow` · `architecture` · `contracts` · `coordination` · `theory-traps`

## Entries
- [L0001]† `workflow,contracts` — a new MCP tool needs a conformance CASE or the total ratchet fails; regenerate goldens additively in the same PR.
- [L0002]† `workflow,coordination` — a closing keyword binds to ONE issue; `closes #a #b` leaves #b open. Repeat the keyword per issue, in the PR BODY (the title never links).
- [L0003]  `workflow,architecture` — joining two co-scaling collections: use `area_indices`/`_sweep_active`, never an inline rescan. Filed 4× (#206/#214/#246/#256). Invisible at fixture scale; verify fixes by byte-diffing output.
- [L0004]  `coordination,contracts` — hand over the DOMAIN with the finding: a mechanism transfers between projects, a severity does not (HYPERSAW-002).
- [L0005]  `workflow,coordination` — when a fix lands, grep its SIBLINGS (neighbour modules + the layer's CLAUDE.md/docstrings): #262→#275, #288→#295.
- [L0006]† `workflow,contracts` — a gate over "every X" must DISCOVER X from the tree; a hand-kept list or an unrun README command is a silent hole (quickstart broken for months; traversal ratchet missed a loader).

<!--
Scope reminder (full rules in CLAUDE.md § Scope boundary): LIBRARY holds only
repo-shared agent-PROCESS lessons. Decisions/plans → ROADMAP.md; code-structure
facts → per-layer CLAUDE.md; user-private machine-local state → ~/.claude memory.
Never edit INDEX without LIBRARY, or vice versa.
-->
