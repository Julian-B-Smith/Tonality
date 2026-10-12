# Audit loop — runbook (the executable cycle)

> The **[AUDIT.md](AUDIT.md) charter is binding** — read it first every cycle;
> this file is only the repeatable *procedure* that runs it. One cycle = one
> pass of the steps below. The audit **finds and reports; it never fixes**
> (fixes are the dev loop's job) and it **only writes under `audit/` or as
> GitHub issues** — never `mts/` `tests/` `scripts/` `docs/` `ROADMAP.md`
> `CLAUDE.md`.

## 0. Preconditions (one of two isolation modes)

The audit must never share a working directory with the dev loop (uncommitted
files collide — it has happened). Pick the mode that matches how the loop runs:

**Mode A — cloud / fresh clone (recommended for a scheduled routine).** A fresh
`git clone` is self-isolating; no worktree needed.
```bash
git clone <repo> tonality-audit && cd tonality-audit
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev,mcp]'          # mcp so the full tool surface imports
```

**Mode B — local worktree (this Mac).** Share history, isolate files; use the
main repo's venv.
```bash
git worktree add ../tonality-audit -b audit-cycle origin/main   # fresh per cycle
cd ../tonality-audit
PY=~/Documents/Tonality/.venv/bin/python3.13
# cleanup at cycle end (from the main repo): git worktree remove ../tonality-audit
```

Either way: **audit `origin/main`'s current tip.** Rebase/re-clone each cycle so
you audit merged code, not a stale branch.

## 1. Scope the cycle (avoid false positives)

- `gh pr list --state open` → **skip areas under open PRs** (auditing
  half-merged work produces transient noise). Note which subsystems are in-flight.
- Skim `ROADMAP.md` for what's **intended-but-unbuilt** — anything unchecked /
  "deferred" / "parked" / "future" is a **known gap, not a bug** (charter §5).
  Recent deltas to know: harmony rule family shipped (gap B); CI enforces
  `pytest tests/` + `pytest audit/checks/` on every PR; port pin fingerprints
  only integer fields (floats are tolerance-checked).
- Note the commit you're auditing: `git rev-parse --short HEAD`.

## 2. Run the committed checks (regression floor)

```bash
$PY -m pytest audit/checks -q          # the standing invariants
```
These now also run in CI — so a *committed* audit check that fails is already
loud on PRs. Your value this cycle is **finding what isn't yet covered.**

## 3. Explore for new findings (the actual audit)

Pick 1–3 invariant families from charter §6 that the current diff/subsystems most
stress, and probe them **as behavioral invariants, not exact outputs** (§6 —
exact-output asserts trip on every refactor). High-value families:
identity/reduction round-trips · `interpret_chord` mask consistency ·
display-free analysis (no note-name strings in `analyze_*`) · transpose
invariance · determinism (same input → identical output) · catalog integrity ·
(stretch) external ground truth vs Ian Ring.
Bias toward subsystems that changed since the last cycle (check `git log` since
the last audit tag/issue) and toward the newest surface (e.g. the `search/` and
`harmony`-family code, `melodic_tendency`, the style-profile pieces).

**Then run the efficiency & complexity pass (charter §6b) — every cycle.** Two
parts: (1) a **structural read** of the newest/most-scalable code for the
scan-inside-a-loop / re-derivation / O(n²)-structure / unbounded-cache
anti-patterns (this is how #206 and #214 were both caught — by loop shape, not
timing); and (2) the **empirical probe**:
```bash
$PY audit/checks/scaling_probe.py     # exponents for the temporal entry points
```
Add the cycle's newest scalable surface to that file's `__main__` (a probe is
three lines: `make_input(n)`, the callable, one `report(...)`). A fitted exponent
> ~1.4 on a should-be-linear path is a §4 finding. **Never** commit a wall-clock
assertion as a collected `audit/checks/test_*` — CI runs those and timing flakes;
the probe stays a hand-run utility whose output is an issue or a cycle-log line.

**Then run the semantic-coherence pass (charter §6a) — every cycle, not optional.**
Unlike the families above, this is a *reading* pass, not a code run: check that the
system still makes coherent sense across code + docs + decisions + `integrations/`
rulings. Concretely each cycle: (a) does the doctrine actually hold in the changed
code (error-don't-guess, plural/evidenced, priors cited, generative-labeled)? (b)
do docstrings / per-layer `CLAUDE.md` / `README` / `INTEGRATION.md` / ROADMAP
"shipped" claims match what the code now does? (c) is any term of art redefined
between code and docs? (d) is any ROADMAP decision or `integrations/` response
ruling contradicted by newer code or a newer notice? (e) did any frozen schema/prior
version change without a bump? File contradictions as §4 findings (the two
locations + the violated claim); a clean pass is logged, not silent.

## 4. File findings (charter §4 format — every finding needs all three)

```bash
gh issue create --label audit --label "severity:high|med|low" \
  --title "<subsystem>: <one line>" \
  --body "Contract violated: <cite CLAUDE.md / ROADMAP / stated invariant>.
Repro: <minimal code>.
Expected vs Actual: <...>.
Audited at: <commit>."
```
Optionally back a bug with a **strict-xfail check in `audit/checks/`** (never
`tests/`) referencing the issue number in its `reason` — it flips to a failure
(auto-alert) when the dev loop fixes it. A standing invariant that earns its keep
gets **proposed for promotion into `tests/` via a normal PR** — never added there
unilaterally.

## 5. Close the cycle

- If you added checks, commit them on the audit branch only (`git add audit/…`,
  never `-A`).
- Mode B: `git worktree remove ../tonality-audit` from the main repo.
- **Append one line to the cycle log below** (date · commit · #issues filed ·
  families probed) so the next cycle sees coverage history and doesn't re-till
  the same ground.

## Cycle log

| Date | Commit | Issues filed | Families probed | Notes |
|---|---|---|---|---|
| _(seed)_ | — | — | — | Loop (re)prepared 2026-07-08; awaiting first scheduled cycle. |
| 2026-08-24 | `9cd7b30` | #286, #287, #288 | 6a (semantic coherence), 6b (efficiency/complexity — structural read + empirical), identity/reduction round-trips, `interpret_chord` mask consistency, register-guard ("error don't guess"), transpose invariance, determinism, catalog integrity | First real cycle (no open PRs; nothing in `mts/` changed since the #274–#277 sweep, only integrations/docs commits). Committed `audit/checks` (3 tests) clean. Behavioral invariant probes (round-trips, `interpret_chord`, `analyze_voicing` register guard, transpose invariance incl. 200-mask random sample, chord-quality mask-collision scan) all clean — no findings. 6a pass over the newest features (`find_scale_runs`, unmatched-naming fallback, gap-32 recommendation surface) came back clean; found #287 (`search/__init__.py` docstring calls shipped `search_voicings` "the planned sibling") and #286 (`modal.py` `plan_from_payload` drops `range_corrected` on JSON round-trip, contradicting its own "reported not absorbed" contract from audit #275). 6b structural read of `mts/temporal/`, `mts/generate/` found #288 (`chromatic.py`'s `_function_of` omits `enrich_unmatched=False`, ~30x wasted work per unmatched chromatic span on a corpus-scale path — the exact cost the codebase already fixed once at a sibling call site) — empirically confirmed (~30x on this machine). `scaling_probe.py`'s `__main__` still only wires `part_profiles`/`part_relations`; newer entry points (`find_scale_runs`, `confirm_key_areas`, `classify_chromatic_events`, `modal_transform`) probed by hand this cycle (exponents all near-linear, informal — no probe added to the file, left as a next-cycle candidate rather than expanding scope mid-cycle). |
| 2026-09-21 | `640d7b6` | none — clean | 6a (semantic coherence), 6b (efficiency/complexity — empirical, expanded), identity/reduction round-trips, `interpret_chord` mask consistency, register-guard, transpose invariance, determinism, catalog integrity | No open PRs. `mts/` unchanged since `9cd7b30` (this cycle's diff is docs/integrations/traces only: `SESSION.md`/`DECISIONS.md` Decision 17, `integrations/PROTOCOL.md`'s new "terminal `status:`" rule, three closed Tonality-Live threads) — so behavioral re-probes on the same code reconfirmed the prior cycle's clean result rather than finding new ground: `interpret_chord` mask-consistency (300 random 3–7-note pc sets, seed 7) 0 issues; `analyze_chord` determinism equal; no spelled note-name strings in its `to_dict()`; interval vector invariant across all 12 transpositions of a triad; `analyze_voicing(None)` raises `SpecificationError` (register-guard holds). Committed `audit/checks` (3 tests) clean. 6a: read the cycle's actual docs delta (Decision 17 + `integrations/PROTOCOL.md`'s terminal-`status:` addition + the `closed-*.md` Tonality-Live files) for contradictions against CLAUDE.md's mailbox section and ROADMAP — coherent, no drift found; `README.md`'s dated freshness line (`d3110b6`, 79 tools) still holds (`test_tool_manifest_pin.py` passes). 6b: closed the "next-cycle candidate" from the prior log line — wired `confirm_key_areas`, `classify_chromatic_events`, `find_scale_runs`, `modal_transform` into `scaling_probe.py`'s `__main__` (committed) alongside `part_profiles`/`part_relations`; all six fit near-linear exponents (0.67–1.07, all ≤1.4). The three issues filed 2026-08-24 (#286 med, #287 low, #288 low) are still open and unaddressed — not re-filed (see SESSION.md 2026-08-27, which independently confirms #286 as a verified two-line regression and names it the next session's first move). |
| 2026-09-28 | `c56a605` | #295 | 6a (semantic coherence), 6b (efficiency/complexity — structural read + empirical), identity/reduction round-trips, `interpret_chord` mask consistency, register-guard, transpose invariance, determinism, catalog integrity | No open PRs. `mts/` unchanged apart from the `3816f9a` fix that closed #286/#287/#288 (own commit re-verified: 1224 tests pass, `pytest audit/checks -q` 3 passed). Behavioral re-probes clean: `interpret_chord` mask consistency (300 random 3–8-note pc sets, seed 11), `analyze_chord` determinism + no note-name leakage, interval-vector transpose invariance across all 12 rotations — no findings. 6b: ran `scaling_probe.py`'s existing six entry points, all still near-linear (0.74–1.04, ≤1.4); structural read this cycle moved to previously-lighter-touched layers — `mts/patterns/cross_part.py`'s `find_cross_part_pattern` (bisect-based shared-onset/homorhythm lookups, not linear scans — no anti-pattern) and `mts/rules/evaluator.py`'s `evaluate` (per-family `_Stream` memoized across rules via the `streams` dict, not re-derived per rule — no anti-pattern); both clean. 6a: read `mts/search/CLAUDE.md` (untouched by the #288 fix, which only patched the sibling `mts/search/__init__.py`) against the now-shipped `search_voicings` — found **#295** (low): the file's own Decision-12 paragraph still calls the shipped, register-required `search_voicings` "the planned ... slice," directly contradicting its own line 25 description of the same function as already built (the same drift shape as #288, in a doc file that fix didn't reach); verified the "handedness" half of that sentence is still accurate (`VOICING_FIELDS` has no signed-chirality field) so the fix should narrow, not delete, the claim. `mts/representation/` reviewed for the "numeric/structural only, no note names/colors" contract (incl. the newer `colour_content.py`) — all descriptor fields are numeric or catalog-name strings (`scale_name`, `quality`), no spelled pitches or RGB/hue values; no drift. |
| 2026-10-12 | `5a7cf57` | none — clean | 6b (empirical), identity/reduction round-trips, transpose/inversion invariance (all 4096 masks), catalog integrity | No open issues. Committed `audit/checks` (3) pass; `pytest tests/` 1277 pass; `scaling_probe.py` six entry points all near-linear (0.73–1.14, ≤1.4). Exhaustive 4096-mask probe: PCs↔mask round-trip, interval vector invariant under all rotations and inversion — 0 failures. Cloud run: did not complete a full 6a read pass or per-PR scoping (open-PR list was too large to read in-session). |
