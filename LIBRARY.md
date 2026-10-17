# LIBRARY — durable, evidence-backed lessons

Long-term memory for the [Self-Improving Knowledge Loop](CLAUDE.md#self-improving-knowledge-loop).
**Repo-shared agent-process lessons only** — the hard-won, evidenced "how to work
in this repo without re-tripping a wire." Not decisions/plans (→ ROADMAP.md), not
code-structure facts (→ per-layer CLAUDE.md), not user-private machine-local state
(→ `~/.claude` auto-memory). See CLAUDE.md § Scope boundary before adding.

Entries are retrieved via [INDEX.md](INDEX.md); every entry has an `[Lxxxx]` anchor
that INDEX points to. New lessons enter as `tier: candidate` and are promoted to
`canonical` on a second independent occurrence or human review. Each entry states
its own **falsifier** — the observation that would retire it (trust present
evidence over any stored lesson).

**Entry template**

```
[Lxxxx] <title> | tier | added: YYYY-MM-DD | tags: … | lesson: … | evidence: … | falsifier: … | supersedes: …
```

---

### [L0001] A new MCP tool requires a conformance case

`tier: candidate` | `added: 2026-07-07` | `tags: workflow, contracts` | `supersedes: —`

- **lesson:** The conformance harness (`tests/test_conformance.py`) enforces
  **total** tool coverage (no exclusions since RE-4b): any function added to
  `mts/mcp/tools.py`'s `TOOLS` tuple without a matching entry in `CASES` fails
  `test_every_tool_has_a_conformance_case`. Add the `CASES` entry and regenerate
  the golden in the **same** PR — `PYTHONPATH=. .venv/bin/python3.13
  tests/test_conformance.py --regenerate` — where a brand-new tool's diff is
  **purely additive** (new lines, zero deletions); any deletion/modification means
  you changed existing output and must justify it.
- **evidence:** Adding `search_identities` (PR #147) tripped exactly this failure;
  adding its `CASES` entry + regenerating produced a `+148 / -0` golden diff,
  confirming no existing behavior moved.
- **falsifier:** `test_conformance.py` stops asserting total tool coverage (e.g.
  `EXCLUDED_TOOLS` is reintroduced), or the golden stops being the tool oracle.

---

### [L0002] GitHub closes only the issue whose number carries the keyword

`tier: candidate` | `added: 2026-08-07` | `tags: workflow, coordination` | `supersedes: —`

- **lesson:** A closing keyword binds to **one** issue reference. A
  `closes #245 #246 #247 #248 #249` auto-closes **only #245** — the bare
  numbers after it are plain links, not closers. Repeat the keyword per issue:
  `closes #245, closes #246, …`. **And put it where GitHub reads it** (refined
  2026-10-08): the PR **body** links the issue as soon as the PR is opened, and so
  does a **commit message** once that commit merges to the default branch. The
  PR **title** never links anything. Write the keywords in the body, so the link
  shows (`gh pr view N --json closingIssuesReferences`) *before* the merge rather
  than being discovered after it. This matters here because the audit thread files
  findings as issues and the dev loop routinely answers several in one sweep PR,
  so the failure mode is a merged, genuinely-fixed sweep leaving issues open and
  the board reading stale.
- **evidence:** PR #252 (audit sweep, 2026-08-07) fixed and shipped #245–#249;
  after merge only #245 was CLOSED and #246–#249 were still OPEN, closed manually
  afterwards. The identical wording had been used on the earlier #204–#208 sweep.
  Channel evidence (2026-09): PR #298 was titled `… — closes #295`, and its
  `closingIssuesReferences` stayed `[]` until `Closes #295.` was added to the body,
  after which both the PR and the issue showed the link. PR #294 had no keyword in
  its body and showed no links, yet its issues closed on merge, because commit
  `3816f9a`'s message read `closes #286, closes #287, closes #288`.
- **falsifier:** GitHub changes the linked-issue parser to accept a keyword
  followed by a list of references (watch the docs for "linking a pull request to
  an issue"); then a single keyword would suffice and this lesson is obsolete.
  For the channel half: a PR whose keyword appears only in its title shows a
  non-empty `closingIssuesReferences`.

---

### [L0003] Joining two co-scaling collections: reach for the shared helper, never a rescan

`tier: canonical` | `added: 2026-08-07` | `tags: workflow, architecture` | `supersedes: —`

- **lesson:** This repo's single most-repeated defect is **a scan or membership
  test inside a loop over a collection that grows with the same input** — four
  independent occurrences, each written by a different session that had no idea
  the previous three existed, each caught only by the audit thread's §6b probe,
  each fixed by the same remedy (bucket/index once, before the loop). Before
  writing any join of two time-ordered streams, use the existing helper —
  `structural_key.area_indices` for areas×beats, `segmentation._sweep_active` for
  the onset sweep — rather than an inline comprehension that reads correctly and
  scales quadratically. Two corollaries earned the hard way: the defect is
  **invisible at test-fixture scale** (shipped tests run 8–16 bars), and it is
  often **masked by a slower neighbour** (#256 sat under `segment_to_chords`), so
  "the tests pass and it feels fast" is not evidence. Verify a fix by
  **byte-comparing old vs new output**, not by re-running the suite: every one of
  these refactors touched a hot path where a subtle off-by-one would pass the
  tests it had.
- **evidence:** #206 `part_profiles` · #214 `part_relations` (165×) · #246
  `drums._match` (exponent 1.81→0.71) · #256 `key_confirmation` + `chromatic`
  (1.90→0.98, 28× at 1200 bars). In #256 two modules written **in the same week
  by the same agent** each re-derived the same quadratic join independently.
- **falsifier:** a fifth occurrence appears in code that *did* use the shared
  helper (⇒ the helper, not the reaching-for-it, is the problem), or `audit/`
  stops running the §6b scaling probe (⇒ the detection this lesson relies on is
  gone and the claim is unverifiable).

---

### [L0004] A mechanism transfers between projects; a severity does not

`tier: canonical` | `added: 2026-08-19` | `tags: coordination, contracts` | `supersedes: —`

- **lesson:** When you hand a consumer a finding, hand them the **domain
  assumption that produced its severity**, or they will import your blast radius
  along with your mechanism. The *shape* of a defect ("first candidate wins a
  tie, and the scan ascends, so every tie resolves downward") travels intact
  between codebases. The *frequency* does not: it is a property of the input
  domain, and the receiving project's domain is almost never yours. State the
  domain in the same breath as the count. Symmetrically, when you RECEIVE a
  finding, re-derive its severity in your own domain before acting on it or
  repeating it — the mechanism is a gift, the number is a hypothesis.
- **evidence:** HYPERSAW-002, 2026-08-19. We reported that our fixed "snap down"
  tie-break decided *every* accidental (all 5 out-of-scale pcs tie in a major
  scale) and sagged chromatic lines flat. HYPERSAW found the identical mechanism
  in their quantiser, independently, and reported it with our severity attached.
  They then filed an unprompted correction: `conform_to_scale` quantises
  **integer MIDI**, where an out-of-scale pc is exactly equidistant *every time*;
  their quantiser takes a **continuous** glide, where the tie is a knife edge one
  ULP wide. Same defect, same direction, radically different reachability. Our
  finding was true and our number was not theirs — and we had not said which
  domain the number came from.
- **falsifier:** a finding whose severity DOES transfer unchanged between two
  projects with different input domains (⇒ severity is a property of the
  mechanism after all, and the caution is noise). Note that a shared domain is
  not a counter-example — the claim is about differing domains.

---

### [L0005] When a fix lands, grep its siblings — the defect is rarely only where it was reported

`tier: canonical` | `added: 2026-09-29` | `tags: workflow, coordination` | `supersedes: —`

- **lesson:** An audit issue names *one* file, and fixing that file closes the
  issue — but the same defect usually also lives in that file's **siblings**: the
  module next to it built on the same pattern, or the per-layer doc describing the
  same thing. Fixing only the named site leaves an identical defect a later audit
  files again. Before closing a fix, grep for the pattern (the stale phrase, the
  unguarded idiom) across the sibling modules **and** the layer's docs
  (`<layer>/CLAUDE.md`, `__init__` docstrings, ROADMAP). The rule gets corrected
  where it is *read* and left standing where it is *inherited*.
- **evidence:** Two independent occurrences, both fixes of mine, both re-filed by
  the audit thread. (1) #262 added the MIDI-boundary `range` flag to
  `generate/conform.py`; the identical unflagged octave flip survived in its
  siblings `remap.py` and `modal.py` until #275. (2) #288 fixed
  `search/__init__.py` calling `search_voicings` "the planned sibling"; the same
  stale claim survived in `mts/search/CLAUDE.md` until #295, three days later.
  Different defects in different layers, same failure: one site fixed, siblings
  unchecked.
- **falsifier:** a sibling grep done at fix time that still misses a recurrence
  the audit then finds (⇒ grepping is the wrong defence, and the fix belongs in a
  shared helper or a gate instead); or a long stretch of fixes where no sibling
  recurrence appears (⇒ these two were a coincidence, and the check is overhead).

### [L0006] A gate must discover its targets; a hand-kept list or an unrun doc command is a silent hole

`tier: candidate` | `added: 2026-10-17` | `tags: workflow, contracts` | `supersedes: —`

- **lesson:** When a check runs over "every X", derive X from the tree (glob the
  modules, walk the TOOLS tuple, glob `examples/`), never from a list written when
  the check was. New code lands outside a hand-kept list without anyone noticing,
  and the check keeps passing. The same holds for a command the README tells a
  human to run: if no test executes it, it is a claim, not a contract. The
  `test_every_tool_has_a_conformance_case` ratchet (L0001) is the shape to copy.
- **evidence:** Two independent holes, both found by the 2026-10-17 drift audit.
  (1) The README's first runnable command, `examples/quickstart_engine_demo.py`,
  crashed for months: RE-6e deleted a helper it imported, and nothing ran
  `examples/`. Now gated by `tests/test_examples.py`, proven red on the old file.
  (2) The path-traversal ratchet listed `rules.library` and `patterns.library`
  by hand, so the drum-pattern loader added later in `io/loaders.py` sat outside
  it (guarded in code by luck, not by the gate). It now scans every module, and
  was proven red on a plant in exactly that module.
- **falsifier:** a discovering gate that misses a target the tree does contain
  (⇒ discovery needs its own control); or hand-kept lists that stay complete
  across many slices (⇒ these two were incidental, not a pattern).
